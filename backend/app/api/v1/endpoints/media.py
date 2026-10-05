from fastapi import APIRouter, Depends
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.media import SignUploadRequest, SignUploadResponse
from app.services.cloudinary_service import CloudinaryService

router = APIRouter()


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
