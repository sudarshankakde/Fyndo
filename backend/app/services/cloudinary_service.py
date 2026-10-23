import hashlib
import time
from typing import Any, Dict, Optional
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from app.core.config import settings

ALLOWED_UPLOAD_TARGETS = {
    "reels": {"video", "image", "auto"},
    "kyc": {"image", "auto"},
    "profile": {"image", "auto"},
    "stores": {"image", "auto"},
    "covers": {"image", "auto"},
    "logos": {"image", "auto"},
    "showcase": {"video", "image", "auto"},
}


def _ensure_cloudinary_configured() -> bool:
    if settings.CLOUDINARY_API_SECRET and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_CLOUD_NAME:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        return True
    return False


def validate_upload_target(folder: str, resource_type: str) -> tuple[str, str]:
    normalized_folder = folder.strip().lower()
    normalized_resource = resource_type.strip().lower()
    allowed_resources = ALLOWED_UPLOAD_TARGETS.get(normalized_folder)
    if not allowed_resources or normalized_resource not in allowed_resources:
        raise ValueError("Unsupported upload folder/resource type combination.")
    return normalized_folder, normalized_resource


class CloudinaryService:
    @staticmethod
    def generate_upload_signature(folder: str = "reels", resource_type: str = "video") -> Dict[str, Any]:
        """
        Generates signed parameters for direct client upload to Cloudinary.
        Bypasses server file buffering completely.
        """
        folder, resource_type = validate_upload_target(folder, resource_type)
        timestamp = int(time.time())
        params_to_sign = {
            "folder": f"fyndo/{folder}",
            "timestamp": timestamp,
        }

        # If Cloudinary credentials exist, sign with Cloudinary SDK
        if settings.CLOUDINARY_API_SECRET and settings.CLOUDINARY_API_KEY:
            signature = cloudinary.utils.api_sign_request(
                params_to_sign,
                settings.CLOUDINARY_API_SECRET
            )
            cloud_name = settings.CLOUDINARY_CLOUD_NAME or "fyndo-cloud"
            api_key = settings.CLOUDINARY_API_KEY
        else:
            # Dev mock signature
            raw = f"folder=fyndo/{folder}&timestamp={timestamp}mock_secret"
            signature = hashlib.sha1(raw.encode("utf-8")).hexdigest()
            cloud_name = "fyndo-dev-mock"
            api_key = "mock_api_key_12345"

        upload_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/upload"

        return {
            "cloud_name": cloud_name,
            "api_key": api_key,
            "timestamp": timestamp,
            "signature": signature,
            "folder": f"fyndo/{folder}",
            "upload_url": upload_url
        }

    @staticmethod
    def upload_file(
        file_path: str, 
        folder: str = "reels", 
        resource_type: str = "video"
    ) -> Optional[Dict[str, Any]]:
        """
        Performs a server-side upload to Cloudinary.
        Used for fallback or admin-initiated uploads.
        """
        if not _ensure_cloudinary_configured():
            return None

        try:
            folder, resource_type = validate_upload_target(folder, resource_type)
            result = cloudinary.uploader.upload(
                file_path,
                folder=f"fyndo/{folder}",
                resource_type=resource_type
            )
            return {
                "url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "duration": result.get("duration"),
            }
        except Exception as exc:
            from app.services.media_service import logger
            logger.error(f"Cloudinary server-side upload failed: {exc}")
            return None
