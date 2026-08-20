#!/usr/bin/env python3
"""Entry point: a YouTube URL in, a structured Gemini analysis out.

    python main.py "https://youtu.be/VIDEO_ID"
"""

from __future__ import annotations

import argparse
import json
import sys

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from agent import AgentError, Analysis, analyze, list_models
from extractor import ExtractionError, VideoData, extract

console = Console()
err_console = Console(stderr=True)


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def render_header(video: VideoData) -> None:
    body = Text()
    body.append(video.title, style="bold white")
    body.append(f"\n{video.author}", style="cyan")
    body.append(f"  ·  {video.duration_hms}", style="dim")
    if video.has_transcript:
        body.append(
            f"  ·  {video.segment_count} caption lines"
            f" · {video.word_count():,} words"
            f" · {video.transcript_language}",
            style="dim",
        )
    body.append(f"\n{video.url}", style="dim blue underline")
    console.print(Panel(body, border_style="bright_black", padding=(1, 2)))


def render_summary(analysis: Analysis) -> None:
    console.print(Panel(
        Markdown(analysis.summary),
        title="[bold]Summary[/bold]",
        border_style="green",
        padding=(1, 2),
    ))


def render_takeaways(analysis: Analysis) -> None:
    if not analysis.takeaways:
        return
    items = []
    for index, item in enumerate(analysis.takeaways, start=1):
        line = Text()
        line.append(f"{index}. ", style="bold yellow")
        line.append(item.takeaway, style="bold")
        line.append(f"\n   {item.why}", style="dim")
        items.append(line)
    console.print(Panel(
        Group(*items),
        title="[bold]Actionable Takeaways[/bold]",
        border_style="yellow",
        padding=(1, 2),
    ))


def render_highlights(analysis: Analysis) -> None:
    if not analysis.highlights:
        return
    table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 2), expand=True)
    table.add_column("Time", style="bold cyan", no_wrap=True)
    table.add_column("Moment", style="bold", ratio=1)
    table.add_column("Why it matters", style="dim", ratio=2)
    for item in analysis.highlights:
        table.add_row(item.timestamp, item.title, item.detail)
    console.print(Panel(
        table,
        title="[bold]Timestamped Highlights[/bold]",
        border_style="magenta",
        padding=(1, 1),
    ))


def render_insights(analysis: Analysis) -> None:
    if not analysis.insights:
        return
    blocks = []
    for group in analysis.insights:
        block = Text()
        block.append(f"{group.category}\n", style="bold blue")
        for point in group.points:
            block.append("  • ", style="blue")
            block.append(f"{point}\n")
        blocks.append(block)
    console.print(Panel(
        Group(*blocks),
        title="[bold]Categorized Insights[/bold]",
        border_style="blue",
        padding=(1, 2),
    ))


def render_notes(analysis: Analysis) -> None:
    if not analysis.content_notes:
        return
    body = Text()
    for note in analysis.content_notes:
        body.append("  • ", style="dim")
        body.append(f"{note}\n", style="dim")
    console.print(Panel(
        body,
        title="[bold]Caveats[/bold]",
        border_style="bright_black",
        padding=(1, 2),
    ))


def render_injection_report(analysis: Analysis) -> None:
    """Always shown -- a clean bill of health is worth stating explicitly."""
    if not analysis.injection_attempts:
        console.print(
            "  [green]✓[/green] [dim]No prompt-injection attempts detected in the transcript.[/dim]\n"
        )
        return

    blocks = []
    for finding in analysis.injection_attempts:
        block = Text()
        block.append(f"[{finding.timestamp}] ", style="bold red")
        block.append(f"{finding.quoted_text}\n", style="italic")
        block.append(f"  → {finding.assessment}", style="dim")
        blocks.append(block)
    console.print(Panel(
        Group(*blocks),
        title="[bold red]⚠ Prompt Injection Attempts Detected (ignored, not obeyed)[/bold red]",
        border_style="red",
        padding=(1, 2),
    ))


def render(video: VideoData, analysis: Analysis) -> None:
    console.print()
    render_header(video)
    render_summary(analysis)
    render_takeaways(analysis)
    render_highlights(analysis)
    render_insights(analysis)
    render_notes(analysis)
    console.print(Rule(style="bright_black"))
    render_injection_report(analysis)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Analyze a YouTube video with Gemini.",
    )
    parser.add_argument("url", nargs="?", help="YouTube URL, short link, or 11-character video id")
    parser.add_argument("-t", "--task", default=None, help="Override the analysis instruction")
    parser.add_argument("-m", "--model", default=None, help="Gemini model (default: gemini-2.5-flash)")
    parser.add_argument("-l", "--lang", action="append", default=None,
                        help="Caption language preference, repeatable (default: English)")
    parser.add_argument("--list-models", action="store_true", help="List models your API key can use, then exit")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON instead of formatted output")
    parser.add_argument("--save", metavar="PATH", default=None, help="Also write the analysis as JSON to PATH")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_models:
        try:
            models = list_models()
        except AgentError as exc:
            err_console.print(f"[bold red]{exc}[/bold red]")
            return 1
        table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 2))
        table.add_column("Model", style="bold cyan")
        table.add_column("Name", style="dim")
        table.add_column("Input tokens", justify="right", style="dim")
        for model in models:
            limit = model["input_token_limit"]
            table.add_row(str(model["name"]), str(model["display_name"]), f"{limit:,}" if limit else "")
        console.print(table)
        console.print(f"\n[dim]Set one with GEMINI_MODEL=<name> in .env, or --model <name>[/dim]")
        return 0

    if not args.url:
        err_console.print("[bold red]error:[/bold red] a YouTube URL is required")
        return 2

    # 1. Extract
    try:
        with console.status("[dim]Fetching metadata and transcript…[/dim]", spinner="dots"):
            video = extract(args.url, languages=args.lang) if args.lang else extract(args.url)
    except ExtractionError as exc:
        err_console.print(f"[bold red]Extraction failed:[/bold red] {exc}")
        return 1

    if not video.has_transcript:
        err_console.print(f"[bold red]Cannot analyze:[/bold red] {video.transcript_error}")
        err_console.print(
            "[dim]Tip: run with -l to try another language, e.g. [/dim][cyan]-l es -l en[/cyan]"
        )
        return 1

    # 2. Analyze
    try:
        with console.status("[dim]Analyzing with Gemini…[/dim]", spinner="dots"):
            analysis = analyze(video, task=args.task, model=args.model)
    except AgentError as exc:
        err_console.print(f"[bold red]Analysis failed:[/bold red] {exc}")
        return 1

    # 3. Output
    payload = {
        "video": {
            "video_id": video.video_id,
            "url": video.url,
            "title": video.title,
            "author": video.author,
            "duration": video.duration_hms,
            "transcript_language": video.transcript_language,
            "word_count": video.word_count(),
        },
        "analysis": analysis.model_dump(),
    }

    if args.json:
        console.print_json(json.dumps(payload, ensure_ascii=False))
    else:
        render(video, analysis)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        err_console.print(f"[dim]Saved to {args.save}[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
