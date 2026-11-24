"""Map my image: split one satellite image into regions of similar-looking land.

This is unsupervised image segmentation. The image is cut into a grid of small squares and
every square is described by the study's 78 colour, texture and edge measurements. Those
measurements are standardised WITHIN this image (extreme values capped at 3 standard
deviations) and reduced with a PCA fitted to this image's squares (95 % of the variance);
the squares are then grouped with K-Means++ (the number of regions chosen by the elbow method),
lone squares are tidied with a 3 x 3 majority filter, and each region's share is reported.

Standardising within the image matters for photos unlike the training data: in the study's
own space a few out-of-range squares (for example very bright roofs in a close-up) get extreme
coordinates and capture whole clusters, leaving the real village/field split unresolved.
The study's saved scaler, PCA and land model are only read, never changed: they describe the
regions in plain words and name them. A region is named by the 30-group land model (from bigger
squares, 8 along the short side, when at least half the region agrees) if the image resembles
the training imagery; otherwise it is read from its colour and texture (``reading.py``).
"""
from __future__ import annotations

import base64
from functools import lru_cache
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import generic_filter
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from .features import extract_features
from .inference import ArtifactVersion, _load_model
from .landmodel import LAND_TYPES, classify_features
from .reading import EYE_CHECK, cue_maps, read_region, region_cues
from .sorting import _describe, _elbow

SHORT_SIDE_CELLS = 24
MAX_LONG_SIDE_CELLS = 40
HINT_SHORT_SIDE = 8       # hint squares: 8 along the short side, close in size to the training patches
CAP = 3.0                 # standard deviations; caps out-of-range measurements before clustering
KEEP_VARIANCE = 0.95
MAX_REGIONS = 8
MIN_SIDE = 128
WORK_LONG_SIDE = 1024  # large images are scaled down first; regions do not need full resolution
PREVIEW_LONG_SIDE = 900
SEED = 42
LETTERS = "ABCDEFGH"
HINT_MIN_AGREEMENT = 0.5  # the land model names a region only when at least half of the region agrees
# The land model is not used when this share of its squares looks unlike the training imagery. On the
# benchmark scenes at most 8% were unfamiliar; a detailed close-up village screenshot had 60%.
HINT_MAX_UNFAMILIAR = 0.3


