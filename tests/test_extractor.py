from unittest.mock import patch

import pytest
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, VideoUnavailable

import extractor
from extractor import ExtractionError, VideoData, _hms, extract_video_id, fetch_transcript

VALID = [
    ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "dQw4w9WgXcQ"),
    ("youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ?t=30", "dQw4w9WgXcQ"),
    ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("  https://www.youtube.com/embed/dQw4w9WgXcQ  ", "dQw4w9WgXcQ"),
]


@pytest.mark.parametrize("value,expected", VALID)
def test_extract_video_id(value, expected):
    assert extract_video_id(value) == expected


@pytest.mark.parametrize("value", ["", "https://vimeo.com/1", "https://www.youtube.com/", "https://youtu.be/nope"])
def test_extract_video_id_rejects(value):
    with pytest.raises(ExtractionError):
        extract_video_id(value)


def test_hms_pads_to_two_digits():
    assert _hms(0) == "00:00:00"
    assert _hms(95) == "00:01:35"
    assert _hms(3725) == "01:02:05"


class FakeSnippet:
    def __init__(self, text, start):
        self.text = text
        self.start = start
        self.duration = 2.0


class FakeFetched(list):
    language_code = "en"


def test_fetch_transcript_formats_every_line_with_a_timestamp():
    fetched = FakeFetched([FakeSnippet("hello\nthere", 0.0), FakeSnippet("later on", 95.0)])
    with patch.object(extractor.YouTubeTranscriptApi, "fetch", return_value=fetched, create=True):
        text, language, count, error = fetch_transcript("dQw4w9WgXcQ")

    assert error is None
    assert language == "en"
    assert count == 2
    # caption line breaks are collapsed, not preserved
    assert text == "[00:00:00] hello there\n[00:01:35] later on"


def test_fetch_transcript_skips_blank_lines():
    fetched = FakeFetched([FakeSnippet("real", 0.0), FakeSnippet("   ", 5.0)])
    with patch.object(extractor.YouTubeTranscriptApi, "fetch", return_value=fetched, create=True):
        text, _, count, _ = fetch_transcript("dQw4w9WgXcQ")
    assert count == 1 and text == "[00:00:00] real"


@pytest.mark.parametrize(
    "exception,expected_phrase",
    [
        (TranscriptsDisabled("dQw4w9WgXcQ"), "disabled captions"),
        (NoTranscriptFound("dQw4w9WgXcQ", ["en"], {}), "no English captions"),
        (VideoUnavailable("dQw4w9WgXcQ"), "unavailable, private, or removed"),
    ],
)
def test_disabled_transcripts_return_an_error_not_an_exception(exception, expected_phrase):
    """A missing transcript is an ordinary outcome; it must never raise."""
    with patch.object(extractor.YouTubeTranscriptApi, "fetch", side_effect=exception, create=True):
        text, language, count, error = fetch_transcript("dQw4w9WgXcQ")

    assert text is None and language is None and count == 0
    assert expected_phrase in error


def test_unknown_exception_still_degrades_gracefully():
    with patch.object(extractor.YouTubeTranscriptApi, "fetch", side_effect=RuntimeError("boom"), create=True):
        text, _, _, error = fetch_transcript("dQw4w9WgXcQ")
    assert text is None and "boom" in error


def test_empty_transcript_is_reported_as_an_error():
    with patch.object(extractor.YouTubeTranscriptApi, "fetch", return_value=FakeFetched([]), create=True):
        text, _, _, error = fetch_transcript("dQw4w9WgXcQ")
    assert text is None and "empty" in error


def test_extract_survives_a_missing_transcript():
    metadata = {
        "title": "T", "author": "A", "description": "D",
        "duration_seconds": 60, "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    }
    with patch.object(extractor, "fetch_metadata", return_value=metadata), \
         patch.object(extractor, "fetch_transcript", return_value=(None, None, 0, "captions disabled")):
        video = extractor.extract("https://youtu.be/dQw4w9WgXcQ")

    assert isinstance(video, VideoData)
    assert video.title == "T" and video.author == "A"
    assert video.has_transcript is False
    assert video.transcript_error == "captions disabled"
    assert video.word_count() == 0


def test_video_data_properties():
    video = VideoData("id", "u", "t", "a", "d", duration_seconds=3725, transcript="one two three")
    assert video.duration_hms == "01:02:05"
    assert video.word_count() == 3
    assert video.has_transcript is True
