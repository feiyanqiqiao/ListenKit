# Cursor Rule: ListenKit

When working in this repository, use the CLI scripts as the source of truth:

- `cli/generate-markdown.sh` for normal URL or local audio/video -> Markdown workflows
- `cli/generate-markdown.sh --output path/name.md` also writes `path/name.json` for structured transcript consumption
- URL workflows try platform subtitles first while still importing local listening audio
- lower-level import, subtitle extraction, ASR, rendering, raw downloader, and `tools/*` workflows are debugging and maintenance interfaces only

Do not duplicate business logic inside editor rules.

Expected Markdown output contains:

- `Source`
- `Transcript`

Keep this adapter focused on transcript generation. Do not add learning-note templates, Obsidian, Anki, or review-system structures unless a downstream project asks for that transformation.
