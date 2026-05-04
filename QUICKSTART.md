# Quickstart

## 1. URL Input

```bash
brew install yt-dlp ffmpeg

audio_path=$(cli/import-audio.sh \
  --url "https://example.com/video" \
  --output-dir work/audio \
  --base-name lesson-one)
```

The command prints the imported audio path, which the example stores in `audio_path`. It defaults to single-item mode and passes `--no-playlist` to `yt-dlp`.

## 2. Local Audio Input

```bash
audio_path=$(cli/import-audio.sh \
  --input ~/Desktop/recording.wav \
  --output-dir work/audio \
  --base-name recording \
  --format m4a)
```

Use this path for Audio Hijack recordings or any existing local audio file.

## 3. Transcribe

```bash
python3 -m venv .venv
.venv/bin/pip install faster-whisper
export FASTER_WHISPER_PYTHON="$PWD/.venv/bin/python"

cli/transcribe-audio.sh \
  --audio-path "$audio_path" \
  --locale en-US \
  --output work/recording-transcript.json
```

The default backend is `faster-whisper small` with CPU `int8`, which is the recommended local option for an 8 GB Mac. Use `--engine apple` if you want the optional Apple Speech backend. See `INSTALL.md`.

## 4. Render Markdown

```bash
cli/render-listening-note.py \
  --audio-path "$audio_path" \
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
