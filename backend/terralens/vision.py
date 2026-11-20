"""Single-image crisis assessment with Gemini vision.

The uploaded overhead image is sent to Google's Gemini API with a remote-sensing
prompt and a strict JSON schema. The reply is validated and clamped before it
reaches the browser. There is no offline fallback: if the API is unavailable the
caller gets a clear error instead of an invented assessment.

Configuration (environment variables or ``.env.local`` in the project root):
  GEMINI_API_KEY  Google AI Studio API key (required)
  GEMINI_MODEL    comma-separated model IDs tried in order
"""
from __future__ import annotations

import base64
import io
import json
import logging
import os
import time
import urllib.error
import urllib.request

from PIL import Image

from .settings import ROOT

log = logging.getLogger(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODELS = "gemini-3.5-flash-lite,gemini-flash-lite-latest"
TIMEOUT_SECONDS = 60
RETRIES = 2
RETRY_DELAY = 2.0
MAX_SIDE = 1600

CRISIS_TYPES = (
    "none", "flood", "tsunami", "storm_damage", "wildfire", "burn_scar", "smoke_plume", "drought",
    "deforestation", "landslide", "earthquake_damage", "structural_damage", "volcanic_activity",
    "oil_spill", "algal_bloom", "industrial_accident", "coastal_erosion", "desertification",
    "dust_storm", "snow_ice_hazard", "mining_damage", "other",
)
STATUSES = ("crisis", "no_crisis", "uncertain")
SEVERITIES = ("none", "low", "moderate", "high", "severe")
IMAGE_KINDS = ("satellite", "aerial", "ground_photo", "map_or_graphic", "other")
CLOUD_COVER = ("none", "some", "heavy")


class VisionError(Exception):
    """A user-facing failure with the HTTP status the route should return."""

    def __init__(self, message: str, status: int = 503):
        super().__init__(message)
        self.message = message
        self.status = status


def _api_key() -> str | None:
    value = os.environ.get("GEMINI_API_KEY", "").strip().strip("\"'")
    if value:
        return value
    env_file = ROOT / ".env.local"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, _, raw = line.partition("=")
            if name.strip() == "GEMINI_API_KEY" and raw.strip():
                return raw.strip().strip("\"'")
    return None


def is_configured() -> bool:
    return _api_key() is not None


def _models() -> list[str]:
    return [name.strip() for name in os.environ.get("GEMINI_MODEL", DEFAULT_MODELS).split(",") if name.strip()]


PROMPT = """You are a remote-sensing analyst helping ordinary people understand an overhead image.
The image is usually a true-colour (RGB) satellite or aerial view. There is no thermal or infrared band,
so never claim temperatures or spectral measurements.

Decide whether the image shows a crisis, hazard or environmental damage, and which kind.

Visual cues and common look-alikes:
- Flood: water covering fields, roads or buildings, irregular brown water outside normal banks, standing water in street grids.
  A brown river inside its banks is NOT a flood.
- Tsunami / storm surge: coastal strip stripped of vegetation, debris lines, flattened settlements near the shore.
- Storm damage: roofs missing, debris fields, fallen trees in rows, flattened crops.
- Wildfire: visible flames, bright orange fronts, smoke columns rising from a line or point.
- Burn scar: black or dark-brown patches with sharp edges in vegetation. Cloud shadows match nearby cloud shapes; deep water is smooth and has shorelines.
- Smoke plume: grey-brown streaky haze from a source. White puffy or layered features are usually clouds.
- Drought: shrunken reservoirs with exposed pale lakebed rings, cracked mud, receded shorelines. Brown harvested fields alone are NOT drought.
- Deforestation: geometric clearings inside forest, fishbone road patterns, fresh bare soil next to intact canopy.
- Landslide: fresh bare scar on a slope with a debris fan below, buried roads.
- Earthquake / structural damage: rubble, collapsed or partly collapsed buildings, debris blocking streets.
- Volcanic activity: lava flows, ash-covered land, steam or ash plume from a crater.
- Oil spill: dark or rainbow-sheen smooth patches on water, often near ships or platforms.
- Algal bloom: bright green or blue-green swirls on lakes or sea.
- Industrial accident: fire, smoke or spill at a factory, refinery or port.
- Coastal erosion: collapsed shoreline, eaten-away beaches, damaged sea walls.
- Desertification / dust storm: sand encroaching on fields or roads; a thick tan haze.
- Snow and ice hazard: avalanche tracks, ice jams, snow-buried settlements.
- Mining damage: open pits, tailings ponds, stripped land.

Rules:
- If the scene looks normal, set status "no_crisis", crisis_type "none", severity "none", and describe the scene.
- If you cannot tell, use status "uncertain" and explain what extra image would help.
- If it is not an overhead image, set image_kind accordingly and status "uncertain".
- Do not invent places, dates, casualty numbers or causes you cannot see. Only name a location if it is written in the image.
- regions: up to 6 boxes around visible evidence as [ymin, xmin, ymax, xmax] on a 0-1000 scale, each with a short label. Empty if nothing to mark.
- evidence: short sentences describing what you see, in the same order as the regions where possible.
- actions: 3 to 4 practical, general steps for residents or local responders. Always suggest confirming with official alerts for real emergencies.
- Write in plain, calm English for non-experts. Keep each sentence short.
"""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "image_kind": {"type": "STRING", "enum": list(IMAGE_KINDS)},
        "status": {"type": "STRING", "enum": list(STATUSES)},
        "crisis_type": {"type": "STRING", "enum": list(CRISIS_TYPES)},
        "secondary_types": {"type": "ARRAY", "items": {"type": "STRING", "enum": list(CRISIS_TYPES)}},
        "severity": {"type": "STRING", "enum": list(SEVERITIES)},
        "confidence": {"type": "NUMBER"},
        "headline": {"type": "STRING"},
        "summary": {"type": "STRING"},
        "scene_description": {"type": "STRING"},
        "affected_area_percent": {"type": "NUMBER"},
        "regions": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"label": {"type": "STRING"}, "box_2d": {"type": "ARRAY", "items": {"type": "INTEGER"}}},
                "required": ["label", "box_2d"],
            },
        },
        "evidence": {"type": "ARRAY", "items": {"type": "STRING"}},
        "secondary_risks": {"type": "ARRAY", "items": {"type": "STRING"}},
        "actions": {"type": "ARRAY", "items": {"type": "STRING"}},
        "cloud_cover": {"type": "STRING", "enum": list(CLOUD_COVER)},
        "quality_notes": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": [
        "image_kind", "status", "crisis_type", "severity", "confidence", "headline", "summary",
        "scene_description", "affected_area_percent", "regions", "evidence", "actions", "cloud_cover",
    ],
}


