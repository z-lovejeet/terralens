"""Real-world operational capabilities: Natural Disaster & Crisis Reconnaissance.
Powered by Gemini 3.5 Flash-Lite Vision Core.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image

from .gemini_service import (
    DISPLAY_MODEL_NAME,
    analyze_disaster_reconnaissance_llm,
)

DISASTER_PRESETS = [
    {
        "id": "wildfire_burn_scar",
        "title": "Active Wildfire & Thermal Burn Scar",
        "location": "Sierra Foothills / Sonoma Complex, USA",
        "type": "Wildfire",
        "description": "Rapidly propagating flame front, thick smoke plumes, and completely charred black vegetative burn scar.",
        "image_path": "artifacts/presets/disasters/wildfire_burn_scar.jpg",
    },
    {
        "id": "tsunami_inundation",
        "title": "Tsunami Surge & Marine Inundation",
        "location": "Sendai Coastal Lowlands, Japan",
        "type": "Tsunami & Marine Surge",
        "description": "High-turbidity seawater intrusion breaching coastal defense dykes and submerging settlements and transport lines.",
        "image_path": "artifacts/presets/disasters/tsunami_inundation.jpg",
    },
    {
        "id": "amazon_deforestation",
        "title": "Rainforest Deforestation Frontier",
        "location": "Rondônia Basin, Amazon Border",
        "type": "Deforestation",
        "description": "Systematic fishbone logging road penetration and complete clear-cutting of virgin rainforest canopy to bare red soil.",
        "image_path": "artifacts/presets/disasters/amazon_deforestation.jpg",
    },
    {
        "id": "river_flood_breach",
        "title": "Catastrophic River Levee Breach",
        "location": "Rhine-Meuse Alluvial Delta",
        "type": "Riverine Flood",
        "description": "Breached protective earthen river dikes causing extensive brown sediment-laden submersion of surrounding cropland.",
        "image_path": "artifacts/presets/disasters/river_flood_breach.jpg",
    },
    {
        "id": "reservoir_drought",
        "title": "Reservoir Drought & Desiccation",
        "location": "Alqueva Basin, Southern Europe",
        "type": "Severe Drought",
        "description": "Critically receded waterlines, exposed dried mud lakebed, and widespread vegetative moisture deficit.",
        "image_path": "artifacts/presets/disasters/reservoir_drought.jpg",
    },
]


def image_to_base64_jpeg(image: Image.Image, quality: int = 88) -> str:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def assess_disaster_scene(image: Image.Image, preset_id: str | None = None) -> dict[str, Any]:
    """Run Natural Disaster Reconnaissance on satellite scene using Gemini 3.5 Flash-Lite Vision.
    Detects tsunami aftermath, wildfires, burn scars, floods, deforestation, and droughts.
    """
    rgb_img = image.convert("RGB")
    w, h = rgb_img.size
    target_dim = 512
    # Resize keeping aspect ratio or scaling smoothly
    resized = rgb_img.resize((target_dim, target_dim), Image.Resampling.LANCZOS)
    
    # Run Gemini Vision Crisis Analysis
    crisis_report = analyze_disaster_reconnaissance_llm(resized, preset_id)
    
    return {
        "preset_id": preset_id,
        "image_base64": image_to_base64_jpeg(resized),
        "dimensions": [w, h],
        "crisis_report": crisis_report,
        "engine": DISPLAY_MODEL_NAME,
    }
