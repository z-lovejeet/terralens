"""Where can we plant trees? Turn a per-square planting reading into spots, counts and advice."""
from __future__ import annotations

from PIL import Image

from .landscan import preview_base64

# How wide the uploaded image is on the ground, chosen by the user in plain terms.
AREA_WIDTHS = {"street": 200, "colony": 500, "neighbourhood": 1000, "large": 3000}
TREE_SPACING_M = 5          # typical spacing for shade trees
USABLE_SHARE = 0.6          # leave room for paths, gaps, utilities and access
SAPLINGS_PER_M2_DENSE = 3   # Miyawaki-style dense planting

METHOD_NOTE = (
    "The screenshot is divided into a labelled grid. An AI image model estimates, square by square, how much is existing "
    "tree canopy, open ground where trees could grow, buildings and roads, water, or other uses such as crop fields, and "
    "marks the best open spots. Tree numbers assume trees about 5 m apart on 60% of the open ground, leaving room for paths, "
    "gaps and utilities, and use the image width you chose to convert the image into square metres."
)

BEFORE_YOU_PLANT = [
    {"topic": "Ask first", "text": "Roadsides, parks and vacant plots usually belong to the municipality, a society or a private owner. Get permission before planting."},
    {"topic": "Check below and above", "text": "Keep clear of underground pipes and cables and overhead wires. Ask the local utility office if unsure."},
    {"topic": "Choose native trees", "text": "Local nurseries and the forest department can suggest native species that suit your climate and need less water."},
    {"topic": "Give them space", "text": "Plant shade trees at least 3 m from buildings and walls so roots and branches have room to grow."},
    {"topic": "Plan the watering", "text": "Young trees need regular watering for the first two to three years. Agree who will look after them."},
]


def _round_trees(count: float) -> int:
    count = max(0, int(count))
    if count >= 1000:
        return int(round(count, -2))
    if count >= 100:
        return int(round(count, -1))
    return count


def _trees_for(area_m2: float) -> int:
    return _round_trees(area_m2 * USABLE_SHARE / TREE_SPACING_M ** 2)


def planting_report(scene: Image.Image, image_width_px: int, rows: int, cols: int, reading: dict, width_key: str, warnings: list[str]) -> dict:
    metres_per_px = AREA_WIDTHS[width_key] / image_width_px
    scene_area_m2 = (scene.width * metres_per_px) * (scene.height * metres_per_px)
    cells = reading["cell_shares"]
    plantable_pct = sum(cell["plantable"] for cell in cells) / len(cells)
    trees_pct = sum(cell["trees"] for cell in cells) / len(cells)
    plantable_m2 = scene_area_m2 * plantable_pct / 100
    cover_after = min(100.0, trees_pct + plantable_pct * USABLE_SHARE)

    spots = []
    for index, spot in enumerate(reading["spots"], start=1):
        box_m2 = scene_area_m2 * (spot["width"] / 100) * (spot["height"] / 100)
        spots.append({**spot, "number": index, "area_m2": round(box_m2, -1), "trees": _trees_for(box_m2)})

    biggest = max((spot for spot in spots if spot["priority"] == "high"), key=lambda spot: spot["area_m2"], default=None)
    ideas = []
    if biggest and biggest["area_m2"] >= 100:
        ideas.append(
            f"Spot {biggest['number']} is large enough for a dense mini-forest: even a 100 m² patch can hold about "
            f"{100 * SAPLINGS_PER_M2_DENSE} saplings planted close together, which grow into a thicket within a few years."
        )
    if any(spot["kind"] == "roadside" for spot in spots):
        ideas.append("A row of shade trees along the marked roadsides would cool the street for people walking and waiting there.")
    if any(spot["kind"] == "school_or_campus" for spot in spots):
        ideas.append("School and campus grounds are ideal for a student planting drive, with classes adopting a tree each.")
    if trees_pct < 15:
        ideas.append("Tree cover here is low, so every tree planted makes a noticeable difference to shade and summer heat.")

    overhead = reading["image_kind"] in ("satellite", "aerial")
    level = "low" if not overhead else "medium" if reading["quality_notes"] else "high"
    return {
        "image": preview_base64(scene),
        "grid": {"rows": rows, "cols": cols},
        "tiles": [
            {"row": index // cols, "col": index % cols, "plantable": cell["plantable"], "trees": cell["trees"]}
            for index, cell in enumerate(cells)
        ],
        "summary": {
            "headline": reading["headline"],
            "text": reading["summary"],
            "trees_possible": _trees_for(plantable_m2),
            "plantable_percent": round(plantable_pct, 1),
            "plantable_m2": round(plantable_m2, -1),
            "tree_cover_now": round(trees_pct, 1),
            "tree_cover_after": round(cover_after, 1),
            "area_width_m": AREA_WIDTHS[width_key],
            "spacing_m": TREE_SPACING_M,
        },
        "spots": spots,
        "ideas": ideas,
        "before_you_plant": BEFORE_YOU_PLANT,
        "reliability": {
            "level": level,
            "note": {
                "high": "Clear overhead image. Tree numbers depend most on the image width you chose, so treat them as a rough guide.",
                "medium": "The image has some problems (see the notes), so treat spots and numbers as rough.",
                "low": "This does not look like a top-down satellite or aerial view, so the spots may be wrong.",
            }[level],
        },
        "quality_notes": reading["quality_notes"],
        "method": METHOD_NOTE,
        "warnings": warnings,
    }
