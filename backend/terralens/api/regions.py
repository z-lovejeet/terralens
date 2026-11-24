"""Map my image: split one uploaded satellite image into regions."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from terralens.api.resources import Resources
from terralens.regions import MAX_REGIONS, MIN_SIDE, map_regions
from terralens.settings import MAX_UPLOAD
from terralens.uploads import decode_image

router = APIRouter(tags=["Map my image"])
log = logging.getLogger(__name__)


def _job(raw: bytes, artifacts, requested_k: int | None) -> dict:
    return map_regions(decode_image(raw, min_side=MIN_SIDE), artifacts, requested_k)


@router.post("/map-regions")
async def regions(
    request: Request,
    resources: Resources,
    file: Annotated[UploadFile | None, File()] = None,
    count: Annotated[str, Form()] = "auto",
):
    resources.limits.check(request, "regions", 12)
    if count == "auto":
        requested_k = None
    elif count.isdigit() and 2 <= int(count) <= MAX_REGIONS:
        requested_k = int(count)
    else:
        raise HTTPException(422, f"Choose Auto or between 2 and {MAX_REGIONS} regions.")
    if file is None:
        raise HTTPException(422, "Choose a satellite image.")
    try:
        raw = await file.read(MAX_UPLOAD + 1)
    finally:
        await file.close()
    if not raw:
        raise HTTPException(422, "The image is empty.")
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "The image must be smaller than 8 MB.")
    try:
        return await asyncio.get_running_loop().run_in_executor(resources.upload_worker, _job, raw, resources.artifacts, requested_k)
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    except FileNotFoundError:
        raise HTTPException(503, "Reference model artifacts are missing. Follow the study setup in README.md.") from None
    except Exception:
        log.exception("Region mapping failed")
        raise HTTPException(500, "The image could not be mapped. Try another image.") from None
