import json
from pathlib import Path

from youtube_agent.metadata import VideoMetadata
from youtube_agent.pipeline import Result, _slug
from youtube_agent.prompts import SYSTEM_INSTRUCTION, build_prompt
from youtube_agent.transcript import Segment, Transcript

META = VideoMetadata(
    video_id="dQw4w9WgXcQ",
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    title="Test Video",
    channel="Test Channel",
    duration_seconds=125,
)
TRANSCRIPT = Transcript("dQw4w9WgXcQ", "en", [Segment("hello world", 0.0, 2.0)])


def test_duration_hms():
    assert META.duration_hms == "2:05"


def test_slug_is_filesystem_safe():
    assert _slug("summary") == "summary"
    assert _slug("Give me a TL;DR!") == "give-me-a-tl-dr"
    assert len(_slug("x" * 100)) == 40


def test_prompt_wraps_transcript_and_names_the_operator_task():
    prompt = build_prompt("summary", META, "hello world", "en")
    assert "<untrusted_transcript" in prompt and "</untrusted_transcript>" in prompt
    assert "Operator task" in prompt
    assert "Test Video" in prompt


def test_system_instruction_covers_injection():
    assert "untrusted" in SYSTEM_INSTRUCTION.lower()


def test_result_writes_json_and_markdown(tmp_path: Path):
    result = Result("dQw4w9WgXcQ", META, TRANSCRIPT, {"summary": "It is a test."})
    written = result.write(tmp_path)

    assert {p.name for p in written} == {"dQw4w9WgXcQ.json", "dQw4w9WgXcQ.summary.md"}

    data = json.loads((tmp_path / "dQw4w9WgXcQ.json").read_text())
    assert data["metadata"]["title"] == "Test Video"
    assert data["transcript"]["word_count"] == 2

    md = (tmp_path / "dQw4w9WgXcQ.summary.md").read_text()
    assert md.startswith("# Test Video")
    assert "It is a test." in md