def _jpeg_base64(image: Image.Image) -> str:
    scaled = image.convert("RGB")
    scaled.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    scaled.save(buffer, format="JPEG", quality=90)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _request(model: str, key: str, payload: bytes) -> dict:
    request = urllib.request.Request(
        API_URL.format(model=model), data=payload, method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def _call_gemini(image: Image.Image, prompt: str = None, schema: dict = None, config: dict | None = None) -> tuple[dict, str]:
    key = _api_key()
    if not key:
        log.warning("GEMINI_API_KEY is not configured")
        raise VisionError("Image reading is not available on this server right now.")
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": _jpeg_base64(image)}},
            {"text": prompt or PROMPT},
        ]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json", "responseSchema": schema or SCHEMA, **(config or {})},
    }).encode()
    last_error = VisionError("The image reader is busy right now. Please try again in a minute.")
    for model in _models():
        for attempt in range(RETRIES + 1):
            try:
                reply = _request(model, key, payload)
            except urllib.error.HTTPError as error:
                log.warning("Gemini %s returned HTTP %s", model, error.code)
                if error.code == 404:
                    break  # model not available to this key; try the next one
                if error.code in (401, 403):
                    raise VisionError("Image reading is not available on this server right now.") from None
                if error.code == 400:
                    raise VisionError("This image could not be processed. Try a different JPEG or PNG.", 422) from None
                if error.code in (429, 500, 502, 503, 504) and attempt < RETRIES:
                    time.sleep(RETRY_DELAY * (attempt + 1))  # temporary overload: wait and retry
                    continue
                if error.code == 429:
                    raise VisionError("The image reader is busy right now. Please try again in a minute.", 429) from None
                break
            except (urllib.error.URLError, TimeoutError) as error:
                log.warning("Gemini %s unreachable: %s", model, error)
                break
            candidates = reply.get("candidates") or []
            if not candidates or candidates[0].get("finishReason") in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST"):
                raise VisionError("This image could not be analysed. Try a clear satellite or aerial view.", 422)
            text = "".join(part.get("text", "") for part in candidates[0].get("content", {}).get("parts", []) if not part.get("thought"))
            try:
                return json.loads(text), reply.get("modelVersion") or model
            except json.JSONDecodeError:
                log.warning("Gemini %s returned non-JSON output", model)
                break
    raise last_error


