# Cursor Rule: ListenKit

When working in this repository, use the CLI scripts as the source of truth:

- `cli/import-audio.sh`
- `cli/transcribe-audio.sh --auto-init` with its default faster-whisper backend
- `cli/render-listening-note.py`

Do not duplicate business logic inside editor rules.

Expected Markdown output contains:

- `Source`
- `Transcript`

Keep this adapter focused on transcript generation. Do not add learning-note templates, Obsidian, Anki, or review-system structures unless a downstream project asks for that transformation.
