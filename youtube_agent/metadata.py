"""Video metadata via yt-dlp (no download, info extraction only)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from yt_dlp import YoutubeDL

from .urls import watch_url


class MetadataError(RuntimeError):
    """Raised when yt-dlp cannot describe the video."""


@dataclass
class VideoMetadata:
    video_id: str
    url: str
    title: str = ""
    channel: str = ""
    channel_id: str = ""
    upload_date: str = ""
    duration_seconds: int = 0
    view_count: int = 0
    like_count: int = 0
    description: str = ""
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    thumbnail: str = ""
    chapters: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def duration_hms(self) -> str:
        total = int(self.duration_seconds or 0)
        hours, rem = divmod(total, 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{hours:d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:d}:{seconds:02d}"


_YDL_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "noplaylist": True,
    "extract_flat": False,
}


def fetch_metadata(video_id: str) -> VideoMetadata:
    """Extract metadata for a video without downloading any media."""
    try:
        with YoutubeDL(_YDL_OPTS) as ydl:
            info = ydl.extract_info(watch_url(video_id), download=False)
    except Exception as exc:  # yt-dlp raises a wide range of DownloadError subclasses
        raise MetadataError(f"yt-dlp could not read {video_id}: {exc}") from exc

    if not isinstance(info, dict):
        raise MetadataError(f"yt-dlp returned no info for {video_id}")

    chapters = [
        {
            "title": chapter.get("title", ""),
            "start_time": chapter.get("start_time", 0),
            "end_time": chapter.get("end_time", 0),
        }
        for chapter in (info.get("chapters") or [])
    ]

    return VideoMetadata(
        video_id=info.get("id", video_id),
        url=info.get("webpage_url") or watch_url(video_id),
        title=info.get("title") or "",
        channel=info.get("uploader") or info.get("channel") or "",
        channel_id=info.get("channel_id") or "",
        upload_date=info.get("upload_date") or "",
        duration_seconds=int(info.get("duration") or 0),
        view_count=int(info.get("view_count") or 0),
        like_count=int(info.get("like_count") or 0),
        description=info.get("description") or "",
        tags=list(info.get("tags") or []),
        categories=list(info.get("categories") or []),
        thumbnail=info.get("thumbnail") or "",
        chapters=chapters,
    )
