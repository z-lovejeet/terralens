"""Name a region from its colour and texture, for images unlike the training data.

Map my image finds regions without any labels (K-Means on the image's own squares). To put an
everyday name on a region it first asks the 30-group land model, but that model learned from
64 x 64 Sentinel-2 patches (10 m per pixel, a dull bluish palette). Close-up screenshots from
map apps are sharper and more colourful, so for them the land model's answer is unreliable.

For those images each region is read from a few measurable cues instead:

* greenness  - excess-green index (2G - R - B) / (R + G + B), the standard RGB vegetation index,
               also compared with the least green region of the same image;
* brightness - mean of each pixel's brightest channel;
* smoothness - mean local standard deviation of grey (5 x 5 pixels); open water is the flattest
               surface in an image;
* stripes    - structure-tensor coherence: how much the edges share one direction. Ploughed or
               planted fields have parallel rows; tree crowns and water do not;
* darkness   - share of very dark pixels (deep or shaded water).

The thresholds were set by checking 14 public satellite views by eye (lakes, rivers, sea fronts,
forests, farms, towns and a desert town). On those, 81 % of clearly identifiable regions were named
right; buildings and water were never named wrongly, while trees versus crop fields was the hardest
pair, so borderline calls are marked as a best guess. This reading is an interpretation of the
clusters, not a trained classifier.
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

# Checked by eye on 14 public satellite views (see the module docstring and README).
EYE_CHECK = {"views": 14, "regions": 52, "accuracy": 0.83, "area_accuracy": 0.90, "clear_accuracy": 0.91}

# Region names the reading can give (keys match the land model's types, plus bare ground).
READ_TYPES = ("trees", "farmland", "water", "built", "bare", "mixed")

GREEN_EXG = 0.10            # clearly green
GREEN_MARGIN = 0.055        # or this much greener than the least green region of the same image
WATER_SMOOTH = 0.011        # local grey spread below this is very flat
WATER_SMOOTH_LOOSE = 0.015  # ...or a little higher, when the region is not reddish and has no rows
WATER_STILL = 0.007         # flat enough to be water whatever its colour (muddy lakes)
WATER_MAX_BRIGHT = 0.55     # bright, flat land is sand or concrete, not water
WATER_MAX_REDNESS = 0.06
WATER_MAX_ROWS = 0.65
WATER_MAX_GREEN = 0.30      # vivid green is plants, however flat it looks
DEEP_DARK = 0.5             # half the pixels very dark...
DEEP_SMOOTH = 0.02          # ...and fairly flat: deep or shaded water
BARE_BRIGHT = 0.63          # bright, not green: sand, dry soil, open ground
BUILT_TEXTURE = 0.04        # textured and not green: roofs, roads, yards
FIELD_ROWS = 0.75           # strongly parallel edges: fields, even when pale
TREE_TEXTURE = 0.035
TREE_ROWS = 0.45
TREE_DARK = 0.32


def cue_maps(scene: Image.Image) -> dict[str, np.ndarray]:
    """Per-pixel cues for the working image."""
    rgb = np.asarray(scene.convert("RGB"), dtype=np.float64) / 255.0
    grey = rgb @ np.array([0.2125, 0.7154, 0.0721])
    mean = ndimage.uniform_filter(grey, 5)
    spread = np.sqrt(np.maximum(ndimage.uniform_filter(grey * grey, 5) - mean * mean, 0.0))
    gx, gy = ndimage.sobel(grey, axis=1) / 4, ndimage.sobel(grey, axis=0) / 4
    jxx, jyy, jxy = (ndimage.gaussian_filter(v, 3) for v in (gx * gx, gy * gy, gx * gy))
    coherence = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-9)
    return {"rgb": rgb, "grey": grey, "spread": spread, "coherence": coherence, "energy": gx * gx + gy * gy}


def region_cues(maps: dict[str, np.ndarray], mask: np.ndarray) -> dict[str, float]:
    """Summarise one region (a boolean pixel mask) as the cues the naming rules use."""
    pixels = maps["rgb"][mask]
    r, g, b = pixels.mean(axis=0)
    energy = maps["energy"][mask]
    return {
        "greenness": float((2 * g - r - b) / (r + g + b + 1e-6)),
        "redness": float((r - b) / (r + b + 1e-6)),
        "brightness": float(pixels.max(axis=1).mean()),
        "texture": float(maps["spread"][mask].mean()),
        "rows": float((maps["coherence"][mask] * energy).sum() / (energy.sum() + 1e-12)),
        "dark": float((maps["grey"][mask] < 0.12).mean()),
    }


def read_region(cues: dict[str, float], least_green: float) -> tuple[str, str]:
    """(land type, confidence) from a region's cues; confidence is 'medium' or 'low' (a best guess)."""
    green = cues["greenness"] >= GREEN_EXG or cues["greenness"] - least_green >= GREEN_MARGIN
    flat, redness, rows = cues["texture"], cues["redness"], cues["rows"]
    if cues["brightness"] < WATER_MAX_BRIGHT and cues["greenness"] < WATER_MAX_GREEN and (
        (flat < WATER_SMOOTH and (redness < WATER_MAX_REDNESS or flat < WATER_STILL))
        or (flat < WATER_SMOOTH_LOOSE and redness < WATER_MAX_REDNESS and rows < WATER_MAX_ROWS)
        or (cues["dark"] > DEEP_DARK and flat < DEEP_SMOOTH)
    ):
        return "water", "medium"
    if not green:
        if cues["brightness"] >= BARE_BRIGHT:
            return "bare", "medium"
        if flat >= BUILT_TEXTURE and rows < FIELD_ROWS:
            return "built", "medium"
        if rows >= FIELD_ROWS or flat < BUILT_TEXTURE:
            return "farmland", "low"  # pale fields, dry grass or bare plots
        return "mixed", "low"
    # Green: trees are darker, rougher and without rows; fields are lighter, smoother, often striped.
    votes = (flat > TREE_TEXTURE) + (rows < TREE_ROWS) + (cues["brightness"] < TREE_DARK)
    if votes == 3:
        return "trees", "medium"
    if votes == 0:
        return "farmland", "medium"
    return ("trees", "low") if votes == 2 else ("farmland", "low")
