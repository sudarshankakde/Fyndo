import os
import shutil
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.media import SignUploadRequest, SignUploadResponse
from app.services.cloudinary_service import CloudinaryService

router = APIRouter()

# Local upload directory setup
UPLOAD_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../uploads"))
os.makedirs(UPLOAD_ROOT, exist_ok=True)


@router.post("/media/sign-upload", response_model=ResponseEnvelope[SignUploadResponse])
async def get_upload_signature(
    request: SignUploadRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generates a secure cryptographic signature allowing direct client uploads
    to Cloudinary. Bypasses backend video bandwidth consumption.
    """
    params = CloudinaryService.generate_upload_signature(
        folder=request.folder,
        resource_type=request.resource_type
    )
    return ResponseEnvelope(
        data=SignUploadResponse(**params),
        message="Upload signature generated"
    )


@router.post("/media/upload", response_model=ResponseEnvelope[dict])
async def upload_media_file(
    file: UploadFile = File(...),
    folder: str = Form("reels"),
):
    """
    Direct file upload endpoint for user reels and store media.
    Stores the uploaded video/image in the local uploads directory
    and returns an accessible URL for streaming and thumbnail preview.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload."
        )

    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = {".mp4", ".mov", ".webm", ".m4v", ".mkv", ".jpg", ".jpeg", ".png", ".webp"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(allowed_exts))}"
        )

    target_dir = os.path.join(UPLOAD_ROOT, folder)
    os.makedirs(target_dir, exist_ok=True)

    unique_filename = f"{uuid.uuid4().hex[:12]}_{os.path.basename(file.filename)}"
    destination_path = os.path.join(target_dir, unique_filename)

    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(destination_path)
    public_url = f"/uploads/{folder}/{unique_filename}"

    return ResponseEnvelope(
        data={
            "url": public_url,
            "filename": unique_filename,
            "size_bytes": file_size,
            "folder": folder,
        },
        message="File uploaded successfully."
    )

