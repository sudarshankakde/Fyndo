"""Media upload endpoints.

Two supported flows, both hardened:

  * `/media/sign-upload` — issues a short-lived Cloudinary signature so the
    client uploads large 9:16 reels straight to the CDN (production path,
    documented in docs/05_System_Architecture.md).
  * `/media/upload` — streams the file to local storage through
    `app/services/media_service.py`, enforcing size ceilings, magic-byte
    content sniffing and an optional server-generated video poster.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.v1.endpoints.auth import AuthContext, get_auth_context
from app.core.context import set_user_id
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.config import settings
from app.models.merchant import MerchantStaff
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.media import (
    ReelEditRequest,
    ReelProcessResponse,
    SignUploadRequest,
    SignUploadResponse,
)
from app.services.cloudinary_service import CloudinaryService, validate_upload_target
from app.services.media_service import MediaValidationError, store_upload
from app.services.reel_processing_service import process_reel

router = APIRouter()


async def get_media_uploader(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    if auth.role == "ROLE_CASHIER":
        staff = await db.get(MerchantStaff, auth.subject_id)
        if not staff or not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Staff account is inactive or not found.",
            )
        if not (staff.can_upload_reels or getattr(staff, "can_manage_content", False)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff account is not authorized to upload or manage media.",
            )
        return auth

    result = await db.execute(select(User).where(User.id == auth.subject_id))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or suspended.",
        )
    set_user_id(user.id)
    return auth


@router.post("/media/sign-upload", response_model=ResponseEnvelope[SignUploadResponse])
async def get_upload_signature(
    request: SignUploadRequest,
    _: AuthContext = Depends(get_media_uploader),
    __: None = Depends(rate_limit("media_sign", 60)),
):
    """Generates a signature allowing direct, bandwidth-free client uploads."""
    try:
        folder, resource_type = validate_upload_target(request.folder, request.resource_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    params = CloudinaryService.generate_upload_signature(
        folder=folder, resource_type=resource_type
    )
    return ResponseEnvelope(
        data=SignUploadResponse(**params),
        message="Upload signature generated",
    )


@router.post("/media/upload", response_model=ResponseEnvelope[dict])
async def upload_media_file(
    file: UploadFile | str = File(...),
    folder: str = Form("reels"),
    sync_cdn: bool = Form(True),
    _: AuthContext = Depends(get_media_uploader),
    __: None = Depends(rate_limit("media_upload", 30)),
):
    """Streams a reel/KYC file to storage with validation and thumbnail export."""
    if isinstance(file, str):
        if file.startswith("http://") or file.startswith("https://"):
            return ResponseEnvelope(data={"url": file, "thumbnail_url": file}, message="URL accepted.")
        if file.startswith("/uploads") or file.startswith("uploads/"):
            return ResponseEnvelope(data={"url": file, "thumbnail_url": file}, message="Existing media accepted.")
        if file.startswith("data:"):
            import base64
            import io
            header, encoded = file.split(",", 1)
            content_type = header.split(";")[0].replace("data:", "")
            ext = content_type.split("/")[-1] if "/" in content_type else "jpg"
            data_bytes = base64.b64decode(encoded)
            file = UploadFile(
                file=io.BytesIO(data_bytes),
                filename=f"upload.{ext}",
                headers={"content-type": content_type}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid media upload payload: string received instead of binary file."
            )

    kind = "image" if (file.content_type or "").startswith("image/") else "video"
    try:
        folder, _ = validate_upload_target(folder, kind)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        # Disk writes and the ffmpeg poster extraction are blocking, so they run
        # in a worker thread to keep the event loop free for other requests.
        result = await run_in_threadpool(store_upload, file, folder, sync_cdn)
    except MediaValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return ResponseEnvelope(data=result, message="File uploaded successfully.")


@router.post("/media/reels/process", response_model=ResponseEnvelope[ReelProcessResponse])
async def process_merchant_reel(
    request: ReelEditRequest,
    _: AuthContext = Depends(get_media_uploader),
    __: None = Depends(rate_limit("media_reel_process", 20)),
):
    """Applies trim / crop / cover / mute / look edits to a merchant's reel."""
    try:
        result = await run_in_threadpool(process_reel, request)
    except MediaValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    return ResponseEnvelope(
        data=ReelProcessResponse(**result), message="Your video is ready.",
    )


@router.get("/media/config", response_model=ResponseEnvelope[dict])
async def media_pipeline_config(_: AuthContext = Depends(get_media_uploader)):
    """Exposes the active upload limits so clients can pre-validate files."""
    return ResponseEnvelope(
        data={
            "max_video_mb": settings.MEDIA_MAX_VIDEO_MB,
            "max_image_mb": settings.MEDIA_MAX_IMAGE_MB,
            "reels_folder": "reels",
            "kyc_folder": "kyc",
        }
    )

