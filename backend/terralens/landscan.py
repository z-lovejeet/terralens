"""Scene-level land scanning built on the frozen PCA + K-Means study model.

A scene (for example a satellite screenshot of a neighbourhood) is cut into a
grid of square tiles. Every tile goes through the same 78-descriptor extractor,
study-fitted scaler, PCA projection and K-Means centroids as the Patch Analyzer.
Nothing is refitted and no reference label is consulted while a tile is grouped.

Plain-language land types are attached to the ten discovered groups afterwards,
from the post-hoc audit (which EuroSAT categories each frozen group mostly
contains). The audit is opened only to *name* groups, never to assign tiles.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from functools import lru_cache
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .features import extract_features
from .inference import ArtifactVersion, _load_model, _project

DETAIL_LEVELS = {"low": 4, "medium": 6, "high": 8}
MAX_LONG_SIDE_TILES = 12
MIN_SCENE_SIDE = 128
PREVIEW_MAX_SIDE = 768
# A tile is unfamiliar when it sits further from its centre than 1.5× the distance
# that only 1% of the 21,600 study patches exceed (any group).
UNUSUAL_FACTOR = 1.5
UNUSUAL_REFERENCE_PERCENTILE = 99
LOOK_CHANGE_FACTOR = 1.5

# Everyday land types and the EuroSAT reference categories they summarise.
LAND_TYPES: dict[str, dict] = {
    "trees": {"label": "Trees & greenery", "classes": ("Forest", "HerbaceousVegetation")},
    "farmland": {"label": "Fields & farmland", "classes": ("AnnualCrop", "PermanentCrop", "Pasture")},
    "water": {"label": "Water", "classes": ("River", "SeaLake")},
    "built": {"label": "Buildings & roads", "classes": ("Residential", "Industrial", "Highway")},
    "bare": {"label": "Bare ground & open plots", "classes": ()},
    "mixed": {"label": "Mixed land", "classes": ()},
}
# The clustering model only ever names groups trees/farmland/water/built/mixed;
# "bare" comes from the Gemini reading used by Check my area.
LAND_ORDER = ("trees", "farmland", "water", "built", "bare", "mixed")
VEGETATED = ("trees", "farmland")


@dataclass(frozen=True)
class Grid:
    rows: int
    cols: int
    tile_px: float
    width: int
    height: int


# ---------------------------------------------------------------------------
# Naming the frozen groups
# ---------------------------------------------------------------------------

def _name_group(shares: dict[str, float]) -> str:
    """A group takes a land type only when that type clearly dominates it."""
    top = max(LAND_ORDER[:4], key=lambda key: shares[key])
    if shares[top] >= 0.5:
        return top
    if shares["trees"] + shares["farmland"] >= 0.75:
        return max(VEGETATED, key=lambda key: shares[key])
    return "mixed"


@lru_cache(maxsize=2)
def _group_profiles(audit_version: ArtifactVersion, run_id: str) -> dict[int, dict]:
    audit = json.loads(audit_version.path.read_text(encoding="utf-8"))
    if audit.get("reference_run_id") != run_id:
        raise ValueError("The saved audit does not describe the frozen scanning model")
    class_to_type = {name: key for key, value in LAND_TYPES.items() for name in value["classes"]}
    profiles = {}
    for row in audit["contingency"]:
        total = max(int(row["total"]), 1)
        shares = dict.fromkeys(LAND_ORDER[:4], 0.0)
        for name, count in row["counts"].items():
            shares[class_to_type[name]] += count / total
        land_type = _name_group(shares)
        profiles[int(row["cluster"])] = {
            "land_type": land_type,
            "shares": {key: round(value, 4) for key, value in shares.items()},
            # How often patches in this group really are the named land type.
            "reliability": round(shares[land_type] if land_type != "mixed" else max(shares.values()), 4),
        }
    return profiles


def group_profiles(artifacts_dir: Path) -> dict[int, dict]:
    model = _load_model(ArtifactVersion.read(Path(artifacts_dir) / "model.joblib"))
    return _group_profiles(ArtifactVersion.read(Path(artifacts_dir) / "audit.json"), model["reference_run_id"])


# ---------------------------------------------------------------------------
# Cutting a scene into tiles
# ---------------------------------------------------------------------------

def plan_grid(width: int, height: int, detail: str) -> Grid:
    if detail not in DETAIL_LEVELS:
        raise ValueError("Choose a detail level: low, medium or high")
    short_tiles = DETAIL_LEVELS[detail]
    tile_px = min(width, height) / short_tiles
    # Integer arithmetic so an exact fit (e.g. 1200 × 800 at 6 rows) keeps its last column.
    long_tiles = min(MAX_LONG_SIDE_TILES, max(width, height) * short_tiles // min(width, height))
    if width >= height:
        cols, rows = long_tiles, short_tiles
    else:
        cols, rows = short_tiles, long_tiles
    return Grid(rows=rows, cols=cols, tile_px=tile_px, width=round(cols * tile_px), height=round(rows * tile_px))


def crop_to_grid(image: Image.Image, grid: Grid) -> Image.Image:
    """Centre-crop the scene to the exact grid footprint."""
    left = (image.width - grid.width) // 2
    top = (image.height - grid.height) // 2
    return image.crop((left, top, left + grid.width, top + grid.height))


def cut_tiles(scene: Image.Image, grid: Grid) -> list[Image.Image]:
    tiles = []
    for row in range(grid.rows):
        for col in range(grid.cols):
            box = (
                round(col * grid.tile_px), round(row * grid.tile_px),
                round((col + 1) * grid.tile_px), round((row + 1) * grid.tile_px),
            )
            tiles.append(scene.crop(box).resize((64, 64), Image.Resampling.LANCZOS))
    return tiles


def preview_base64(scene: Image.Image) -> str:
    preview = scene.copy()
    preview.thumbnail((PREVIEW_MAX_SIDE, PREVIEW_MAX_SIDE), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    preview.save(buffer, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# Grouping tiles with the frozen model
# ---------------------------------------------------------------------------

def _classify(tiles: list[Image.Image], artifacts_dir: Path) -> dict:
    model = _load_model(ArtifactVersion.read(Path(artifacts_dir) / "model.joblib"))
    profiles = group_profiles(artifacts_dir)
    raw = np.stack([extract_features(tile) for tile in tiles])
    _, space = _project(model, raw)
    clusters = model["kmeans"].predict(space)
    centres = model["kmeans"].cluster_centers_
    distances = np.linalg.norm(space - centres[clusters], axis=1)
    reference = np.concatenate(list(model["cluster_distances"].values()))
    typical_spread = float(np.median(reference))
    unusual_limit = UNUSUAL_FACTOR * float(np.percentile(reference, UNUSUAL_REFERENCE_PERCENTILE))
    return {
        "run_id": model["reference_run_id"],
        "clusters": clusters,
        "space": space,
        "unusual": distances > unusual_limit,
        "land_types": [profiles[int(cluster)]["land_type"] for cluster in clusters],
        "profiles": profiles,
        "typical_spread": typical_spread,
    }


def _breakdown(land_types: list[str], cover: dict[str, float] | None = None) -> list[dict]:
    """Shares per land type: counted from tiles, or taken from an overall cover estimate."""
    total = len(land_types)
    return [
        {
            "land_type": key,
            "label": LAND_TYPES[key]["label"],
            "tiles": land_types.count(key),
            "percent": round(cover.get(key, 0.0), 1) if cover is not None else round(100 * land_types.count(key) / total, 1),
        }
        for key in LAND_ORDER
    ]


def _percent(breakdown: list[dict], *keys: str) -> float:
    return round(sum(item["percent"] for item in breakdown if item["land_type"] in keys), 1)


def _reliability(unusual_tiles: np.ndarray, land_types: list[str]) -> dict:
    unusual = float(np.mean(unusual_tiles))
    mixed = land_types.count("mixed") / len(land_types)
    if unusual <= 0.15 and mixed <= 0.3:
        level, note = "high", "Most tiles look like the satellite images the model learned from."
    elif unusual <= 0.4 and mixed <= 0.55:
        level, note = "medium", "Some tiles look unfamiliar or mixed, so treat the percentages as rough."
    else:
        level, note = "low", (
            "Many tiles look unlike the model's satellite images. Use a top-down satellite view "
            "zoomed out to show a whole neighbourhood, and avoid map labels or 3D views."
        )
    return {"level": level, "unusual_percent": round(100 * unusual, 1), "mixed_percent": round(100 * mixed, 1), "note": note}


def _group_table(profiles: dict[int, dict]) -> list[dict]:
    return [
        {"cluster": cluster, "land_type": profile["land_type"], "reliability": profile["reliability"]}
        for cluster, profile in sorted(profiles.items())
    ]


METHOD_NOTE = (
    "Each tile is described by 78 colour, texture and edge measurements, projected with the study's PCA "
    "(28 components) and matched to the nearest of the 10 K-Means groups. Groups were discovered without "
    "labels; their everyday names come from checking afterwards which land types each group mostly contained."
)


# ---------------------------------------------------------------------------
# Feature 1: Check my area
# ---------------------------------------------------------------------------

def _area_profile(breakdown: list[dict]) -> dict:
    green = _percent(breakdown, *VEGETATED)
    trees = _percent(breakdown, "trees")
    built = _percent(breakdown, "built")
    water = _percent(breakdown, "water")
    dominant = max((item for item in breakdown if item["land_type"] != "mixed"), key=lambda item: item["percent"])

    bare = _percent(breakdown, "bare")
    if built >= 50:
        headline = "A mostly built-up area"
    elif bare >= 40:
        headline = "An area with a lot of open, bare ground"
    elif green >= 60 and trees >= _percent(breakdown, "farmland"):
        headline = "A green, mostly natural area"
    elif green >= 60:
        headline = "A mostly farmland area"
    elif water >= 35:
        headline = "An area dominated by water"
    elif dominant["percent"] >= 30:
        headline = f"A mixed area, mostly {dominant['label'].lower()}"
    else:
        headline = "A mixed area with no single dominant land type"

    if green >= 60:
        score_label = "High"
    elif green >= 40:
        score_label = "Good"
    elif green >= 20:
        score_label = "Moderate"
    else:
        score_label = "Low"

    considerations = []
    if green < 20:
        considerations.append({
            "topic": "Heat", "tone": "watch",
            "text": "Very little greenery. Areas like this usually get hotter on summer days; trees and parks help cool them.",
        })
    elif green >= 40:
        considerations.append({
            "topic": "Greenery", "tone": "good",
            "text": "Plenty of green cover, which supports cleaner air, shade and cooler summers.",
        })
    if water >= 5:
        considerations.append({
            "topic": "Water nearby", "tone": "watch",
            "text": "Water bodies are part of this view. If you are buying or building, check your local flood-risk map.",
        })
    if built >= 50 and trees < 10:
        considerations.append({
            "topic": "Open space", "tone": "watch",
            "text": "Dense buildings with almost no trees. Look for nearby parks if outdoor space matters to you.",
        })
    if bare >= 20:
        considerations.append({
            "topic": "Open plots", "tone": "info",
            "text": "A lot of bare ground or empty plots. Areas like this are often being developed, so expect construction nearby.",
        })
    if _percent(breakdown, "farmland") >= 40:
        considerations.append({
            "topic": "Farming area", "tone": "info",
            "text": "Large share of fields. Expect seasonal changes in colour as crops grow and are harvested.",
        })
    if not considerations:
        considerations.append({
            "topic": "Balanced", "tone": "info",
            "text": "No single land type dominates. Compare this view again in another season to see how it changes.",
        })
    return {
        "headline": headline,
        "green_cover": {"percent": green, "label": score_label},
        "built_percent": built,
        "water_percent": water,
        "considerations": considerations,
    }


def area_check(image: Image.Image, artifacts_dir: Path, detail: str = "medium") -> dict:
    rgb = image.convert("RGB")
    grid = plan_grid(rgb.width, rgb.height, detail)
    scene = crop_to_grid(rgb, grid)
    result = _classify(cut_tiles(scene, grid), artifacts_dir)
    land_types = result["land_types"]
    breakdown = _breakdown(land_types)
    warnings = []
    if (scene.width, scene.height) != rgb.size:
        warnings.append(f"Edges trimmed from {rgb.width}×{rgb.height} to {scene.width}×{scene.height} so the grid fits evenly.")
    tiles = [
        {
            "row": index // grid.cols, "col": index % grid.cols,
            "land_type": land_types[index], "cluster": int(result["clusters"][index]),
            "unusual": bool(result["unusual"][index]),
        }
        for index in range(len(land_types))
    ]
    return {
        "run_id": result["run_id"],
        "image": preview_base64(scene),
        "grid": {"rows": grid.rows, "cols": grid.cols},
        "tiles": tiles,
        "breakdown": breakdown,
        "profile": _area_profile(breakdown),
        "reliability": _reliability(result["unusual"], land_types),
        "groups": _group_table(result["profiles"]),
        "method": METHOD_NOTE,
        "warnings": warnings,
    }


AREA_METHOD_NOTE = (
    "The screenshot is divided into a labelled grid of squares. An AI image model estimates how much of each square "
    "is trees, fields, water, buildings or bare ground, ignoring map labels and pins. Each square on the map takes its "
    "largest share (or 'mixed' if nothing covers at least 40%), and the overall percentages are the average of all squares."
)


def area_report(scene: Image.Image, rows: int, cols: int, reading: dict, warnings: list[str]) -> dict:
    """Build the Check my area report from a per-square land reading."""
    tiles = [
        {"row": index // cols, "col": index % cols, "land_type": land_type, "shares": shares}
        for index, (land_type, shares) in enumerate(zip(reading["cells"], reading["cell_shares"], strict=True))
    ]
    breakdown = _breakdown(reading["cells"], reading["cover"])
    overhead = reading["image_kind"] in ("satellite", "aerial")
    level = "low" if not overhead else "medium" if reading["quality_notes"] else "high"
    note = {
        "high": "Clear overhead image, so the reading should give a dependable rough picture of the area.",
        "medium": "The image has some problems (see the notes), so treat the percentages as rough.",
        "low": "This does not look like a top-down satellite or aerial view, so the reading may be wrong.",
    }[level]
    return {
        "image": preview_base64(scene),
        "grid": {"rows": rows, "cols": cols},
        "tiles": tiles,
        "breakdown": breakdown,
        "profile": _area_profile(breakdown),
        "reliability": {"level": level, "note": note},
        "place": {key: reading[key] for key in ("setting", "headline", "summary", "features", "quality_notes")},
        "method": AREA_METHOD_NOTE,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Feature 2: Crisis Radar (what changed between two views of one place)
# ---------------------------------------------------------------------------

STORIES = {
    "flood": {
        "title": "Water has spread onto land",
        "explanation": "Areas that looked like fields, greenery or buildings now look like water. This is the pattern left by floods or rising rivers.",
        "next_steps": [
            "Check official flood warnings for this area before travelling.",
            "Avoid low-lying roads and riverbanks until water levels are confirmed safe.",
            "Compare with a newer image in a few days to see if the water is receding.",
        ],
    },
    "drying": {
        "title": "Water has shrunk",
        "explanation": "Areas that looked like water now look like land. Lakes and reservoirs shrink like this during droughts or heavy water use.",
        "next_steps": [
            "Check local water-supply and drought notices.",
            "Farmers relying on this water source may need to plan irrigation early.",
            "Repeat the check after the rainy season to see whether it recovers.",
        ],
    },
    "clearing": {
        "title": "Trees and greenery have been cleared",
        "explanation": "Areas that looked like trees now look like fields, bare or mixed land. This is the pattern of tree cutting, land clearing or fire damage.",
        "next_steps": [
            "If this is a protected forest, report it to the local forest department.",
            "Compare with an older image to see how fast the clearing is spreading.",
            "Cleared slopes raise the risk of soil erosion and landslides in heavy rain.",
        ],
    },
    "construction": {
        "title": "New buildings or roads have appeared",
        "explanation": "Areas that looked like fields or greenery now look like buildings and roads. This is the pattern of town growth or new construction.",
        "next_steps": [
            "Check the local development plan to see whether this construction is approved.",
            "Look at how much green space remains nearby.",
            "New paved surfaces increase rain run-off, so drainage matters more.",
        ],
    },
    "regrowth": {
        "title": "Greenery has returned",
        "explanation": "Areas that looked like buildings, bare or mixed land now look green. This is the pattern of regrowth, new plantations or crops coming up.",
        "next_steps": [
            "Seasonal crops can cause this; compare images from the same month in different years.",
            "If this is a restoration project, repeat the check yearly to track progress.",
        ],
    },
    "shift": {
        "title": "The land looks different",
        "explanation": "Parts of this place have changed appearance, but not in one clear direction. Seasons, harvests or different lighting can also cause this.",
        "next_steps": [
            "Make sure both images show the same area at the same zoom.",
            "Prefer images taken in the same season to avoid false alarms.",
        ],
    },
    "none": {
        "title": "No real change found",
        "explanation": "The two views look like the same kinds of land in the same places.",
        "next_steps": ["Check again later, or try a higher detail level to look closer."],
    },
}


STORY_ORDER = ("flood", "drying", "construction", "clearing", "regrowth")
MIN_STORY_SHIFT = 5.0  # percentage points of the whole area


def _story_for(change: dict[str, float]) -> str:
    """Pick the story from the net change in each land type, so squares that straddle two
    land types (and read as 'mixed') cannot flip the verdict."""
    scores = {
        "flood": change["water"],
        "drying": -change["water"],
        "construction": change["built"],
        "clearing": -change["trees"],
        # vegetation gained at the expense of buildings, bare or mixed land (not water, which is drying)
        "regrowth": min(change["trees"] + change["farmland"], -(change["built"] + change.get("bare", 0) + change["mixed"])),
    }
    best = max(STORY_ORDER, key=lambda key: (scores[key], -STORY_ORDER.index(key)))
    return best if scores[best] >= MIN_STORY_SHIFT else "shift"


def change_check(before: Image.Image, after: Image.Image, artifacts_dir: Path, detail: str = "medium") -> dict:
    before_rgb, after_rgb = before.convert("RGB"), after.convert("RGB")
    warnings = []
    ratio_before = before_rgb.width / before_rgb.height
    ratio_after = after_rgb.width / after_rgb.height
    if abs(ratio_before - ratio_after) / ratio_before > 0.1:
        warnings.append("The two images have different shapes. Make sure they show the same area at the same zoom.")
    if after_rgb.size != before_rgb.size:
        after_rgb = after_rgb.resize(before_rgb.size, Image.Resampling.LANCZOS)
    grid = plan_grid(before_rgb.width, before_rgb.height, detail)
    before_scene, after_scene = crop_to_grid(before_rgb, grid), crop_to_grid(after_rgb, grid)
    first = _classify(cut_tiles(before_scene, grid), artifacts_dir)
    second = _classify(cut_tiles(after_scene, grid), artifacts_dir)

    movement = np.linalg.norm(first["space"] - second["space"], axis=1)
    look_threshold = LOOK_CHANGE_FACTOR * first["typical_spread"]
    tiles, transitions = [], {}
    for index, (old, new) in enumerate(zip(first["land_types"], second["land_types"], strict=True)):
        if old != new:
            change = "type"
            transitions[(old, new)] = transitions.get((old, new), 0) + 1
        elif movement[index] > look_threshold:
            change = "look"
        else:
            change = "none"
        tiles.append({
            "row": index // grid.cols, "col": index % grid.cols,
            "before": old, "after": new, "change": change,
            "movement": round(float(movement[index]), 3),
        })

    total = len(tiles)
    changed = sum(tile["change"] == "type" for tile in tiles)
    look_changed = sum(tile["change"] == "look" for tile in tiles)
    changed_percent = round(100 * changed / total, 1)

    before_breakdown, after_breakdown = _breakdown(first["land_types"]), _breakdown(second["land_types"])
    deltas = [
        {
            "land_type": old["land_type"], "label": old["label"],
            "before": old["percent"], "after": new["percent"],
            "change": round(new["percent"] - old["percent"], 1),
        }
        for old, new in zip(before_breakdown, after_breakdown, strict=True)
    ]
    if changed_percent < 5:
        level, story = "none", "none"
    else:
        story = _story_for({row["land_type"]: row["change"] for row in deltas})
        level = "major" if changed_percent >= 35 else "noticeable" if changed_percent >= 15 else "small"
    top_transitions = [
        {"from": old, "to": new, "tiles": count, "percent": round(100 * count / total, 1)}
        for (old, new), count in sorted(transitions.items(), key=lambda item: -item[1])[:4]
    ]
    return {
        "run_id": first["run_id"],
        "before_image": preview_base64(before_scene),
        "after_image": preview_base64(after_scene),
        "grid": {"rows": grid.rows, "cols": grid.cols},
        "tiles": tiles,
        "summary": {
            "changed_percent": changed_percent,
            "look_changed_percent": round(100 * look_changed / total, 1),
            "level": level,
        },
        "verdict": {"story": story, **STORIES[story]},
        "deltas": deltas,
        "transitions": top_transitions,
        "reliability": {
            "before": _reliability(first["unusual"], first["land_types"]),
            "after": _reliability(second["unusual"], second["land_types"]),
        },
        "groups": _group_table(first["profiles"]),
        "method": METHOD_NOTE + " A tile counts as changed when its land type differs between the two views.",
        "warnings": warnings,
    }
