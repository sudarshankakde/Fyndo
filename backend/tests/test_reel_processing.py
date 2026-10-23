"""Tests for the server-side reel editor (`/media/reels/process`).

Pure command-building tests run everywhere; the real-encode integration test
is skipped when ffmpeg is not installed, and skipped on constrained CI boxes
where x264 cannot reliably allocate the 1080x1920 encode buffers.
"""
import os
import shutil
import subprocess
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.schemas.media import ReelCropBox, ReelEditRequest, ReelLook
from app.services import reel_processing_service as svc
from app.services.media_service import MediaValidationError, upload_root

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    from app.core.database import Base, engine
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client: AsyncClient) -> str:
    phone = f"+91{uuid.uuid4().int % 10_000_000_000:010d}"
    send = await client.post("/api/v1/auth/otp/send", json={"phone": phone})
    otp = send.json()["data"]["test_otp"]
    verify = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})
    return verify.json()["data"]["access_token"]


def _meta(width=720, height=1280, duration=40.0, has_audio=True) -> svc.SourceMeta:
    return svc.SourceMeta(path="src.mp4", width=width, height=height, duration=duration, has_audio=has_audio)


# ---------------------------------------------------------------- pure logic
def test_filter_graph_fills_9_16_and_applies_crop_and_look():
    spec = ReelEditRequest(
        source_url="/uploads/reels/a.mp4", trim_start=0, trim_end=20,
        crop=ReelCropBox(x=0.25, y=0.0, w=0.5, h=1.0),
        look=ReelLook(preset="mono", brightness=20, contrast=-10, saturation=0),
    )
    graph = svc.build_filter_graph(spec, _meta(width=1920, height=1080))
    assert graph.startswith("crop=960:1080:480:0,")
    assert f"scale={settings.REEL_OUTPUT_WIDTH}:{settings.REEL_OUTPUT_HEIGHT}" in graph
    assert "hue=s=0" in graph
    assert "brightness=0.1:contrast=0.9:saturation=1.0" in graph
    assert graph.endswith(",format=yuv420p")


def test_ffmpeg_args_include_trim_and_audio_options():
    meta = _meta()
    kept = ReelEditRequest(source_url="/uploads/reels/a.mp4", trim_start=1.5, trim_end=46.0)
    args = svc.build_ffmpeg_args(kept, meta, length=44.5, output_path="out.mp4")
    assert args[:8] == ["ffmpeg", "-y", "-loglevel", "error", "-nostdin", "-ss", "1.500", "-i"]
    assert "-c:a" in args and "aac" in args
    muted = kept.model_copy(update={"mute": True})
    assert "-an" in svc.build_ffmpeg_args(muted, meta, length=44.5, output_path="out.mp4")


def test_validate_spec_rejects_too_short_or_too_long_clips():
    meta = _meta(duration=90.0)
    too_short = ReelEditRequest(source_url="/uploads/reels/a.mp4", trim_start=0, trim_end=5)
    with pytest.raises(MediaValidationError):
        svc.validate_spec(too_short, meta)
    too_long = ReelEditRequest(source_url="/uploads/reels/a.mp4", trim_start=0, trim_end=90)
    with pytest.raises(MediaValidationError):
        svc.validate_spec(too_long, meta)


def test_edit_request_rejects_zero_length_trim():
    with pytest.raises(ValueError):
        ReelEditRequest(source_url="/uploads/reels/a.mp4", trim_start=5, trim_end=5)


def test_crop_box_must_stay_inside_frame():
    with pytest.raises(ValueError):
        ReelCropBox(x=0.8, y=0.0, w=0.5, h=1.0)


@pytest.mark.parametrize(
    "bad_url",
    ["uploads/reels/a.mp4", "/uploads/kyc/a.mp4", "/uploads/reels/../a.mp4", "/uploads/reels/", "/uploads/reels/.hidden"],
)
def test_resolve_source_rejects_unsafe_paths(bad_url: str):
    with pytest.raises(MediaValidationError):
        svc.resolve_source_path(bad_url)


# ---------------------------------------------------------------- endpoint
@pytest.mark.asyncio
async def test_process_endpoint_requires_authentication(client: AsyncClient):
    res = await client.post("/api/v1/media/reels/process", json={
        "source_url": "/uploads/reels/missing.mp4", "trim_start": 0, "trim_end": 20,
    })
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_process_endpoint_404_when_source_missing(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(svc, "_tool_available", lambda _name: True)
    token = await _login(client)
    res = await client.post(
        "/api/v1/media/reels/process",
        json={"source_url": "/uploads/reels/does-not-exist.mp4", "trim_start": 0, "trim_end": 20},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


def _make_clip(path: str, seconds: int = 20) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
         f"testsrc=duration={seconds}:size=320x240:rate=24", "-f", "lavfi", "-i",
         f"sine=frequency=440:duration={seconds}", "-c:v", "libx264", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", path],
        check=True, capture_output=True, timeout=120,
    )


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_process_renders_vertical_clip_end_to_end(monkeypatch):
    """Direct service call — avoids running two ffmpeg encodes under the ASGI
    threadpool, which triggers x264 OOM on memory-constrained runners."""
    monkeypatch.setattr(settings, "REEL_OUTPUT_WIDTH", 540)
    monkeypatch.setattr(settings, "REEL_OUTPUT_HEIGHT", 960)
    monkeypatch.setattr(settings, "REEL_ENCODE_THREADS", 1)

    reels_dir = os.path.join(upload_root(), svc.REELS_FOLDER)
    os.makedirs(reels_dir, exist_ok=True)
    stem = f"test-{uuid.uuid4().hex[:8]}"
    source = os.path.join(reels_dir, f"{stem}.mp4")
    _make_clip(source, seconds=20)
    rendered_url = None
    second_url = None
    try:
        spec = ReelEditRequest(
            source_url=f"/uploads/reels/{stem}.mp4", trim_start=1.0, trim_end=17.0,
            crop=ReelCropBox(x=0.2, y=0.0, w=0.6, h=1.0), cover_time=3.0, mute=True,
            look=ReelLook(preset="warm", brightness=10, contrast=5, saturation=15),
        )
        data = svc.process_reel(spec)
        rendered_url = data["url"]
        assert data["url"].startswith("/uploads/reels/") and data["url"].endswith(".mp4")
        assert data["thumbnail_url"].endswith(".webp")
        assert data["duration_seconds"] == 16
        assert (data["width"], data["height"]) == (540, 960)

        rendered = svc.resolve_source_path(data["url"])
        meta = svc.probe_source(rendered)
        assert (meta.width, meta.height) == (540, 960)
        assert meta.has_audio is False

        spec2 = spec.model_copy(update={"trim_end": 16.0, "previous_output_url": data["url"], "mute": False})
        data2 = svc.process_reel(spec2)
        second_url = data2["url"]
        assert not os.path.exists(rendered)
        assert svc.probe_source(svc.resolve_source_path(second_url)).has_audio is True
    finally:
        for url in (rendered_url, second_url, f"/uploads/reels/{stem}.mp4"):
            if not url:
                continue
            base = os.path.join(reels_dir, os.path.basename(url))
            for p in (base, os.path.splitext(base)[0] + ".webp"):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
