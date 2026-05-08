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

This single command derives `ja-JP` from `Japanese`, tries URL subtitles first, imports local audio for listening, and renders plain transcript Markdown. If no usable subtitles are available, it falls back to ASR from the imported audio. URL import defaults to single-item mode.

It writes both `work/lesson-one.md` and the structured transcript artifact `work/lesson-one.json`.

## Local Media Input

```bash
cli/generate-markdown.sh \
  --input ~/Desktop/recording.wav \
  --language English \
  --output work/recording-transcript.md \
  --auto-init
```

Use this path for Audio Hijack recordings or any existing local audio/video file. For URL input, the Markdown title defaults to the video's platform title when available. For local input, the Markdown title is derived from the input filename unless `--title` is provided.

This writes both `work/recording-transcript.md` and `work/recording-transcript.json`.

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

Use `--locale` for regional ASR variants and `--title` when the generated title should not use the URL platform title or local source filename.

## Backends

The default backend is `faster-whisper small` with CPU `int8`, which is the recommended local option for an 8 GB Mac. `--auto-init` authorizes ListenKit to create `ListenKit/.venv` and install `faster-whisper` on first use. Do not manually run `python3 -m venv .venv` from a parent directory; use `--auto-init` or `cli/init-faster-whisper.sh` so the environment stays inside this repo. Use `--engine apple` if you want the bundled Apple Speech backend. See `INSTALL.md`.

## Agent Integrations

External agents should use `cli/generate-markdown.sh` as the only public ListenKit entrypoint, then consume either the generated Markdown or same-stem JSON artifact.

See `LLM_INTEGRATION.md` for the integration contract. Lower-level commands are maintenance/debugging interfaces; see `docs/debugging.md`.

## Agent Adapters

Use one adapter when you want an agent to run the same high-level workflow:

- Codex: `adapters/codex/SKILL.md`
- Claude: `adapters/claude/CLAUDE.md`
- Cursor: `adapters/cursor/foreign-listening.md`
