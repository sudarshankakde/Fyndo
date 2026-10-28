import hashlib
import os
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
    "avatars": {"image", "auto"},
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

    @staticmethod
    def get_optimized_video_url(url: Optional[str]) -> Optional[str]:
        """
        Injects Cloudinary video delivery optimizations (f_auto,q_auto) if URL is on Cloudinary
        and not already transformed.
        """
        if not url or "res.cloudinary.com" not in url or "/video/upload/" not in url:
            return url
        if "f_auto" in url or "q_auto" in url or "sp_auto" in url:
            return url
        return url.replace("/video/upload/", "/video/upload/f_auto,q_auto/")

    @staticmethod
    def get_hls_url(
        public_id: Optional[str] = None,
        video_url: Optional[str] = None,
        cloud_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generates an adaptive HLS streaming URL (.m3u8) using Cloudinary streaming profile sp_auto.
        Can derive from public_id or from a standard Cloudinary video upload URL.
        """
        cloud = cloud_name or settings.CLOUDINARY_CLOUD_NAME or "fyndo-cloud"
        if public_id:
            pid = public_id.rsplit(".", 1)[0] if "." in public_id else public_id
            return f"https://res.cloudinary.com/{cloud}/video/upload/sp_auto/{pid}.m3u8"

        if video_url and "res.cloudinary.com" in video_url and "/video/upload/" in video_url:
            parts = video_url.split("/video/upload/")
            base = parts[0]
            rest = parts[1]
            if "," in rest.split("/")[0] or rest.startswith("f_") or rest.startswith("q_") or rest.startswith("sp_"):
                rest = "/".join(rest.split("/")[1:])
            rest_without_ext = rest.rsplit(".", 1)[0] if "." in rest else rest
            return f"{base}/video/upload/sp_auto/{rest_without_ext}.m3u8"

        return None

    @staticmethod
    def resolve_to_cloudinary_url(url: Optional[str], folder: str = "logos") -> Optional[str]:
        """
        If the url is local (e.g. /uploads/..., http://localhost:.../uploads/...),
        checks if the file exists in local storage and uploads it to Cloudinary.
        Returns the Cloudinary CDN URL, or the original url if upload fails / not configured.
        """
        if not url:
            return url
        if "res.cloudinary.com" in url or (url.startswith("https://") and "localhost" not in url and "127.0.0.1" not in url and "10.0.2.2" not in url):
            return url
        if not _ensure_cloudinary_configured():
            return url

        upload_idx = url.find("/uploads/")
        if upload_idx == -1:
            return url
        rel_path = url[upload_idx + 1:]  # e.g. "uploads/logos/..."

        backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        local_file_path = os.path.join(backend_root, rel_path)

        if not os.path.exists(local_file_path):
            return url

        try:
            cloud_res = CloudinaryService.upload_file(local_file_path, folder=folder, resource_type="image")
            if cloud_res and cloud_res.get("url"):
                return cloud_res["url"]
        except Exception:
            pass

        return url
