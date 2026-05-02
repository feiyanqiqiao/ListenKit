# Cursor Rule: Foreign Listening Material

When working in this repository, use the CLI scripts as the source of truth:

- `cli/import-audio.sh`
- `cli/transcribe-audio.sh`
- `cli/render-listening-note.py`

Do not duplicate business logic inside editor rules.

Expected output is plain Markdown with:

- `Source`
- `Transcript`
- `Listening Focus`
- `Useful Expressions`
- `Study Plan`

Keep analysis concise and practical for listening practice. Do not add Obsidian, Anki, or spaced-repetition structures unless the user asks.

