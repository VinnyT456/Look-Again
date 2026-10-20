from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from look_again.serve.classifier import UnreadableImage
from look_again.serve.schemas import ClassifyResponse

router = APIRouter(prefix="/v1")

MAX_IMAGE_BYTES = 20 * 1024 * 1024


class Base64Body(BaseModel):
    image_base64: str


async def _image_bytes(request: Request) -> bytes:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if upload is None or isinstance(upload, str):
            raise HTTPException(422, "Send the image in a form field named 'file'.")
        data = await upload.read(MAX_IMAGE_BYTES + 1)
    elif content_type.startswith("application/json"):
        body = Base64Body.model_validate(await request.json())
        try:
            data = base64.b64decode(body.image_base64, validate=True)
        except binascii.Error as error:
            raise HTTPException(422, "image_base64 isn't valid base64.") from error
    else:
        raise HTTPException(415, "Send multipart/form-data with 'file', or JSON with 'image_base64'.")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image is larger than 20 MB.")
    if not data:
        raise HTTPException(422, "The image is empty.")
    return data


@router.post("/classify", response_model=ClassifyResponse)
async def classify(request: Request) -> ClassifyResponse:
    detector = request.app.state.detector
    if detector is None:
        raise HTTPException(503, "The detector model isn't loaded.")
    data = await _image_bytes(request)
    try:
        return await run_in_threadpool(detector.classify_bytes, data)
    except UnreadableImage as error:
        raise HTTPException(422, "Couldn't read that image.") from error
