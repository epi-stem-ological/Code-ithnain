# YouTube Agent Engine

Send it a YouTube link, get back structured output: summaries, outlines, study
notes, quotes, action items, threads, blog drafts — or any free-form task you
describe.

```
link ──▶ url parse ──▶ yt-dlp metadata ─┐
                                        ├──▶ prompt assembly ──▶ Gemini ──▶ out/*.md + out/*.json
         youtube-transcript-api ────────┘
```

## Setup

```bash
# 1. clone and enter the repo
git clone https://github.com/epi-stem-ological/Code-ithnain.git
cd Code-ithnain

# 2. create and activate a virtual environment (Python 3.10+)
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. install dependencies
pip install --upgrade pip
pip install -r requirements.txt    # or requirements-dev.txt to also get pytest

# 4. add your Gemini API key
cp .env.example .env
$EDITOR .env                       # paste your key from https://aistudio.google.com/apikey
```

To leave the environment later: `deactivate`.

## Usage

```bash
# default: a summary with timestamped takeaways
python -m youtube_agent "https://youtu.be/VIDEO_ID"

# several tasks at once
python -m youtube_agent "https://youtu.be/VIDEO_ID" -t summary -t action_items -t quotes

# any free-form instruction works as a task
python -m youtube_agent "https://youtu.be/VIDEO_ID" -t "list every book mentioned, with the timestamp"

# non-English captions, in preference order
python -m youtube_agent "https://youtu.be/VIDEO_ID" -l ar -l en

# what caption tracks exist? (no API key needed)
python -m youtube_agent "https://youtu.be/VIDEO_ID" --list-languages

# print only, write nothing
python -m youtube_agent "https://youtu.be/VIDEO_ID" --no-write
```

Results land in `out/` (override with `-o` or `YTA_OUTPUT_DIR`): one
`<video_id>.json` with the full transcript and metadata, plus one
`<video_id>.<task>.md` per task.

Built-in tasks: `summary`, `outline`, `notes`, `quotes`, `questions`,
`action_items`, `thread`, `blog`.

## Using it from Python

```python
from youtube_agent.pipeline import Engine

result = Engine().process("https://youtu.be/VIDEO_ID", tasks=["summary", "notes"])
print(result.metadata.title, result.transcript.word_count())
print(result.outputs["summary"])
result.write(Path("out"))
```

## Layout

| File | Role |
| --- | --- |
| `youtube_agent/urls.py` | Parse every YouTube link shape into a video id |
| `youtube_agent/metadata.py` | yt-dlp metadata extraction (no media download) |
| `youtube_agent/transcript.py` | Captions, timestamping, language selection |
| `youtube_agent/prompts.py` | System instruction and task templates |
| `youtube_agent/gemini.py` | google-genai client wrapper |
| `youtube_agent/pipeline.py` | `Engine` — orchestration; `Result` — output writing |
| `youtube_agent/cli.py` | Argument parsing and the `python -m youtube_agent` entry point |
| `youtube_agent/config.py` | `.env` / environment configuration |

## Prompt injection

A transcript is text written by whoever uploaded the video, so it is treated as
untrusted data throughout:

- Transcript and description are wrapped in `<untrusted_transcript>` delimiters,
  clearly separated from the operator's task.
- The system instruction tells the model never to obey instructions found inside
  those delimiters, and to report them as a finding instead.
- The engine has no tools and no network access of its own — it only reads
  YouTube and writes local files, so a malicious transcript has nothing to reach
  for even if it does influence the model's text.

Still treat the generated output as untrusted if you pipe it anywhere that acts
on it.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The suite covers URL parsing, transcript formatting, prompt assembly, and output
writing — no network or API key required.

## Notes and limits

- **Captions are required.** Videos with captions disabled will fail with a
  clear error. Whisper-based audio fallback is the natural next step (see below).
- **Long videos** can exceed the model's context. Gemini 2.5 Flash handles
  roughly 1M tokens, which covers most videos, but very long streams may need
  chunk-and-merge.
- **Rate limits.** The free Gemini tier is limited; batch runs may need backoff.

## Possible next steps

1. `--audio-fallback`: `yt-dlp` audio extraction + Whisper for uncaptioned videos.
2. Playlist and channel input — fan out over many videos, then synthesize across them.
3. A local cache keyed by video id, so re-running a task costs nothing.
4. Chunk-and-merge summarization for videos past the context window.
5. Embeddings + a vector store, so you can ask questions across every video you've fed it.
6. Wrap it as an MCP server so Claude Code can call it on any link you paste.