def _text(value, limit: int = 400) -> str:
    return " ".join(str(value or "").split())[:limit]


def _list(values, limit: int, length: int = 220) -> list[str]:
    if not isinstance(values, list):
        return []
    return [_text(item, length) for item in values if _text(item, length)][:limit]


def _choice(value, options: tuple[str, ...], fallback: str) -> str:
    return value if value in options else fallback


def _number(value, low: float, high: float) -> float | None:
    try:
        return round(min(max(float(value), low), high), 3)
    except (TypeError, ValueError):
        return None


def _regions(values) -> list[dict]:
    regions = []
    for item in values if isinstance(values, list) else []:
        box = item.get("box_2d") if isinstance(item, dict) else None
        if not (isinstance(box, list) and len(box) == 4):
            continue
        try:
            top, left, bottom, right = (min(max(int(v), 0), 1000) for v in box)
        except (TypeError, ValueError):
            continue
        if bottom - top < 5 or right - left < 5:
            continue
        regions.append({
            "label": _text(item.get("label"), 80) or "Marked area",
            "top": top / 10, "left": left / 10, "height": (bottom - top) / 10, "width": (right - left) / 10,
        })
    return regions[:6]


def normalise(raw: dict) -> dict:
    """Keep only well-formed fields so the browser never renders unexpected values."""
    status = _choice(raw.get("status"), STATUSES, "uncertain")
    crisis_type = _choice(raw.get("crisis_type"), CRISIS_TYPES, "other")
    severity = _choice(raw.get("severity"), SEVERITIES, "none")
    if status == "no_crisis":
        crisis_type, severity = "none", "none"
    elif crisis_type == "none" and status == "crisis":
        crisis_type = "other"
    secondary = [item for item in raw.get("secondary_types") or [] if item in CRISIS_TYPES and item not in ("none", crisis_type)]
    return {
        "image_kind": _choice(raw.get("image_kind"), IMAGE_KINDS, "other"),
        "status": status,
        "crisis_type": crisis_type,
        "secondary_types": list(dict.fromkeys(secondary))[:3],
        "severity": severity,
        "confidence": _number(raw.get("confidence"), 0, 1),
        "headline": _text(raw.get("headline"), 140) or "Assessment complete",
        "summary": _text(raw.get("summary"), 600),
        "scene_description": _text(raw.get("scene_description"), 500),
        "affected_area_percent": _number(raw.get("affected_area_percent"), 0, 100) if status == "crisis" else 0,
        "regions": _regions(raw.get("regions")),
        "evidence": _list(raw.get("evidence"), 6),
        "secondary_risks": _list(raw.get("secondary_risks"), 4),
        "actions": _list(raw.get("actions"), 5),
        "cloud_cover": _choice(raw.get("cloud_cover"), CLOUD_COVER, "none"),
        "quality_notes": _list(raw.get("quality_notes"), 3),
    }


