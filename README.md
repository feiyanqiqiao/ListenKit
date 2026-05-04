# ListenKit

Local-first multilingual listening-material generator, with optional agent adapters.

This project turns foreign-language audio or video into a Markdown listening-study note. It is a small toolchain, not a full language-learning system.

## What It Does

```text
URL or local audio
  -> cli/import-audio.sh
  -> cli/transcribe-audio.sh
  -> cli/render-listening-note.py
  -> AI-assisted Markdown study note
```

Inputs:

- yt-dlp-supported URLs
- Local audio files
- Audio Hijack recordings saved as local files

Output:

- A plain Markdown note with transcript, listening focus, useful expressions, and a short study plan

## What It Is Not

- Not tied to Codex. Codex is only one adapter.
- Not tied to Japanese. Japanese and English are the first sample languages.
- Not an Obsidian vault, Anki deck, or spaced-repetition system.
- Not a source of copyrighted audio or transcripts.

## Requirements

- Python environment with `faster-whisper` for the default local ASR backend
- macOS for the optional Apple Speech backend
- `yt-dlp` for URL import
- `ffmpeg` for audio conversion
- Python 3.10+ for Markdown rendering and tests

Install common dependencies:

```bash
brew install yt-dlp ffmpeg
python3 -m venv .venv
.venv/bin/pip install faster-whisper
export FASTER_WHISPER_PYTHON="$PWD/.venv/bin/python"
```

## Quick Example

```bash
audio_path=$(cli/import-audio.sh \
  --url "https://example.com/video" \
  --output-dir work/audio \
  --base-name sample)

cli/transcribe-audio.sh \
  --audio-path "$audio_path" \
  --locale ja-JP \
  --output work/sample-transcript.json

cli/render-listening-note.py \
  --audio-path "$audio_path" \
  --transcript-json work/sample-transcript.json \
  --title "Sample Listening Note" \
  --language Japanese \
  --output work/sample-note.md
```

The default backend is `faster-whisper small` on CPU with `int8` compute. This is the recommended starting point for an 8 GB Mac. To use Apple Speech instead, pass `--engine apple`; if your Apple Speech helper lives outside this repository, set `APPLE_SPEECH_HELPER=/path/to/helper`.

Then ask your agent or editor to fill `Listening Focus`, `Useful Expressions`, and `Study Plan` using the adapter instructions.

## Adapters

- Codex: `adapters/codex/SKILL.md`
- Claude: `adapters/claude/CLAUDE.md`
- Cursor: `adapters/cursor/foreign-listening.md`

All adapters call the same CLI. They should not reimplement import, transcription, or rendering logic.

## Privacy and Copyright

The default transcription route uses local `faster-whisper`; the first run may download model files. Apple Speech is available as an optional local macOS backend. The AI editing stage may send transcript text to the model provider you use. Only process material you have the right to use.

See `PRIVACY_AND_COPYRIGHT.md`.
