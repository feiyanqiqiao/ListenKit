# Quickstart

## URL Input

```bash
brew install yt-dlp ffmpeg

cli/generate-markdown.sh \
  --url "https://example.com/video" \
  --language Japanese \
  --output work/lesson-one.md \
  --auto-init
```

This single command imports audio, derives `ja-JP` from `Japanese`, transcribes the audio to transcript JSON, and renders plain transcript Markdown. It defaults to single-item URL import through `yt-dlp --no-playlist`.

## Local Media Input

```bash
cli/generate-markdown.sh \
  --input ~/Desktop/recording.wav \
  --language English \
  --output work/recording-transcript.md \
  --auto-init
```

Use this path for Audio Hijack recordings or any existing local audio/video file. The Markdown title is derived from the input filename unless `--title` is provided.

## Optional Overrides

```bash
cli/generate-markdown.sh \
  --input ~/Desktop/recording.wav \
  --language English \
  --locale en-GB \
  --title "Manual Transcript Title" \
  --output work/recording-transcript.md \
  --auto-init
```

Use `--locale` for regional ASR variants and `--title` when the generated title should not come from the source filename.

## Backends

The default backend is `faster-whisper small` with CPU `int8`, which is the recommended local option for an 8 GB Mac. `--auto-init` authorizes ListenKit to create `ListenKit/.venv` and install `faster-whisper` on first use. Do not manually run `python3 -m venv .venv` from a parent directory; use `--auto-init` or `cli/init-faster-whisper.sh` so the environment stays inside this repo. Use `--engine apple` if you want the bundled Apple Speech backend. See `INSTALL.md`.

## Low-Level CLI

The high-level command is the recommended interface for URL or local media input. The lower-level commands remain available for debugging, caching, and advanced workflows:

- `cli/import-audio.sh`
- `cli/transcribe-audio.sh`
- `cli/render-listening-note.py`

## Agent Adapters

Use one adapter when you want an agent to run the same high-level workflow:

- Codex: `adapters/codex/SKILL.md`
- Claude: `adapters/claude/CLAUDE.md`
- Cursor: `adapters/cursor/foreign-listening.md`