def assess_crisis(image: Image.Image) -> dict:
    raw, model = _call_gemini(image)
    if not isinstance(raw, dict):
        raise VisionError("The image scanner returned an unreadable answer. Please try again.")
    return {**normalise(raw), "model": model}


# ---------------------------------------------------------------------------
# Check my area: land-cover reading of a screenshot
# ---------------------------------------------------------------------------

AREA_LAND_TYPES = ("trees", "farmland", "water", "built", "bare", "mixed")
COVER_TYPES = AREA_LAND_TYPES[:-1]
SETTINGS = ("city", "town_or_suburb", "village", "farmland", "forest", "coastal", "industrial", "mixed", "other")
MIXED_BELOW = 40  # a square whose largest share is under this is shown as mixed
COLUMN_LETTERS = "ABCDEFGHIJKL"
AREA_CONFIG = {"temperature": 0, "thinkingConfig": {"thinkingLevel": "medium"}}

AREA_PROMPT = """You are measuring land cover in a top-down satellite or aerial image, often a Google Maps screenshot.
Ignore map labels, pins, icons, road names and app buttons; judge only the ground underneath.

A grid of {rows} rows x {cols} columns is drawn on the image. Each square is labelled in its top-left corner with
a column letter (A is the left column) and a row number (1 is the top row), e.g. A1, B1 ... {last}.

For EVERY square from A1 to {last}, look only inside that square and estimate what percentage of its area is:
- trees: tree canopy (dark green, rough, rounded crowns), forest, orchards, tree-lined avenues
- farmland: crop fields (often regular strips or patches), grass, lawns, pasture, sports fields
- water: rivers, lakes, ponds, canals, sea, swimming pools, flooded ground
- built: roofs of houses, flats, factories and sheds; roads, paved yards, parking, railways
- bare: bare soil, sand, dry mud, empty plots, dirt tracks, construction sites, rock
The five numbers for each square must add up to 100. Work square by square; do not copy neighbouring answers.

Then describe the place in plain, calm English for a non-expert: a short headline, a two-sentence summary, and up to
5 things that stand out (a large open field, a dense block of houses, a canal, many empty plots). Do not guess the
city, owners or exact distances. Mention real image problems (heavy labels, blur, clouds, tilted 3D view) in quality_notes.
"""


def _area_schema() -> dict:
    share = {"type": "INTEGER"}
    return {
        "type": "OBJECT",
        "properties": {
            "image_kind": {"type": "STRING", "enum": list(IMAGE_KINDS)},
            "setting": {"type": "STRING", "enum": list(SETTINGS)},
            "cells": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {"cell": {"type": "STRING"}, **{key: share for key in COVER_TYPES}},
                    "required": ["cell", *COVER_TYPES],
                },
            },
            "headline": {"type": "STRING"},
            "summary": {"type": "STRING"},
            "features": {"type": "ARRAY", "items": {"type": "STRING"}},
            "quality_notes": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": ["image_kind", "setting", "cells", "headline", "summary", "features"],
    }


def _label(row: int, col: int) -> str:
    return f"{COLUMN_LETTERS[col]}{row + 1}"


def grid_overlay(image: Image.Image, rows: int, cols: int) -> Image.Image:
    """Draw the labelled reading grid so each answer can be tied to an exact square."""
    from PIL import ImageDraw, ImageFont

    canvas = image.convert("RGB")
    canvas.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(canvas, "RGBA")
    width, height = canvas.size
    cell_w, cell_h = width / cols, height / rows
    size = max(12, int(min(cell_w, cell_h) * 0.14))
    try:
        font = ImageFont.load_default(size=size)
    except TypeError:  # Pillow without scalable default font
        font = ImageFont.load_default()
    for index in range(1, cols):
        x = round(index * cell_w)
        draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 200), width=2)
    for index in range(1, rows):
        y = round(index * cell_h)
        draw.line([(0, y), (width, y)], fill=(255, 255, 255, 200), width=2)
    for row in range(rows):
        for col in range(cols):
            x, y = round(col * cell_w) + 3, round(row * cell_h) + 3
            text = _label(row, col)
            box = draw.textbbox((x, y), text, font=font)
            draw.rectangle((box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2), fill=(0, 0, 0, 170))
            draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    return canvas


