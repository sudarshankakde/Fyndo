from typing import Optional
from pydantic import BaseModel, Field


class SignUploadRequest(BaseModel):
    folder: str = Field("reels", description="reels or kyc")
    resource_type: str = Field("video", description="video, image, or auto")


class SignUploadResponse(BaseModel):
    cloud_name: str
    api_key: str
    timestamp: int
    signature: str
    folder: str
    upload_url: str
