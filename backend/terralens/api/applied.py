"""FastAPI routes for Regional Scene Scanner and Temporal Change Detector."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from PIL import Image

from terralens.api.resources import Resources
from terralens.applied import detect_temporal_change, scan_regional_scene

router = APIRouter(tags=["Applied Capabilities"])

SCANNER_PRESETS = [
    {
        "id": "rhine_valley",
        "title": "Rhine River Basin & Floodplain",
        "location": "Bonn, Germany",
        "description": "Meandering river corridor flanked by riparian forest, cropland, and shipping docks.",
    },
    {
        "id": "black_forest",
        "title": "Black Forest Coniferous Canopy",
        "location": "Baden-Württemberg, Germany",
        "description": "Continuous high-density evergreen canopy with high-elevation alpine clearings.",
    },
    {
        "id": "ruhr_industrial",
        "title": "Ruhr Industrial & Logistics Basin",
        "location": "Duisburg, Germany",
        "description": "Heavy industrial manufacturing yards, rail arteries, and dense residential blocks.",
    },
    {
        "id": "agro_plains",
        "title": "Castile Agricultural Grain Belt",
        "location": "Meseta Central, Spain",
        "description": "Vast patchwork of irrigated annual crop furrows, vineyards, and pastures.",
    },
]

CHANGE_PRESETS = [
    {
        "id": "deforestation",
        "title": "Forest Canopy Clearing (Deforestation)",
        "location": "Amazon Border / Rondônia",
        "description": "Dense tropical canopy transitioning to cleared bare soil and pasture.",
    },
    {
        "id": "drought",
        "title": "Reservoir & Riverbed Shrinkage (Drought)",
        "location": "Rhine Low-Water Emergency",
        "description": "Deep surface water retreating to expose sandbars and sediment.",
    },
    {
        "id": "urban_sprawl",
        "title": "Urban Encroachment & Industrial Expansion",
        "location": "Perimeter Logistics Hub",
        "description": "Natural rural pasture converted into concrete logistics warehousing.",
    },
]

ANALYZER_PRESETS = [
    {"id": "pe0bce20c66ac24a69c02", "label": "Dense Forest Canopy", "dominant": "Forest"},
    {"id": "p4c4d3414ff772fda8d8b", "label": "Meandering River Channel", "dominant": "River & Waterways"},
    {"id": "pc3e5311f7c0a3428ea84", "label": "Heavy Industrial Complex", "dominant": "Industrial Buildings"},
    {"id": "p4ad8538c80a0317ebcc1", "label": "Residential Roof Grid", "dominant": "Residential Buildings"},
    {"id": "pf86a09867b8db213f801", "label": "Active Agricultural Crops", "dominant": "Annual Crops"},
]


@router.get("/scan/presets")
def get_scanner_presets():
    return SCANNER_PRESETS


@router.post("/scan")
async def scan_scene(
    resources: Resources,
    file: UploadFile | None = File(None),
    preset_id: str | None = Form(None),
    grid_size: int = Form(4),
):
    artifacts_dir = resources.artifacts
    image: Image.Image | None = None

    if preset_id:
        preset_file = artifacts_dir / "presets" / "landscapes" / f"{preset_id}.jpg"
        if not preset_file.is_file():
            raise HTTPException(404, f"Preset '{preset_id}' not found.")
        image = Image.open(preset_file)
    elif file:
        raw = await file.read()
        await file.close()
        if not raw:
            raise HTTPException(422, "Uploaded file is empty.")
        try:
            image = Image.open(io.BytesIO(raw))
        except Exception:
            raise HTTPException(422, "Could not decode uploaded image.")
    else:
        # Default to first preset
        preset_file = artifacts_dir / "presets" / "landscapes" / "rhine_valley.jpg"
        image = Image.open(preset_file)

    try:
        grid_dim = max(2, min(8, int(grid_size)))
        result = scan_regional_scene(image, artifacts_dir, target_grid=grid_dim)
        return result
    finally:
        if image:
            image.close()


@router.get("/change/presets")
def get_change_presets():
    return CHANGE_PRESETS


@router.post("/change")
async def detect_changes(
    resources: Resources,
    preset_id: str | None = Form(None),
    before_file: UploadFile | None = File(None),
    after_file: UploadFile | None = File(None),
):
    artifacts_dir = resources.artifacts
    b_img: Image.Image | None = None
    a_img: Image.Image | None = None

    if preset_id:
        b_path = artifacts_dir / "presets" / "changes" / f"{preset_id}_before.jpg"
        a_path = artifacts_dir / "presets" / "changes" / f"{preset_id}_after.jpg"
        if not b_path.is_file() or not a_path.is_file():
            raise HTTPException(404, f"Change preset '{preset_id}' not found.")
        b_img = Image.open(b_path)
        a_img = Image.open(a_path)
    elif before_file and after_file:
        b_raw = await before_file.read()
        a_raw = await after_file.read()
        await before_file.close()
        await after_file.close()
        try:
            b_img = Image.open(io.BytesIO(b_raw))
            a_img = Image.open(io.BytesIO(a_raw))
        except Exception:
            raise HTTPException(422, "Could not decode before/after images.")
    else:
        # Default to deforestation
        b_path = artifacts_dir / "presets" / "changes" / "deforestation_before.jpg"
        a_path = artifacts_dir / "presets" / "changes" / "deforestation_after.jpg"
        b_img = Image.open(b_path)
        a_img = Image.open(a_path)

    try:
        result = detect_temporal_change(b_img, a_img, artifacts_dir)
        return result
    finally:
        if b_img:
            b_img.close()
        if a_img:
            a_img.close()


@router.get("/analyzer/presets")
def get_analyzer_presets():
    return ANALYZER_PRESETS
