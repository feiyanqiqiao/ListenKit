# Quickstart

## 1. URL Input

```bash
brew install yt-dlp ffmpeg

cli/import-audio.sh \
  --url "https://example.com/video" \
  --output-dir work/audio \
  --base-name lesson-one
```

The command defaults to single-item mode and passes `--no-playlist` to `yt-dlp`.

## 2. Local Audio Input

```bash
cli/import-audio.sh \
  --input ~/Desktop/recording.wav \
  --output-dir work/audio \
  --base-name recording \
  --format m4a
```

Use this path for Audio Hijack recordings or any existing local audio file.

## 3. Transcribe

```bash
cli/transcribe-audio.sh \
  --audio-path work/audio/recording.m4a \
  --locale en-US \
  --output work/recording-transcript.json
```

v1 expects an Apple Speech helper at `tools/apple-speech-helper/run-apple-speech-helper.sh`. See `INSTALL.md`.

## 4. Render Markdown

```bash
cli/render-listening-note.py \
  --audio-path work/audio/recording.m4a \
  --transcript-json work/recording-transcript.json \
  --title "Recording Practice" \
  --language English \
  --output work/recording-note.md
```

## 5. AI Editing

Use one adapter:

- Codex: `adapters/codex/SKILL.md`
- Claude: `adapters/claude/CLAUDE.md`
- Cursor: `adapters/cursor/foreign-listening.md`

Ask the agent to complete `Listening Focus`, `Useful Expressions`, and `Study Plan` without adding long-term review systems.

