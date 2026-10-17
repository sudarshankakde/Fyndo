"""Media storage + processing pipeline for reels, thumbnails and KYC docs.

Responsibilities:
  * enforce size ceilings and per-folder content rules,
  * stream uploads to disk with a hard byte cap (no full-file buffering),
  * verify real content type from magic bytes (defeats extension spoofing),
  * derive a poster thumbnail from the first video frame via ffmpeg when
    available, degrading gracefully when the binary is absent.

Cloudinary remains the production CDN (see docs/05_System_Architecture.md
section 2.2); this module is the hardened local/dev + fallback path.
"""
import hashlib
import logging
import os
import shutil
import subprocess
import uuid
from typing import Dict, Optional

from fastapi import UploadFile

from app.core.config import settings
from app.services.cloudinary_service import CloudinaryService

logger = logging.getLogger("fyndo.media")

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v", ".mkv"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS

_FFMPEG_AVAILABLE: Optional[bool] = None


class MediaValidationError(Exception):
    """Raised when an upload fails validation. `status_code` maps to HTTP."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def upload_root() -> str:
    """Absolute path of the configured upload root."""
    configured = settings.UPLOAD_ROOT
    if not os.path.isabs(configured):
        configured = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", configured)
        )
    os.makedirs(configured, exist_ok=True)
    return configured


def sniff_media_kind(header: bytes) -> Optional[str]:
    """Detects 'video'/'image' from the first bytes of a file, or None."""
    if len(header) < 12:
        return None
    if header[:4] == b"\x89PNG":
        return "image"
    if header[:3] == b"\xff\xd8\xff":
        return "image"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image"
    if header[4:8] == b"ftyp":
        return "video"  # mp4 / m4v / mov family
    if header[:4] == b"\x1a\x45\xdf\xa3":
        return "video"  # matroska / webm
    return None


def max_bytes_for(folder: str, content_type: Optional[str]) -> int:
    is_image = bool(content_type and content_type.startswith("image/"))
    megabytes = settings.MEDIA_MAX_IMAGE_MB if is_image or folder == "kyc" else settings.MEDIA_MAX_VIDEO_MB
    return megabytes * 1024 * 1024


def resolve_extension(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise MediaValidationError(
            f"Unsupported file format '{ext or 'unknown'}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return ext


def _write_stream(file_obj, destination: str, max_bytes: int) -> int:
    """Streams `file_obj` to disk, aborting (and cleaning up) beyond max_bytes."""
    written = 0
    chunk_size = settings.MEDIA_CHUNK_BYTES
    try:
        with open(destination, "wb") as buffer:
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise MediaValidationError(
                        f"File exceeds the maximum allowed size of "
                        f"{max_bytes // (1024 * 1024)} MB.",
                        status_code=413,
                    )
                buffer.write(chunk)
    except MediaValidationError:
        if os.path.exists(destination):
            os.remove(destination)
        raise
    except Exception:
        if os.path.exists(destination):
            os.remove(destination)
        raise
    return written


def ffmpeg_available() -> bool:
    global _FFMPEG_AVAILABLE
    if _FFMPEG_AVAILABLE is None:
        _FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
        if not _FFMPEG_AVAILABLE:
            logger.info("ffmpeg not found on PATH: server-side thumbnails disabled.")
    return _FFMPEG_AVAILABLE


def generate_video_thumbnail(video_path: str, output_path: str) -> bool:
    """Extracts a poster frame converted to a 9:16-safe WEBP. Best effort."""
    if not ffmpeg_available():
        return False
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-ss", "00:00:01", "-i", video_path,
                "-frames:v", "1",
                "-vf", "scale=720:-2",
                output_path,
            ],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as exc:
        logger.warning(f"Thumbnail generation failed for {video_path}: {exc}")
        return False


def store_upload(upload: UploadFile, folder: str) -> Dict[str, object]:
    """Validates and persists an upload. Returns a metadata dict."""
    if not upload.filename:
        raise MediaValidationError("No filename provided in upload.")

    ext = resolve_extension(upload.filename)
    expected_kind = "image" if ext in IMAGE_EXTENSIONS else "video"
    limit = max_bytes_for(folder, upload.content_type)

    target_dir = os.path.join(upload_root(), folder)
    os.makedirs(target_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    destination = os.path.join(target_dir, unique_name)

    size_bytes = _write_stream(upload.file, destination, limit)

    with open(destination, "rb") as handle:
        header = handle.read(32)
    actual_kind = sniff_media_kind(header)
    if actual_kind is None or actual_kind != expected_kind:
        os.remove(destination)
        raise MediaValidationError(
            "The file content does not match its extension. Upload the original video or image."
        )

    checksum = hashlib.sha256()
    with open(destination, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(block)

    thumbnail_url = None
    if expected_kind == "video":
        thumb_name = f"{uuid.uuid4().hex[:12]}.webp"
        thumb_path = os.path.join(target_dir, thumb_name)
        if generate_video_thumbnail(destination, thumb_path):
            thumbnail_url = f"/uploads/{folder}/{thumb_name}"

    # Production path: Sync to Cloudinary if configured
    cloudinary_data = CloudinaryService.upload_file(destination, folder, expected_kind)
    if cloudinary_data:
        # If Cloudinary upload succeeded, we also try to upload the thumbnail if it exists
        final_url = cloudinary_data["url"]
        final_thumb = thumbnail_url
        public_id = cloudinary_data["public_id"]
        
        if thumbnail_url and os.path.exists(os.path.join(upload_root(), thumbnail_url.lstrip("/"))):
            thumb_cloud = CloudinaryService.upload_file(
                os.path.join(upload_root(), thumbnail_url.lstrip("/")), 
                folder, 
                "image"
            )
            if thumb_cloud:
                final_thumb = thumb_cloud["url"]
        
        return {
            "url": final_url,
            "thumbnail_url": final_thumb,
            "cloudinary_public_id": public_id,
            "filename": unique_name,
            "size_bytes": size_bytes,
            "folder": folder,
            "content_type": upload.content_type or "application/octet-stream",
            "checksum_sha256": checksum.hexdigest(),
        }

    return {
        "url": f"/uploads/{folder}/{unique_name}",
        "filename": unique_name,
        "size_bytes": size_bytes,
        "folder": folder,
        "content_type": upload.content_type or "application/octet-stream",
        "checksum_sha256": checksum.hexdigest(),
        "thumbnail_url": thumbnail_url,
    }
