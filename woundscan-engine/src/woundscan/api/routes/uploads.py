"""Presigned upload URL endpoints for binary capture data."""
from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from woundscan.api.auth import get_identity
from woundscan.auth.identity import Identity

router = APIRouter(prefix="/uploads", tags=["uploads"])


class UploadRequest(BaseModel):
    wound_id: UUID
    artifact_type: str  # "rgb" | "depth_burst" | "polarized" | "multispectral"
    file_count: int = 1


class PresignedUpload(BaseModel):
    s3_key: str
    upload_url: str
    method: str = "PUT"


class UploadResponse(BaseModel):
    uploads: list[PresignedUpload]


@router.post("/presigned", response_model=UploadResponse)
def get_presigned_uploads(
    request: UploadRequest,
    identity: Identity = Depends(get_identity),
) -> UploadResponse:
    """Issue presigned PUT URLs.

    Production wires `S3Storage` here. The dev path returns deterministic
    keys and a placeholder URL so the iOS app's flow can be tested
    without S3.
    """
    uploads = []
    for i in range(request.file_count):
        key = f"captures/{request.wound_id}/{request.artifact_type}/{uuid4()}-{i}.bin"
        uploads.append(
            PresignedUpload(
                s3_key=key,
                upload_url=f"http://localhost:9000/{key}",
            )
        )
    return UploadResponse(uploads=uploads)