def _grid(image: Image.Image) -> tuple[Image.Image, int, int, float]:
    """Scale the image down if needed and crop it to a whole number of square cells."""
    rgb = image.convert("RGB")
    if max(rgb.size) > WORK_LONG_SIDE:
        scale = WORK_LONG_SIDE / max(rgb.size)
        rgb = rgb.resize((round(rgb.width * scale), round(rgb.height * scale)), Image.Resampling.LANCZOS)
    cell = min(rgb.size) / SHORT_SIDE_CELLS
    long_cells = min(MAX_LONG_SIDE_CELLS, int(max(rgb.size) * SHORT_SIDE_CELLS // min(rgb.size)))
    cols, rows = (long_cells, SHORT_SIDE_CELLS) if rgb.width >= rgb.height else (SHORT_SIDE_CELLS, long_cells)
    width, height = round(cols * cell), round(rows * cell)
    left, top = (rgb.width - width) // 2, (rgb.height - height) // 2
    return rgb.crop((left, top, left + width, top + height)), rows, cols, cell


def _cells(scene: Image.Image, rows: int, cols: int, cell: float) -> list[Image.Image]:
    return [
        scene.crop((round(c * cell), round(r * cell), round((c + 1) * cell), round((r + 1) * cell)))
        for r in range(rows) for c in range(cols)
    ]


def clustering_space(raw: np.ndarray) -> np.ndarray:
    """This image's squares, standardised within the image, capped, and reduced with a per-image PCA."""
    z = np.nan_to_num(StandardScaler().fit_transform(raw))
    z = np.clip(z, -CAP, CAP)
    return PCA(n_components=KEEP_VARIANCE, svd_solver="full", random_state=SEED).fit_transform(z)


def _majority(grid: np.ndarray) -> np.ndarray:
    """3 x 3 majority filter: a lone square takes the region most common around it."""
    return generic_filter(grid, lambda values: np.bincount(values.astype(int)).argmax(), size=3, mode="nearest").astype(int)


@lru_cache(maxsize=2)
def _benchmark(version: ArtifactVersion) -> dict:
    return json.loads(version.path.read_text(encoding="utf-8"))


def measured_accuracy(artifacts_dir: Path) -> dict | None:
    """Accuracy measured by scripts/benchmark_regions.py on scenes with a known layout, if it has been run."""
    path = Path(artifacts_dir) / "regions-benchmark.json"
    if not path.is_file():
        return None
    report = _benchmark(ArtifactVersion.read(path))
    native = report["results"]["native"]
    if "name_accuracy" not in native:
        return None  # written by an older benchmark; run scripts/benchmark_regions.py again
    return {
        "scenes": report["scenes"],
        "ari": native["ari"],
        "area_error_points": native["area_error_points"],
        "name_accuracy": native["name_accuracy"],
        "named_share": native["named_share"],
        "zoomed_ari": report["results"]["zoomed_x3"]["ari"],
        "colour_texture": EYE_CHECK,
    }


def _preview(scene: Image.Image) -> str:
    image = scene.copy()
    image.thumbnail((PREVIEW_LONG_SIDE, PREVIEW_LONG_SIDE), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def map_regions(image: Image.Image, artifacts_dir: Path, requested_k: int | None = None) -> dict:
    if requested_k is not None and not 2 <= requested_k <= MAX_REGIONS:
        raise ValueError(f"Choose between 2 and {MAX_REGIONS} regions.")
    original = image.size
    scene, rows, cols, cell = _grid(image)
    raw = np.stack([extract_features(square) for square in _cells(scene, rows, cols, cell)])
    if len(np.unique(np.round(raw, 6), axis=0)) < 2:
        raise ValueError("This image looks the same everywhere, so there are no regions to separate.")
    labelled = classify_features(raw, artifacts_dir)  # frozen study projection: unfamiliar flags only
    space = clustering_space(raw)
    # Land-model names come from bigger squares, closer in size to the training patches; on the
    # benchmark this made them right about 98% of the time instead of about 60%.
    factor = max(1, SHORT_SIDE_CELLS // HINT_SHORT_SIDE)
    hint_rows, hint_cols = max(1, rows // factor), max(1, cols // factor)
    hint_raw = np.stack([extract_features(square) for square in _cells(scene, hint_rows, hint_cols, cell * factor)])
    hint_labels = classify_features(hint_raw, artifacts_dir)
    hint_types = np.array(hint_labels["land_types"]).reshape(hint_rows, hint_cols)
    hint_unfamiliar = float(np.mean(hint_labels["unusual"]))
    model_names = hint_unfamiliar < HINT_MAX_UNFAMILIAR  # otherwise regions are read from colour and texture
    row_index = np.minimum(np.arange(rows) // factor, hint_rows - 1)
    col_index = np.minimum(np.arange(cols) // factor, hint_cols - 1)
    cell_hints = hint_types[row_index][:, col_index].ravel()

    # Never ask for more regions than the image has distinct-looking squares (e.g. flat or uniform images).
    upper = min(MAX_REGIONS, max(2, len(np.unique(np.round(space, 6), axis=0))))
    if requested_k is not None:
        requested_k = min(requested_k, upper)
    candidates, fits = [], {}
    for k in range(2, upper + 1):
        fits[k] = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(space)
        candidates.append({
            "k": k,
            "inertia": round(float(fits[k].inertia_), 3),
            "silhouette": round(float(silhouette_score(space, fits[k].labels_)), 4),
        })
    k = requested_k or _elbow([c["k"] for c in candidates], [c["inertia"] for c in candidates])
    raw_grid = fits[k].labels_.reshape(rows, cols)
    grid = _majority(raw_grid)
    if len(np.unique(grid)) < len(np.unique(raw_grid)):
        grid = raw_grid  # tidying must never erase a whole region
    labels = grid.ravel()

    model = _load_model(ArtifactVersion.read(Path(artifacts_dir) / "model.joblib"))
    standardized = model["scaler"].transform(model["imputer"].transform(raw))
    overall = standardized.mean(axis=0)
    present = [label for label in np.unique(labels)]
    present.sort(key=lambda label: -np.sum(labels == label))  # biggest region first, lettered A, B, C ...
    order = {label: rank for rank, label in enumerate(present)}
    if not model_names:
        maps = cue_maps(scene)
        height, width = maps["grey"].shape
        pixel_labels = grid[(np.arange(height) * rows // height)][:, (np.arange(width) * cols // width)]
        cues = {label: region_cues(maps, pixel_labels == label) for label in present}
        least_green = min(c["greenness"] for c in cues.values())

    regions = []
    for label in present:
        members = np.flatnonzero(labels == label)
        if model_names:
            types = [str(cell_hints[i]) for i in members]
            counts = {t: types.count(t) for t in LAND_TYPES if types.count(t)}
            named = {t: n for t, n in counts.items() if t != "mixed"}
            name = max(named, key=named.get) if named else "mixed"
            agreement = round(named.get(name, 0) / len(members), 3)
            confidence = "high"
            if agreement < HINT_MIN_AGREEMENT:
                name, confidence = "mixed", "low"  # the region is a mix of land types
        else:
            name, confidence = read_region(cues[label], least_green)
            agreement = None
        regions.append({
            "region": order[label],
            "letter": LETTERS[order[label]],
            "share": round(100 * len(members) / len(labels), 1),
            "cells": int(len(members)),
            "description": _describe(standardized[members].mean(axis=0) - overall),
            "name": name,
            "named_by": "land model" if model_names else "colour and texture",
            "confidence": confidence,
            "model_agreement": agreement,
        })
    cover: dict[str, float] = {}
    for region in regions:
        cover[region["name"]] = cover.get(region["name"], 0.0) + region["share"]

    silhouette = float(silhouette_score(space, labels)) if len(present) > 1 else None
    separation = "weak" if silhouette is None or silhouette < 0.1 else "moderate" if silhouette < 0.25 else "clear"
    warnings = []
    if scene.size != original and max(original) <= WORK_LONG_SIDE:
        warnings.append(f"Edges trimmed from {original[0]}×{original[1]} so the squares fit evenly.")
    if max(original) > WORK_LONG_SIDE:
        warnings.append(f"Large image scaled down from {original[0]}×{original[1]} before mapping.")
    unfamiliar = float(np.mean(labelled["unusual"]))
    return {
        "image": _preview(scene),
        "grid": {"rows": rows, "cols": cols},
        "cells": [order[int(label)] for label in labels],
        "k": len(present),
        "chosen": "you" if requested_k else "automatic",
        "regions": regions,
        "candidates": candidates,
        "silhouette": round(silhouette, 4) if silhouette is not None else None,
        "separation": separation,
        "unfamiliar_percent": round(100 * unfamiliar, 1),
        "warnings": warnings,
        "accuracy": measured_accuracy(artifacts_dir),
        "naming": {
            "method": "land model" if model_names else "colour and texture",
            "unfamiliar_percent": round(100 * hint_unfamiliar, 1),
        },
        "land_cover": [{"name": key, "share": round(value, 1)} for key, value in sorted(cover.items(), key=lambda item: -item[1])],
        "method": (
            f"Your image is cut into {rows} × {cols} squares. Each square is described by the study's 78 colour, texture and "
            "edge measurements, which are standardised within your image (extreme values capped) and reduced with PCA. The squares "
            "are then grouped with K-Means++; on Auto, every number of regions from 2 to 8 is tried and the elbow method picks the one where adding "
            "more regions stops making them much tighter. A 3 × 3 majority filter tidies lone squares. Each region is then named: if your image resembles the "
            "satellite images the study learned from, by the 30-group land model on bigger squares (8 along the short side) when at least half "
            "of the region agrees; otherwise from its colour and texture (greenness, brightness, smoothness, field rows and dark water). "
            "Nothing is sent outside this server."
        ),
    }
