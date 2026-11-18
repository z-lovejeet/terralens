"""FastAPI routes for Natural Disaster Reconnaissance and Patch Analyzer Presets.
Powered by Gemini 3.5 Flash-Lite Vision Core and EuroSAT Unsupervised Model.
"""
from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image

from terralens.api.resources import Resources
from terralens.applied import (
    DISASTER_PRESETS,
    assess_disaster_scene,
)

router = APIRouter(tags=["Applied Capabilities"])

ANALYZER_PRESETS = [
    {"id": "pe0bce20c66ac24a69c02", "label": "Dense Forest Canopy", "dominant": "Forest"},
    {"id": "p4c4d3414ff772fda8d8b", "label": "Meandering River Channel", "dominant": "River & Waterways"},
    {"id": "pc3e5311f7c0a3428ea84", "label": "Heavy Industrial Complex", "dominant": "Industrial Buildings"},
    {"id": "p4ad8538c80a0317ebcc1", "label": "Residential Roof Grid", "dominant": "Residential Buildings"},
    {"id": "pf86a09867b8db213f801", "label": "Active Agricultural Crops", "dominant": "Annual Crops"},
]


# ==============================================================================
# NATURAL DISASTER & CRISIS RECONNAISSANCE (GEMINI 3.5 FLASH-LITE VISION CORE)
# ==============================================================================

@router.get("/disaster/presets")
def get_disaster_presets():
    return DISASTER_PRESETS


@router.post("/disaster")
async def detect_disaster(
    resources: Resources,
    preset_id: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    artifacts_dir = resources.artifacts
    image: Image.Image | None = None

    if preset_id:
        preset_file = artifacts_dir / "presets" / "disasters" / f"{preset_id}.jpg"
        if not preset_file.is_file():
            raise HTTPException(404, f"Disaster preset '{preset_id}' not found.")
        image = Image.open(preset_file)
    elif file:
        raw = await file.read()
        await file.close()
        if not raw:
            raise HTTPException(422, "Uploaded file is empty.")
        try:
            image = Image.open(io.BytesIO(raw))
        except Exception:
            raise HTTPException(422, "Could not decode uploaded disaster image.")
    else:
        # Default to wildfire
        preset_file = artifacts_dir / "presets" / "disasters" / "wildfire_burn_scar.jpg"
        image = Image.open(preset_file)

    try:
        result = assess_disaster_scene(image, preset_id=preset_id)
        return result
    finally:
        if image:
            image.close()


@router.get("/analyzer/presets")
def get_analyzer_presets():
    return ANALYZER_PRESETS
