"""Extract YouTube video metadata and transcript.

Two sources, neither of which downloads the video itself:
  - yt-dlp            -> title, author, description (info extraction only)
  - youtube-transcript-api -> English captions, formatted with timestamps

Nothing here talks to an LLM. Everything returned is untrusted input authored by
the video's uploader; agent.py is responsible for containing it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL

ENGLISH = ("en", "en-US", "en-GB", "en-CA", "en-AU")

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "music.youtube.com", "youtu.be", "www.youtu.be",
}
_PATH_PREFIXES = ("/embed/", "/v/", "/shorts/", "/live/")


class ExtractionError(RuntimeError):
    """Raised when the video itself cannot be read (bad URL, private, removed)."""


@dataclass
class VideoData:
    """Everything extractor.py knows about one video.

    ``transcript`` is None when captions could not be retrieved; ``transcript_error``
    then explains why. A missing transcript is not an exception -- callers decide
    whether it is fatal.
    """

    video_id: str
    url: str
    title: str
    author: str
    description: str
    duration_seconds: int = 0
    transcript: str | None = None
    transcript_language: str | None = None
    transcript_error: str | None = None
    segment_count: int = 0

    @property
    def has_transcript(self) -> bool:
        return bool(self.transcript)

    @property
    def duration_hms(self) -> str:
        return _hms(self.duration_seconds)

    def word_count(self) -> int:
        return len(self.transcript.split()) if self.transcript else 0


def _hms(seconds: float) -> str:
    total = int(seconds or 0)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def extract_video_id(url_or_id: str) -> str:
    """Return the 11-character video id from a URL, short link, or bare id."""
    candidate = (url_or_id or "").strip()
    if not candidate:
        raise ExtractionError("no URL given")

    if _VIDEO_ID.match(candidate):
        return candidate

    if "://" not in candidate:
        candidate = "https://" + candidate

    parsed = urlparse(candidate)
    host = parsed.netloc.lower().split(":")[0]
    if host not in _HOSTS:
        raise ExtractionError(f"not a YouTube URL: {url_or_id!r}")

    if host.endswith("youtu.be"):
        segment = parsed.path.lstrip("/").split("/")[0]
        if _VIDEO_ID.match(segment):
            return segment
        raise ExtractionError(f"no video id found in {url_or_id!r}")

    values = parse_qs(parsed.query).get("v")
    if values and _VIDEO_ID.match(values[0]):
        return values[0]

    for prefix in _PATH_PREFIXES:
        if parsed.path.startswith(prefix):
            segment = parsed.path[len(prefix):].split("/")[0]
            if _VIDEO_ID.match(segment):
                return segment

    raise ExtractionError(f"no video id found in {url_or_id!r}")


def fetch_metadata(video_id: str) -> dict[str, Any]:
    """Title, author, description and duration via yt-dlp. No media is downloaded."""
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    except Exception as exc:  # yt-dlp raises many DownloadError subclasses
        raise ExtractionError(f"could not read video {video_id}: {exc}") from exc

    if not isinstance(info, dict):
        raise ExtractionError(f"yt-dlp returned no information for {video_id}")

    return {
        "title": info.get("title") or "(untitled)",
        "author": info.get("uploader") or info.get("channel") or "(unknown)",
        "description": info.get("description") or "",
        "duration_seconds": int(info.get("duration") or 0),
        "url": info.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}",
    }


def _snippet_fields(item: Any) -> tuple[str, float]:
    """Read (text, start) from either a 1.x snippet object or a 0.6.x dict."""
    if isinstance(item, dict):
        return str(item.get("text", "")), float(item.get("start") or 0.0)
    return str(item.text), float(item.start or 0.0)


def fetch_transcript(
    video_id: str,
    languages: Sequence[str] = ENGLISH,
) -> tuple[str | None, str | None, int, str | None]:
    """Fetch English captions.

    Returns ``(transcript, language, segment_count, error)``. On failure the first
    three are None/0 and ``error`` carries a human-readable reason -- transcripts
    being disabled is an ordinary outcome, not an exception.
    """
    wanted = list(languages) or list(ENGLISH)

    try:
        if hasattr(YouTubeTranscriptApi, "fetch"):  # youtube-transcript-api 1.x
            fetched = YouTubeTranscriptApi().fetch(video_id, languages=wanted)
            language = getattr(fetched, "language_code", wanted[0])
            raw = list(fetched)
        else:  # 0.6.x static API
            raw = YouTubeTranscriptApi.get_transcript(video_id, languages=wanted)
            language = wanted[0]
    except Exception as exc:
        return None, None, 0, _explain(exc, video_id)

    lines: list[str] = []
    for item in raw:
        text, start = _snippet_fields(item)
        text = " ".join(text.split())  # collapse caption line breaks
        if text:
            lines.append(f"[{_hms(start)}] {text}")

    if not lines:
        return None, None, 0, f"the transcript for {video_id} was empty"

    return "\n".join(lines), language, len(lines), None


def _explain(exc: Exception, video_id: str) -> str:
    """Turn a youtube-transcript-api exception into something a human can act on."""
    name = type(exc).__name__
    reasons = {
        "TranscriptsDisabled": "the uploader has disabled captions for this video",
        "NoTranscriptFound": "no English captions are available (try another language)",
        "VideoUnavailable": "the video is unavailable, private, or removed",
        "AgeRestricted": "the video is age-restricted, so captions cannot be read anonymously",
        "VideoUnplayable": "the video is not playable (region lock or removal)",
        "IpBlocked": "YouTube is blocking requests from this IP address",
        "RequestBlocked": "YouTube is blocking requests from this IP address",
    }
    reason = reasons.get(name, str(exc).strip().splitlines()[0] if str(exc).strip() else name)
    return f"no transcript for {video_id}: {reason}"


def extract(url: str, languages: Sequence[str] = ENGLISH) -> VideoData:
    """Extract metadata and transcript for a YouTube URL.

    Raises ExtractionError only if the video itself cannot be read. A missing
    transcript is reported on the returned VideoData instead.
    """
    video_id = extract_video_id(url)
    metadata = fetch_metadata(video_id)
    transcript, language, count, error = fetch_transcript(video_id, languages)

    return VideoData(
        video_id=video_id,
        url=metadata["url"],
        title=metadata["title"],
        author=metadata["author"],
        description=metadata["description"],
        duration_seconds=metadata["duration_seconds"],
        transcript=transcript,
        transcript_language=language,
        transcript_error=error,
        segment_count=count,
    )
