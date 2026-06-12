# ListenKit

Local-first multilingual audio and video transcription toolchain. ListenKit turns URL or local media input into plain transcript Markdown plus same-stem transcript JSON.

## Quick Try

```bash
git clone <repo-url>
cd ListenKit
# macOS/Homebrew path. Linux users should install yt-dlp and ffmpeg with their package manager.
brew install yt-dlp ffmpeg
cli/generate-markdown.sh --help
cli/generate-markdown.sh --url "https://example.com/video" --language Japanese --output work/sample.md --auto-init
```

This writes:

```text
work/sample.md
work/sample.json
```

## Install For Your AI Agent

If you know your agent rules or context path:

```bash
cli/install-agent-instructions.sh --target <your-agent-rules-file-or-dir>
```

If you do not know the target path yet, use the `--print` fallback described in `LLM_INTEGRATION.md`.

## Documentation

- `LLM_INTEGRATION.md`: AI/agent install and usage contract
- `docs/install.md`: dependencies, backend setup, and troubleshooting
- `docs/debugging.md`: lower-level maintenance and debugging interfaces
- `docs/output-format.md`: transcript Markdown and JSON output shape
- `cli/check-runtime.sh`: read-only Python 3.14 and faster-whisper health check

## What It Does

```text
URL or local media
  -> cli/generate-markdown.sh
  -> transcript Markdown + same-stem transcript JSON
```

Inputs:

- yt-dlp-supported URLs
- Local audio, video, or media files
- Audio Hijack recordings saved as local files

Output:

- Plain Markdown with source metadata and transcript text
- Same-stem transcript JSON with normalized text, segments, engine metadata, locale, and timing status
- Optional audio clips exported from a downstream time-range manifest through `cli/export-audio-slices.py`

## What It Is Not

- Not tied to Codex. Codex is only one adapter.
- Not tied to Japanese. Japanese, English, Chinese, and Korean labels are supported by the public CLI.
- Not a note-taking, language-learning, Obsidian, Anki, or spaced-repetition system.
- Not a source of copyrighted audio or transcripts.

## Adapters

- Generic agent instructions: `adapters/agent/listenkit-agent-instructions.md`
- Codex: `adapters/codex/SKILL.md`
- Claude: `adapters/claude/CLAUDE.md`
- Cursor: `adapters/cursor/foreign-listening.md`

Adapters should call the public `cli/generate-markdown.sh` entrypoint for normal use, then consume either the generated Markdown or same-stem JSON. When a downstream workflow has selected time ranges, call `cli/export-audio-slices.py` instead of invoking `ffmpeg` directly. Adapters should not reimplement import, subtitle extraction, transcription, rendering, or downstream note systems.

## Privacy and Copyright

The default transcription route uses local `faster-whisper`; the first run may download model files. Apple Speech is available as an optional local macOS backend. Downstream tools that consume transcript text may send it to the model provider you use. Only process material you have the right to use.

See `PRIVACY_AND_COPYRIGHT.md`.
