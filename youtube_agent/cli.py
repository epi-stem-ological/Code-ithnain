"""Command-line entry point: python -m youtube_agent <url> [--task ...]"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

from .config import Config, ConfigError
from .metadata import MetadataError
from .pipeline import Engine
from .prompts import DEFAULT_TASK, TASKS
from .transcript import DEFAULT_LANGUAGES, TranscriptError, list_available_languages
from .urls import InvalidYouTubeURL, extract_video_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="youtube-agent",
        description="Turn a YouTube link into summaries, notes, outlines and more.",
    )
    parser.add_argument("url", help="YouTube URL, short link, or 11-character video id")
    parser.add_argument(
        "-t",
        "--task",
        action="append",
        default=None,
        help=(
            "Task to run; repeatable. Built-ins: "
            + ", ".join(sorted(TASKS))
            + ". Any other text is used as a free-form instruction."
        ),
    )
    parser.add_argument(
        "-l",
        "--lang",
        action="append",
        default=None,
        help="Preferred caption language, in order of preference (default: en).",
    )
    parser.add_argument("-o", "--output-dir", default=None, help="Where to write results (default: $YTA_OUTPUT_DIR or ./out)")
    parser.add_argument("--list-languages", action="store_true", help="List available caption tracks and exit")
    parser.add_argument("--no-write", action="store_true", help="Print to stdout only; write no files")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        video_id = extract_video_id(args.url)
    except InvalidYouTubeURL as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.list_languages:
        try:
            for track in list_available_languages(video_id):
                kind = "auto" if track["generated"] else "manual"
                print(f"{track['language_code']:<8} {track['language']} ({kind})")
        except TranscriptError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0

    try:
        config = Config.from_env()
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.output_dir:
        config = dataclasses.replace(config, output_dir=Path(args.output_dir))
        config.output_dir.mkdir(parents=True, exist_ok=True)

    tasks = args.task or [DEFAULT_TASK]
    languages = args.lang or list(DEFAULT_LANGUAGES)

    try:
        result = Engine(config).process(video_id, tasks=tasks, languages=languages)
    except (MetadataError, TranscriptError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"{result.metadata.title} — {result.metadata.channel} ({result.metadata.duration_hms})")
    print(f"transcript: {result.transcript.word_count()} words [{result.transcript.language}]\n")
    for task, body in result.outputs.items():
        print(f"===== {task} =====\n{body}\n")

    if not args.no_write:
        for path in result.write(config.output_dir):
            print(f"wrote {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
