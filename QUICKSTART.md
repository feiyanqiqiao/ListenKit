# Quickstart

## 1. URL Input

```bash
brew install yt-dlp ffmpeg

audio_path=$(cli/import-audio.sh \
  --url "https://example.com/video" \
  --output-dir work/audio \
  --base-name lesson-one \
  --format mp3)
```

The command prints the imported audio path, which the example stores in `audio_path`. It defaults to single-item mode and passes `--no-playlist` to `yt-dlp`. Add `--write-info-json` or `--write-thumbnail` when you want yt-dlp sidecar files.

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
cli/transcribe-audio.sh \
  --audio-path "$audio_path" \
  --locale en-US \
  --output work/recording-transcript.json \
  --auto-init
```

The default backend is `faster-whisper small` with CPU `int8`, which is the recommended local option for an 8 GB Mac. `--auto-init` authorizes ListenKit to create `ListenKit/.venv` and install `faster-whisper` on first use. Do not manually run `python3 -m venv .venv` from a parent directory; use `--auto-init` or `cli/init-faster-whisper.sh` so the environment stays inside this repo. Use `--engine apple` if you want the bundled Apple Speech backend. See `INSTALL.md`.

## 4. Render Markdown

```bash
cli/render-listening-note.py \
  --audio-path "$audio_path" \
  --transcript-json work/recording-transcript.json \
  --title "Recording Transcript" \
  --language English \
  --output work/recording-transcript.md
```

The rendered Markdown contains source metadata and the transcript. Downstream projects can transform that transcript into their own note format.

## 5. Agent Adapters

Use one adapter when you want an agent to run the same import/transcribe/render CLI workflow:

- Codex: `adapters/codex/SKILL.md`
- Claude: `adapters/claude/CLAUDE.md`
- Cursor: `adapters/cursor/foreign-listening.md`
