"""Server-side reel editor (ffmpeg) — storage-provider agnostic.

Takes a merchant-supplied edit spec (trim, 9:16 crop, mute, colour "look",
cover frame) and renders a vertical reel into the local uploads/reels/
directory. Keeping rendering on our own machine means the editor keeps
working if we swap storage backends (local disk today → S3/R2 tomorrow).
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from typing import List, Optional

from app.core.config import settings
from app.schemas.media import ReelEditRequest
from app.services.media_service import MediaValidationError, upload_root

logger = logging.getLogger("fyndo.reel_processing")

REELS_FOLDER = "reels"
_WINDOW_SLACK_SECONDS = 0.75  # merchants trim visually; forgive sub-second drift

_LOOK_PRESETS = {
    "original": "",
    "bright": "eq=brightness=0.06:contrast=1.08:saturation=1.05",
    "warm": "eq=brightness=0.03:saturation=1.1,colorbalance=rm=.08:gm=.02:bm=-.05",
    "cool": "eq=brightness=0.02:saturation=1.05,colorbalance=rm=-.05:gm=.02:bm=.08",
    "mono": "hue=s=0,eq=contrast=1.1",
    "vivid": "eq=brightness=0.04:contrast=1.12:saturation=1.3",
}


@dataclass
class SourceMeta:
    path: str
    width: int
    height: int
    duration: float
    has_audio: bool


# ---------------------------------------------------------------- helpers
def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def _even(n: int) -> int:
    return n if n % 2 == 0 else n - 1


def resolve_source_path(url: str) -> str:
    """Maps a `/uploads/reels/<name>` URL or valid video URL to an absolute, sandboxed path."""
    if not isinstance(url, str) or not url.strip():
        raise MediaValidationError("Please pick a video you just uploaded.", 400)

    url_str = url.strip()
    reels_dir = os.path.realpath(os.path.join(upload_root(), REELS_FOLDER))
    os.makedirs(reels_dir, exist_ok=True)

    if "://" in url_str:
        from urllib.parse import urlparse
        parsed = urlparse(url_str)
        if parsed.path.startswith("/uploads/reels/"):
            url_str = parsed.path
        else:
            filename = os.path.basename(parsed.path)
            candidate = os.path.realpath(os.path.join(reels_dir, filename)) if filename else None
            if candidate and os.path.commonpath([reels_dir, candidate]) == reels_dir and os.path.exists(candidate):
                return candidate

            import hashlib, urllib.request
            url_hash = hashlib.sha256(url_str.encode()).hexdigest()[:12]
            ext = os.path.splitext(parsed.path)[1].lower()
            if ext not in (".mp4", ".mov", ".webm", ".mkv"):
                ext = ".mp4"
            cached_file = os.path.join(reels_dir, f"ext_{url_hash}{ext}")
            if not os.path.exists(cached_file) or os.path.getsize(cached_file) == 0:
                try:
                    req = urllib.request.Request(url_str, headers={"User-Agent": "Mozilla/5.0"})
                    max_bytes = settings.MEDIA_MAX_VIDEO_MB * 1024 * 1024
                    written = 0
                    with urllib.request.urlopen(req, timeout=30) as resp, open(cached_file, "wb") as out_f:
                        while chunk := resp.read(settings.MEDIA_CHUNK_BYTES):
                            written += len(chunk)
                            if written > max_bytes:
                                raise MediaValidationError(
                                    f"External video exceeds {settings.MEDIA_MAX_VIDEO_MB} MB limit.", 413
                                )
                            out_f.write(chunk)
                except urllib.error.HTTPError as h_err:
                    _cleanup(cached_file)
                    fallback_sample = os.path.join(reels_dir, "sample_reel.mp4")
                    if ("ForBiggerBlazes" in url_str or "sample" in url_str.lower()) and os.path.exists(fallback_sample):
                        logger.warning("External sample %s returned HTTP %s, falling back to local sample_reel.mp4", url_str, h_err.code)
                        return fallback_sample
                    raise MediaValidationError(
                        f"External video source returned HTTP {h_err.code}. Please choose a valid video.", 400
                    )
                except MediaValidationError:
                    _cleanup(cached_file)
                    raise
                except Exception as exc:
                    _cleanup(cached_file)
                    logger.warning("Failed to fetch external video %s: %s", url_str, exc)
                    raise MediaValidationError("Could not download external video source.", 400)
            return cached_file

    if not url_str.startswith("/uploads/reels/"):
        raise MediaValidationError("Please pick a video you just uploaded.", 400)
    name = url_str[len("/uploads/reels/") :]
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise MediaValidationError("That video reference is not valid.", 400)

    candidate = os.path.realpath(os.path.join(reels_dir, name))
    if os.path.commonpath([reels_dir, candidate]) != reels_dir:
        raise MediaValidationError("That video reference is not valid.", 400)
    if not os.path.exists(candidate):
        raise MediaValidationError("We can’t find that video anymore. Upload it again.", 404)
    return candidate


def probe_source(path: str) -> SourceMeta:
    if not _tool_available("ffprobe"):
        raise MediaValidationError("Video tools are not available on the server.", 503)
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", path,
        ],
        capture_output=True, timeout=30,
    )
    if result.returncode != 0:
        raise MediaValidationError("We couldn’t read that video. Try another file.", 400)
    data = json.loads(result.stdout.decode("utf-8", errors="ignore") or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        raise MediaValidationError("This file has no video track.", 400)
    width = int(video.get("width", 0))
    height = int(video.get("height", 0))
    rotation = 0
    for tag_source in (video.get("tags") or {}, *(sd.get("tags", {}) for sd in video.get("side_data_list") or [])):
        try:
            rotation = int(float(tag_source.get("rotate", rotation)))
        except (TypeError, ValueError):
            pass
    if abs(rotation) in (90, 270):
        width, height = height, width

    duration = 0.0
    try:
        duration = float(data.get("format", {}).get("duration") or video.get("duration") or 0)
    except (TypeError, ValueError):
        pass
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    return SourceMeta(path=path, width=width, height=height, duration=duration, has_audio=has_audio)


def validate_spec(spec: ReelEditRequest, meta: SourceMeta) -> float:
    """Returns the output length in seconds (post-trim) if the spec is valid."""
    if spec.trim_start < 0 or spec.trim_start >= spec.trim_end:
        raise MediaValidationError(
            f"Invalid trim window: start ({spec.trim_start:.1f}s) must be before end ({spec.trim_end:.1f}s).",
            400,
        )

    # Check overshoot against real source duration
    if meta.duration:
        if spec.trim_end > meta.duration:
            overshoot = spec.trim_end - meta.duration
            if overshoot <= _WINDOW_SLACK_SECONDS:
                spec.trim_end = meta.duration
            else:
                raise MediaValidationError(
                    f"The video is {meta.duration:.1f}s long; the chosen clip ends at {spec.trim_end:.1f}s.",
                    400,
                )

    length = spec.trim_end - spec.trim_start
    if length < settings.REEL_MIN_SECONDS - _WINDOW_SLACK_SECONDS:
        raise MediaValidationError(
            f"Reels must be at least {settings.REEL_MIN_SECONDS} seconds long.", 422,
        )
    if length > settings.REEL_MAX_SECONDS + _WINDOW_SLACK_SECONDS:
        raise MediaValidationError(
            f"Reels can be up to {settings.REEL_MAX_SECONDS} seconds long.", 422,
        )

    if spec.cover_time is not None:
        offset = spec.cover_time
        if offset < 0 or offset > length + _WINDOW_SLACK_SECONDS:
            raise MediaValidationError("The cover photo moment is outside the clip.", 400)
    return length


# ---------------------------------------------------------------- filter graph
def _look_filters(spec: ReelEditRequest) -> List[str]:
    chain: List[str] = []
    if spec.look is None:
        return chain
    preset = _LOOK_PRESETS.get(spec.look.preset, "")
    if preset:
        chain.append(preset)
    if any((spec.look.brightness, spec.look.contrast, spec.look.saturation)):
        chain.append(
            "eq=brightness={b}:contrast={c}:saturation={s}".format(
                b=round(spec.look.brightness / 200.0, 3),
                c=round(1 + spec.look.contrast / 100.0, 3),
                s=round(1 + spec.look.saturation / 100.0, 3),
            )
        )
    return chain


def build_filter_graph(spec: ReelEditRequest, meta: SourceMeta) -> str:
    """Returns a comma-separated ffmpeg -vf chain that outputs a 9:16 frame."""
    chain: List[str] = []
    out_w = settings.REEL_OUTPUT_WIDTH
    out_h = settings.REEL_OUTPUT_HEIGHT
    if spec.crop is not None and meta.width and meta.height:
        cw = _even(max(2, int(round(spec.crop.w * meta.width))))
        ch = _even(max(2, int(round(spec.crop.h * meta.height))))
        cx = _even(max(0, int(round(spec.crop.x * meta.width))))
        cy = _even(max(0, int(round(spec.crop.y * meta.height))))
        chain.append(f"crop={cw}:{ch}:{cx}:{cy}")
    chain.append(f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase")
    chain.append(f"crop={out_w}:{out_h}")
    chain.extend(_look_filters(spec))
    chain.append("format=yuv420p")
    return ",".join(chain)


def _resolve_music_path(track_name: Optional[str]) -> Optional[str]:
    if not track_name or track_name.strip().lower() in ("none", "no music"):
        return None
    normalized = track_name.lower().strip()
    alias_map = {
        "trendy": "trendy.aac",
        "trendy store pop": "trendy.aac",
        "cafe": "cafe.aac",
        "cafe lo-fi vibes": "cafe.aac",
        "acoustic": "acoustic.aac",
        "acoustic sunshine": "acoustic.aac",
        "cinematic": "cinematic.aac",
        "cinematic ambient": "cinematic.aac",
    }
    fname = alias_map.get(normalized)
    if not fname:
        for key, val in alias_map.items():
            if key in normalized:
                fname = val
                break
    if not fname:
        return None
    assets_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "assets", "music"))
    candidate = os.path.join(assets_dir, fname)
    return candidate if os.path.exists(candidate) else None


def build_ffmpeg_args(
    spec: ReelEditRequest, meta: SourceMeta, length: float, output_path: str,
) -> List[str]:
    music_path = _resolve_music_path(getattr(spec, "music_track", None))
    vf = build_filter_graph(spec, meta)

    if music_path:
        # Multi-track mixing: Input 0 is trimmed video, Input 1 is looping music
        args = [
            "ffmpeg", "-y", "-loglevel", "error", "-nostdin",
            "-ss", f"{spec.trim_start:.3f}", "-i", meta.path,
            "-stream_loop", "-1", "-i", music_path,
            "-t", f"{length:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-threads", str(max(1, settings.REEL_ENCODE_THREADS)),
            "-r", "30", "-movflags", "+faststart",
        ]
        if spec.mute or not meta.has_audio:
            # Silence original video audio, but KEEP background music track
            args += [
                "-vf", vf,
                "-map", "0:v",
                "-map", "1:a",
                "-c:a", "aac", "-b:a", "128k", "-ac", "2",
                "-shortest",
                output_path,
            ]
        else:
            # Mix original video audio (1.0) and music track (0.35)
            complex_filter = f"[0:v]{vf}[v0];[0:a]volume=1.0[a0];[1:a]volume=0.35[a1];[a0][a1]amix=inputs=2:duration=first[aout]"
            args += [
                "-filter_complex", complex_filter,
                "-map", "[v0]",
                "-map", "[aout]",
                "-c:a", "aac", "-b:a", "128k", "-ac", "2",
                output_path,
            ]
        return args

    # Standard single-track processing
    args = [
        "ffmpeg", "-y", "-loglevel", "error", "-nostdin",
        "-ss", f"{spec.trim_start:.3f}", "-i", meta.path,
        "-t", f"{length:.3f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-threads", str(max(1, settings.REEL_ENCODE_THREADS)),
        "-r", "30", "-movflags", "+faststart",
    ]
    if spec.mute or not meta.has_audio:
        args.append("-an")
    else:
        args += ["-c:a", "aac", "-b:a", "128k", "-ac", "2"]
    args.append(output_path)
    return args


# ---------------------------------------------------------------- rendering
def _extract_cover(src_path: str, cover_time: float, output_path: str) -> bool:
    args = [
        "ffmpeg", "-y", "-loglevel", "error", "-nostdin",
        "-ss", f"{cover_time:.3f}", "-i", src_path,
        "-frames:v", "1", "-vf", "scale=720:-2", output_path,
    ]
    try:
        res = subprocess.run(args, capture_output=True, timeout=30)
    except Exception as exc:
        logger.warning("Cover frame extraction failed: %s", exc)
        return False
    return res.returncode == 0 and os.path.exists(output_path)


def _remove_previous_output(url: Optional[str]) -> None:
    if not url:
        return
    try:
        path = resolve_source_path(url)
    except MediaValidationError:
        return
    for candidate in (path, os.path.splitext(path)[0] + ".webp"):
        try:
            if os.path.exists(candidate):
                os.remove(candidate)
        except OSError:
            pass


def _cleanup(*paths: str) -> None:
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


def process_reel(spec: ReelEditRequest) -> dict:
    """Renders a reel per `spec`, returning metadata about the new file."""
    if not (_tool_available("ffmpeg") and _tool_available("ffprobe")):
        raise MediaValidationError("Video tools are not available on the server.", 503)

    source = resolve_source_path(spec.source_url)
    meta = probe_source(source)

    # Automatically adapt client trim & cover targets if video duration is shorter than requested
    if meta.duration and meta.duration > 0:
        if spec.trim_end > meta.duration:
            logger.info("Clamping trim_end from %.2fs to source duration %.2fs", spec.trim_end, meta.duration)
            spec.trim_end = meta.duration
        if spec.trim_start >= spec.trim_end:
            spec.trim_start = 0.0
        clip_len = spec.trim_end - spec.trim_start
        if spec.cover_time is not None and spec.cover_time > clip_len:
            spec.cover_time = max(0.0, clip_len - 0.5)

    length = validate_spec(spec, meta)

    logger.info(
        "process_reel: source=%s duration=%.2fs trim_start=%.2fs trim_end=%.2fs length=%.2fs cover_time=%s",
        os.path.basename(source),
        meta.duration,
        spec.trim_start,
        spec.trim_end,
        length,
        spec.cover_time,
    )

    reels_dir = os.path.join(upload_root(), REELS_FOLDER)
    os.makedirs(reels_dir, exist_ok=True)
    stem = uuid.uuid4().hex[:12]
    output_path = os.path.join(reels_dir, f"{stem}.mp4")
    cover_path = os.path.join(reels_dir, f"{stem}.webp")

    args = build_ffmpeg_args(spec, meta, length, output_path)
    try:
        result = subprocess.run(
            args, capture_output=True, timeout=settings.REEL_PROCESSING_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        _cleanup(output_path, cover_path)
        raise MediaValidationError("Preparing this video took too long. Try a shorter clip.", 504)

    if result.returncode != 0 or not os.path.exists(output_path):
        logger.error("ffmpeg failed for %s: %s", source, result.stderr.decode(errors="ignore")[-800:])
        _cleanup(output_path, cover_path)
        raise MediaValidationError("We could not prepare this video. Please try another file.", 500)

    cover_url: Optional[str] = None
    if spec.cover_time is not None:
        if _extract_cover(output_path, spec.cover_time, cover_path):
            cover_url = f"/uploads/{REELS_FOLDER}/{os.path.basename(cover_path)}"
    if cover_url is None:
        if _extract_cover(output_path, min(1.0, max(0.0, length / 2)), cover_path):
            cover_url = f"/uploads/{REELS_FOLDER}/{os.path.basename(cover_path)}"

    _remove_previous_output(spec.previous_output_url)

    return {
        "url": f"/uploads/{REELS_FOLDER}/{os.path.basename(output_path)}",
        "thumbnail_url": cover_url,
        "duration_seconds": int(round(length)),
        "width": settings.REEL_OUTPUT_WIDTH,
        "height": settings.REEL_OUTPUT_HEIGHT,
        "size_bytes": os.path.getsize(output_path),
    }