def _cell_shares(values, rows: int, cols: int, keys: tuple[str, ...] = COVER_TYPES) -> list[dict[str, float]] | None:
    """Per-square shares keyed by the grid label, each normalised to 100."""
    by_label = {}
    for item in values if isinstance(values, list) else []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("cell", "")).strip().upper()
        shares = {key: _number(item.get(key), 0, 100) or 0.0 for key in keys}
        total = sum(shares.values())
        if total > 0:
            by_label[label] = {key: 100 * value / total for key, value in shares.items()}
    expected = [_label(row, col) for row in range(rows) for col in range(cols)]
    if sum(label in by_label for label in expected) < 0.8 * len(expected):
        return None
    empty = dict.fromkeys(keys, 0.0)
    return [by_label.get(label, empty) for label in expected]


def _dominant(shares: dict[str, float]) -> str:
    top = max(COVER_TYPES, key=lambda key: shares[key])
    return top if shares[top] >= MIXED_BELOW else "mixed"


def assess_area(image: Image.Image, rows: int, cols: int) -> dict:
    last = _label(rows - 1, cols - 1)
    raw, model = _call_gemini(
        grid_overlay(image, rows, cols), AREA_PROMPT.format(rows=rows, cols=cols, last=last), _area_schema(), AREA_CONFIG,
    )
    if not isinstance(raw, dict):
        raise VisionError("The image could not be read. Please try again.")
    shares = _cell_shares(raw.get("cells"), rows, cols)
    if shares is None:
        raise VisionError("The image could not be mapped. Try a clearer, top-down screenshot.", 422)
    known = [cell for cell in shares if sum(cell.values())]
    cover = {key: round(sum(cell[key] for cell in known) / len(known), 1) for key in COVER_TYPES}
    return {
        "image_kind": _choice(raw.get("image_kind"), IMAGE_KINDS, "other"),
        "setting": _choice(raw.get("setting"), SETTINGS, "other"),
        "headline": _text(raw.get("headline"), 140),
        "summary": _text(raw.get("summary"), 600),
        "cells": [_dominant(cell) if sum(cell.values()) else "mixed" for cell in shares],
        "cell_shares": [{key: round(value, 1) for key, value in cell.items()} for cell in shares],
        "cover": cover,
        "features": _list(raw.get("features"), 5),
        "quality_notes": _list(raw.get("quality_notes"), 3),
        "model": model,
    }


# ---------------------------------------------------------------------------
# Where can we plant trees?
# ---------------------------------------------------------------------------

PLANT_KEYS = ("trees", "plantable", "built", "water", "other")
SPOT_KINDS = ("open_plot", "roadside", "park_or_lawn", "courtyard", "field_edge", "school_or_campus", "riverbank", "other")
PRIORITIES = ("high", "medium", "low")

