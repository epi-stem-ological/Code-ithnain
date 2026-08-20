"""Parsing of the many shapes a YouTube link can take."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

_PATH_PREFIXES = ("/embed/", "/v/", "/shorts/", "/live/")


class InvalidYouTubeURL(ValueError):
    """Raised when a string is neither a video id nor a recognizable YouTube URL."""


def extract_video_id(url_or_id: str) -> str:
    """Return the 11-character video id for a YouTube URL, id, or short link.

    Accepts watch URLs, youtu.be short links, /shorts/, /embed/, /v/, and /live/
    paths, with or without a scheme.
    """
    candidate = (url_or_id or "").strip()
    if not candidate:
        raise InvalidYouTubeURL("empty input")

    if _ID.match(candidate):
        return candidate

    if "://" not in candidate:
        candidate = "https://" + candidate

    parsed = urlparse(candidate)
    host = parsed.netloc.lower().split(":")[0]
    if host not in _HOSTS:
        raise InvalidYouTubeURL(f"not a YouTube URL: {url_or_id!r}")

    if host.endswith("youtu.be"):
        segment = parsed.path.lstrip("/").split("/")[0]
        if _ID.match(segment):
            return segment
        raise InvalidYouTubeURL(f"no video id in {url_or_id!r}")

    video_ids = parse_qs(parsed.query).get("v")
    if video_ids and _ID.match(video_ids[0]):
        return video_ids[0]

    for prefix in _PATH_PREFIXES:
        if parsed.path.startswith(prefix):
            segment = parsed.path[len(prefix):].split("/")[0]
            if _ID.match(segment):
                return segment

    raise InvalidYouTubeURL(f"no video id in {url_or_id!r}")


def watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"
