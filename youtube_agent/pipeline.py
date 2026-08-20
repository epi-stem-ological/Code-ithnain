"""The engine: link in, structured output out."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .config import Config
from .gemini import GeminiClient
from .metadata import VideoMetadata, fetch_metadata
from .prompts import DEFAULT_TASK, SYSTEM_INSTRUCTION, build_prompt
from .transcript import DEFAULT_LANGUAGES, Transcript, fetch_transcript
from .urls import extract_video_id


@dataclass
class Result:
    video_id: str
    metadata: VideoMetadata
    transcript: Transcript
    outputs: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "metadata": self.metadata.to_dict(),
            "transcript": {
                "language": self.transcript.language,
                "word_count": self.transcript.word_count(),
                "text": self.transcript.text,
            },
            "outputs": self.outputs,
        }

    def write(self, output_dir: Path) -> list[Path]:
        """Write JSON plus one markdown file per task. Returns the paths written."""
        output_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []

        json_path = output_dir / f"{self.video_id}.json"
        json_path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(json_path)

        for task, body in self.outputs.items():
            md_path = output_dir / f"{self.video_id}.{task}.md"
            header = f"# {self.metadata.title}\n\n[{self.metadata.url}]({self.metadata.url}) — {self.metadata.channel}\n\n"
            md_path.write_text(header + body + "\n", encoding="utf-8")
            written.append(md_path)

        return written


class Engine:
    """Fetch metadata + transcript for a link, then run one or more LLM tasks."""

    def __init__(self, config: Config | None = None, client: GeminiClient | None = None):
        self.config = config or Config.from_env()
        self.client = client or GeminiClient(self.config)

    def process(
        self,
        url_or_id: str,
        tasks: Sequence[str] = (DEFAULT_TASK,),
        languages: Sequence[str] = DEFAULT_LANGUAGES,
        timestamp_every: int = 30,
    ) -> Result:
        video_id = extract_video_id(url_or_id)
        metadata = fetch_metadata(video_id)
        transcript = fetch_transcript(video_id, languages=languages)
        transcript_text = transcript.timestamped_text(every_seconds=timestamp_every)

        outputs: dict[str, str] = {}
        for task in tasks:
            prompt = build_prompt(task, metadata, transcript_text, transcript.language)
            outputs[_slug(task)] = self.client.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)

        return Result(video_id=video_id, metadata=metadata, transcript=transcript, outputs=outputs)


def _slug(task: str) -> str:
    """Filesystem-safe short name for a task (free-form tasks get truncated)."""
    cleaned = "".join(char if char.isalnum() else "-" for char in task.lower()).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned[:40] or "output"
