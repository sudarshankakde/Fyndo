from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


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


# -- Reel editor contracts (server-side ffmpeg render pipeline) ----------------
ReelLookPreset = Literal["original", "bright", "warm", "cool", "mono", "vivid"]


class ReelCropBox(BaseModel):
    """Normalised crop rectangle (fractions of the source frame)."""

    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    w: float = Field(..., gt=0.0, le=1.0)
    h: float = Field(..., gt=0.0, le=1.0)

    @model_validator(mode="after")
    def _within_frame(self) -> "ReelCropBox":
        if self.x + self.w > 1.0001 or self.y + self.h > 1.0001:
            raise ValueError("Crop rectangle lies outside the source frame.")
        return self


class ReelLook(BaseModel):
    preset: ReelLookPreset = "original"
    brightness: int = Field(0, ge=-100, le=100)
    contrast: int = Field(0, ge=-100, le=100)
    saturation: int = Field(0, ge=-100, le=100)


class ReelEditRequest(BaseModel):
    source_url: str
    trim_start: float = Field(..., ge=0.0)
    trim_end: float = Field(..., gt=0.0)
    crop: Optional[ReelCropBox] = None
    cover_time: Optional[float] = Field(None, ge=0.0)
    mute: bool = False
    look: Optional[ReelLook] = None
    previous_output_url: Optional[str] = None

    @model_validator(mode="after")
    def _trim_order(self) -> "ReelEditRequest":
        if self.trim_end <= self.trim_start:
            raise ValueError("trim_end must be greater than trim_start.")
        return self


class ReelProcessResponse(BaseModel):
    url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: int
    width: int
    height: int
    size_bytes: int
