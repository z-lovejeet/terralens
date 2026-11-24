"""Sort my photos: group a batch of uploaded satellite land images."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from terralens.api.resources import Resources
from terralens.settings import MAX_UPLOAD
from terralens.sorting import MAX_CHOSEN_K, MAX_PHOTOS, MIN_PHOTOS, sort_photos
from terralens.uploads import decode_image

router = APIRouter(tags=["Sort my photos"])
log = logging.getLogger(__name__)
MIN_PHOTO_SIDE = 32


def _sort_job(items: list[tuple[str, bytes]], artifacts, requested_k: int | None) -> dict:
    photos = []
    for name, raw in items:
        try:
            photos.append((name, decode_image(raw, min_side=MIN_PHOTO_SIDE)))
        except HTTPException as error:
            raise HTTPException(error.status_code, f"{name}: {error.detail}") from None
    return sort_photos(photos, artifacts, requested_k)


@router.post("/sort-photos")
async def sort(
    request: Request,
    resources: Resources,
    files: Annotated[list[UploadFile] | None, File()] = None,
    groups: Annotated[str, Form()] = "auto",
):
    resources.limits.check(request, "sort", 8)
    if groups == "auto":
        requested_k = None
    elif groups.isdigit() and 2 <= int(groups) <= MAX_CHOSEN_K:
        requested_k = int(groups)
    else:
        raise HTTPException(422, f"Choose Auto or between 2 and {MAX_CHOSEN_K} groups.")
    files = files or []
    if not MIN_PHOTOS <= len(files) <= MAX_PHOTOS:
        for upload in files:
            await upload.close()
        raise HTTPException(422, f"Choose between {MIN_PHOTOS} and {MAX_PHOTOS} photos.")
    if requested_k is not None and requested_k >= len(files):
        raise HTTPException(422, "Choose fewer groups than photos.")
    items = []
    for upload in files:
        try:
            raw = await upload.read(MAX_UPLOAD + 1)
        finally:
            await upload.close()
        name = (upload.filename or f"photo-{len(items) + 1}")[:120]
        if not raw:
            raise HTTPException(422, f"{name} is empty.")
        if len(raw) > MAX_UPLOAD:
            raise HTTPException(413, f"{name} is larger than 8 MB.")
        items.append((name, raw))
    try:
        return await asyncio.get_running_loop().run_in_executor(resources.upload_worker, _sort_job, items, resources.artifacts, requested_k)
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    except FileNotFoundError:
        raise HTTPException(503, "Reference model artifacts are missing. Follow the study setup in README.md.") from None
    except Exception:
        log.exception("Photo sorting failed")
        raise HTTPException(500, "The photos could not be sorted. Try again with fewer or different photos.") from None
