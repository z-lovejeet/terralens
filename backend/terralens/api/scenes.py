"""Everyday tools: Check my area, Crisis Radar single-image scan and before/after comparison."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from PIL import Image

from terralens.api.resources import Resources
from terralens.landscan import MIN_SCENE_SIDE, area_check, area_report, change_check, crop_to_grid, plan_grid
from terralens.settings import MAX_UPLOAD
from terralens.uploads import decode_image
from terralens.planting import planting_report
from terralens.vision import VisionError, assess_area, assess_crisis, assess_planting

router = APIRouter(tags=["Everyday tools"])
log = logging.getLogger(__name__)
Detail = Literal["low", "medium", "high"]
AreaWidth = Literal["street", "colony", "neighbourhood", "large"]


async def _read_upload(file: UploadFile | None, label: str) -> bytes:
    if file is None:
        raise HTTPException(422, f"Choose the {label} image.")
    try:
        raw = await file.read(MAX_UPLOAD + 1)
    finally:
        await file.close()
    if not raw:
        raise HTTPException(422, f"The {label} image is empty.")
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "Each image must be smaller than 8 MB.")
    return raw


async def _run(executor, function, *args):
    try:
        return await asyncio.get_running_loop().run_in_executor(executor, function, *args)
    except (HTTPException, VisionError):
        raise
    except FileNotFoundError:
        raise HTTPException(503, "Reference model artifacts are missing. Follow the study setup in README.md.") from None
    except Exception:
        log.exception("Scene scan failed")
        raise HTTPException(500, "The scan could not be completed. Try another image.") from None


def _area_prepare(raw: bytes, detail: str) -> tuple[Image.Image, int, int, list[str]]:
    scene, rows, cols, warnings, _ = _prepare_grid(raw, detail)
    return scene, rows, cols, warnings


def _prepare_grid(raw: bytes, detail: str) -> tuple[Image.Image, int, int, list[str], int]:
    """Decode, crop to an even grid, and report the original width (the user's scale refers to it)."""
    image = decode_image(raw, min_side=MIN_SCENE_SIDE)
    grid = plan_grid(image.width, image.height, detail)
    scene = crop_to_grid(image, grid)
    warnings = []
    if scene.size != image.size:
        warnings.append(f"Edges trimmed from {image.width}×{image.height} to {scene.width}×{scene.height} so the grid fits evenly.")
    return scene, grid.rows, grid.cols, warnings, image.width


def _change_job(before: bytes, after: bytes, artifacts, detail: str) -> dict:
    return change_check(
        decode_image(before, min_side=MIN_SCENE_SIDE), decode_image(after, min_side=MIN_SCENE_SIDE), artifacts, detail,
    )


def _scan_prepare(raw: bytes, artifacts) -> tuple[Image.Image, dict]:
    """Crop once so the AI's marked areas and the land-cover grid share one frame."""
    image = decode_image(raw, min_side=MIN_SCENE_SIDE)
    scene = crop_to_grid(image, plan_grid(image.width, image.height, "medium"))
    return scene, area_check(scene, artifacts, "medium")


@router.post("/area-check")
async def check_area(
    request: Request,
    resources: Resources,
    file: Annotated[UploadFile | None, File()] = None,
    detail: Annotated[Detail, Form()] = "high",
):
    resources.limits.check(request, "scene", 12)
    raw = await _read_upload(file, "satellite")
    scene, rows, cols, warnings = await _run(resources.upload_worker, _area_prepare, raw, detail)
    try:
        reading = await _run(resources.vision_worker, assess_area, scene, rows, cols)
        return area_report(scene, rows, cols, reading, warnings)
    except VisionError as error:
        raise HTTPException(error.status, error.message) from None
    finally:
        scene.close()


@router.post("/change-check")
async def check_change(
    request: Request,
    resources: Resources,
    before: Annotated[UploadFile | None, File()] = None,
    after: Annotated[UploadFile | None, File()] = None,
    detail: Annotated[Detail, Form()] = "medium",
):
    resources.limits.check(request, "scene", 12)
    before_raw = await _read_upload(before, "before")
    after_raw = await _read_upload(after, "after")
    return await _run(resources.upload_worker, _change_job, before_raw, after_raw, resources.artifacts, detail)


@router.post("/crisis-scan")
async def crisis_scan(request: Request, resources: Resources, file: Annotated[UploadFile | None, File()] = None):
    resources.limits.check(request, "crisis", 6)
    raw = await _read_upload(file, "satellite")
    scene, land = await _run(resources.upload_worker, _scan_prepare, raw, resources.artifacts)
    try:
        assessment, vision_error = await _run(resources.vision_worker, assess_crisis, scene), None
    except VisionError as error:
        assessment, vision_error = None, {"message": error.message, "status": error.status}
    finally:
        scene.close()
    return {
        "image": land["image"],
        "assessment": assessment,
        "vision_error": vision_error,
        "land": {key: land[key] for key in ("run_id", "grid", "tiles", "breakdown", "reliability", "groups", "method")},
    }


@router.post("/plant-check")
async def plant_check(
    request: Request,
    resources: Resources,
    file: Annotated[UploadFile | None, File()] = None,
    area_width: Annotated[AreaWidth, Form()] = "colony",
):
    resources.limits.check(request, "scene", 12)
    raw = await _read_upload(file, "satellite")
    scene, rows, cols, warnings, original_width = await _run(resources.upload_worker, _prepare_grid, raw, "high")
    try:
        reading = await _run(resources.vision_worker, assess_planting, scene, rows, cols)
        return planting_report(scene, original_width, rows, cols, reading, area_width, warnings)
    except VisionError as error:
        raise HTTPException(error.status, error.message) from None
    finally:
        scene.close()
