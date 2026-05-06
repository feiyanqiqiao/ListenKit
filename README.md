# ListenKit

Local-first multilingual audio and video transcription toolchain, with optional agent adapters.

This project turns foreign-language audio or video into transcript JSON and plain transcript Markdown. It is a small toolchain, not a language-learning system.

## What It Does

```text
URL or local audio
  -> cli/import-audio.sh
  -> cli/transcribe-audio.sh
  -> cli/render-listening-note.py
  -> transcript Markdown
```

Inputs:

- yt-dlp-supported URLs
- Local audio files
- Audio Hijack recordings saved as local files

Output:

- Transcript JSON
- Plain Markdown with source metadata and transcript text

## What It Is Not

- Not tied to Codex. Codex is only one adapter.
- Not tied to Japanese. Japanese and English are the first sample languages.
- Not a note-taking, language-learning, Obsidian, Anki, or spaced-repetition system.
- Not a source of copyrighted audio or transcripts.

## Requirements

- Python 3.10+ for the default local `faster-whisper` backend
- macOS for the optional Apple Speech backend
- `yt-dlp` for URL import
- `ffmpeg` for audio conversion
- Python 3.10+ for Markdown rendering and tests
- Xcode command line tools for the optional Apple Speech helper build

Install common dependencies:

```bash
brew install yt-dlp ffmpeg
```

## Quick Example

```bash
audio_path=$(cli/import-audio.sh \
  --url "https://example.com/video" \
  --output-dir work/audio \
  --base-name sample \
  --format mp3)

cli/transcribe-audio.sh \
  --audio-path "$audio_path" \
  --locale ja-JP \
  --output work/sample-transcript.json \
  --auto-init

cli/render-listening-note.py \
  --audio-path "$audio_path" \
  --transcript-json work/sample-transcript.json \
  --title "Sample Transcript" \
  --language Japanese \
  --output work/sample-transcript.md
```

The default backend is `faster-whisper small` on CPU with `int8` compute. This is the recommended starting point for an 8 GB Mac. On first use, pass `--auto-init` to let ListenKit create `ListenKit/.venv` and install `faster-whisper`; advanced users can run `cli/init-faster-whisper.sh` once or set `FASTER_WHISPER_PYTHON=/path/to/python`. Do not run `python3 -m venv .venv` from a parent directory, because that creates an environment outside the ListenKit repo. To use the bundled Apple Speech helper instead, pass `--engine apple`; if your Apple Speech helper lives outside this repository, set `APPLE_SPEECH_HELPER=/path/to/helper`.

## Adapters

- Codex: `adapters/codex/SKILL.md`
- Claude: `adapters/claude/CLAUDE.md`
- Cursor: `adapters/cursor/foreign-listening.md`

All adapters call the same CLI. They should not reimplement import, transcription, rendering, or downstream note systems.

`cli/import-audio.sh` can also save URL sidecars with `--write-info-json` and `--write-thumbnail`, use `--quality <value>`, and use a custom `--filename-template` when you need yt-dlp naming control.

## Privacy and Copyright

The default transcription route uses local `faster-whisper`; the first run may download model files. Apple Speech is available as an optional local macOS backend. Downstream tools that consume transcript text may send it to the model provider you use. Only process material you have the right to use.

See `PRIVACY_AND_COPYRIGHT.md`.
