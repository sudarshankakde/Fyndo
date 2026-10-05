import hashlib
import time
from typing import Any, Dict
import cloudinary.utils
from app.core.config import settings


class CloudinaryService:
    @staticmethod
    def generate_upload_signature(folder: str = "reels", resource_type: str = "video") -> Dict[str, Any]:
        """
        Generates signed parameters for direct client upload to Cloudinary.
        Bypasses server file buffering completely.
        """
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
