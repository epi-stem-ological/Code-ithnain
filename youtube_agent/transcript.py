"""Caption retrieval via youtube-transcript-api.

Supports both the 1.x instance API (``YouTubeTranscriptApi().fetch``) and the
legacy 0.6.x static API (``YouTubeTranscriptApi.get_transcript``), so the module
keeps working across the version boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from youtube_transcript_api import YouTubeTranscriptApi

DEFAULT_LANGUAGES = ("en", "en-US", "en-GB")


class TranscriptError(RuntimeError):
    """Raised when no usable transcript can be retrieved."""


@dataclass(frozen=True)
class Segment:
    text: str
    start: float
    duration: float

    @property
    def timestamp(self) -> str:
        total = int(self.start)
        hours, rem = divmod(total, 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{hours:d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:d}:{seconds:02d}"


@dataclass
class Transcript:
    video_id: str
    language: str
    segments: list[Segment]

    @property
    def text(self) -> str:
        return " ".join(segment.text.strip() for segment in self.segments if segment.text.strip())

    def timestamped_text(self, every_seconds: int = 30) -> str:
        """Transcript with a timestamp marker at most every ``every_seconds``.

        Keeps the LLM able to cite moments without inflating the prompt with a
        timestamp on every caption line.
        """
        lines: list[str] = []
        next_mark = 0.0
        for segment in self.segments:
            body = segment.text.strip()
            if not body:
                continue
            if segment.start >= next_mark:
                lines.append(f"[{segment.timestamp}] {body}")
                next_mark = segment.start + every_seconds
            else:
                lines.append(body)
        return "\n".join(lines)

    def word_count(self) -> int:
        return len(self.text.split())


def _to_segments(raw: Iterable[Any]) -> list[Segment]:
    segments: list[Segment] = []
    for item in raw:
        if isinstance(item, dict):
            text, start, duration = item.get("text", ""), item.get("start", 0.0), item.get("duration", 0.0)
        else:  # 1.x FetchedTranscriptSnippet
            text, start, duration = item.text, item.start, item.duration
        segments.append(Segment(text=str(text), start=float(start or 0.0), duration=float(duration or 0.0)))
    return segments


def fetch_transcript(
    video_id: str,
    languages: Sequence[str] = DEFAULT_LANGUAGES,
) -> Transcript:
    """Fetch captions for ``video_id``, preferring the given language order."""
    wanted = list(languages) or list(DEFAULT_LANGUAGES)

    try:
        if hasattr(YouTubeTranscriptApi, "fetch"):  # 1.x instance API
            fetched = YouTubeTranscriptApi().fetch(video_id, languages=wanted)
            language = getattr(fetched, "language_code", wanted[0])
            segments = _to_segments(fetched)
        else:  # 0.6.x static API
            raw = YouTubeTranscriptApi.get_transcript(video_id, languages=wanted)
            language = wanted[0]
            segments = _to_segments(raw)
    except Exception as exc:
        raise TranscriptError(
            f"no transcript for {video_id} in {wanted}: {exc}. "
            "The video may have captions disabled, or be age/region restricted."
        ) from exc

    if not segments:
        raise TranscriptError(f"transcript for {video_id} was empty")

    return Transcript(video_id=video_id, language=language, segments=segments)


def list_available_languages(video_id: str) -> list[dict[str, Any]]:
    """Return the caption tracks YouTube exposes for a video."""
    try:
        api = YouTubeTranscriptApi()
        listing = api.list(video_id) if hasattr(api, "list") else YouTubeTranscriptApi.list_transcripts(video_id)
        return [
            {
                "language": track.language,
                "language_code": track.language_code,
                "generated": track.is_generated,
                "translatable": track.is_translatable,
            }
            for track in listing
        ]
    except Exception as exc:
        raise TranscriptError(f"could not list transcripts for {video_id}: {exc}") from exc
