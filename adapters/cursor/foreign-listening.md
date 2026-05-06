# Cursor Rule: ListenKit

When working in this repository, use the CLI scripts as the source of truth:

- `cli/generate-markdown.sh` for normal URL or local audio/video -> Markdown workflows
- URL workflows try platform subtitles first while still importing local listening audio
- `cli/import-audio.sh`, `cli/transcribe-audio.sh`, and `cli/render-listening-note.py` only for debugging, caching, or advanced workflows

Do not duplicate business logic inside editor rules.

Expected Markdown output contains:

- `Source`
- `Transcript`

Keep this adapter focused on transcript generation. Do not add learning-note templates, Obsidian, Anki, or review-system structures unless a downstream project asks for that transformation.