PLANT_PROMPT = """You are helping residents find places to plant trees in a top-down satellite or aerial image,
often a Google Maps screenshot. Ignore map labels, pins, icons and app buttons; judge only the ground.

A grid of {rows} rows x {cols} columns is drawn on the image, each square labelled in its top-left corner
(column letter, A on the left; row number, 1 at the top), from A1 to {last}.

For EVERY square from A1 to {last}, estimate what percentage of its area is:
- trees: existing tree canopy
- plantable: open ground where trees could realistically be planted: bare or grassy empty plots, wide unpaved
  roadside verges and medians, open lawns and parks without trees, school or campus grounds, edges of fields,
  open courtyards, banks of streams or ponds
- built: buildings, roads, paved areas, parking, railways (not plantable)
- water: rivers, lakes, ponds, canals
- other: anything else, including actively farmed crop fields, sports pitches and construction in progress
The five numbers for each square must add up to 100. Work square by square. Be realistic: a narrow footpath or a
small gap between houses is not plantable.

Then list up to 8 of the best planting spots as boxes [ymin, xmin, ymax, xmax] on a 0-1000 scale around the open
ground itself. For each spot give a short label, its kind, a priority (high = large, open and clearly public, such as
a vacant plot, wide verge or park; low = small, awkward or possibly private), and a one-sentence reason.
Finish with a short headline, a two-sentence summary of the planting opportunity, and any image problems in quality_notes.
Do not guess the city, owners or exact distances.
"""


def _plant_schema() -> dict:
    share = {"type": "INTEGER"}
    return {
        "type": "OBJECT",
        "properties": {
            "image_kind": {"type": "STRING", "enum": list(IMAGE_KINDS)},
            "cells": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {"cell": {"type": "STRING"}, **{key: share for key in PLANT_KEYS}},
                    "required": ["cell", *PLANT_KEYS],
                },
            },
            "spots": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "label": {"type": "STRING"},
                        "kind": {"type": "STRING", "enum": list(SPOT_KINDS)},
                        "priority": {"type": "STRING", "enum": list(PRIORITIES)},
                        "reason": {"type": "STRING"},
                        "box_2d": {"type": "ARRAY", "items": {"type": "INTEGER"}},
                    },
                    "required": ["label", "kind", "priority", "reason", "box_2d"],
                },
            },
            "headline": {"type": "STRING"},
            "summary": {"type": "STRING"},
            "quality_notes": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": ["image_kind", "cells", "spots", "headline", "summary"],
    }


def assess_planting(image: Image.Image, rows: int, cols: int) -> dict:
    last = _label(rows - 1, cols - 1)
    raw, model = _call_gemini(
        grid_overlay(image, rows, cols), PLANT_PROMPT.format(rows=rows, cols=cols, last=last), _plant_schema(), AREA_CONFIG,
    )
    if not isinstance(raw, dict):
        raise VisionError("The image could not be read. Please try again.")
    shares = _cell_shares(raw.get("cells"), rows, cols, PLANT_KEYS)
    if shares is None:
        raise VisionError("The image could not be mapped. Try a clearer, top-down screenshot.", 422)
    spots = []
    items = raw.get("spots") if isinstance(raw.get("spots"), list) else []
    for item, region in zip(items, _regions_with_source(items)):
        if region is None:
            continue  # unusable box: drop the spot rather than mark the wrong place
        spots.append({
            **region,
            "kind": _choice(item.get("kind"), SPOT_KINDS, "other"),
            "priority": _choice(item.get("priority"), PRIORITIES, "medium"),
            "reason": _text(item.get("reason"), 220),
        })
    order = {"high": 0, "medium": 1, "low": 2}
    spots.sort(key=lambda spot: order[spot["priority"]])
    return {
        "image_kind": _choice(raw.get("image_kind"), IMAGE_KINDS, "other"),
        "cell_shares": [{key: round(value, 1) for key, value in cell.items()} for cell in shares],
        "spots": spots[:8],
        "headline": _text(raw.get("headline"), 140),
        "summary": _text(raw.get("summary"), 600),
        "quality_notes": _list(raw.get("quality_notes"), 3),
        "model": model,
    }


def _regions_with_source(values) -> list[dict]:
    """Like _regions, but keeps one entry per input item (None for unusable boxes) so details stay aligned."""
    aligned = []
    for item in values if isinstance(values, list) else []:
        region = _regions([item]) if isinstance(item, dict) else []
        aligned.append(region[0] if region else None)
    return aligned
