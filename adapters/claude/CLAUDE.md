# Foreign Listening Material

Use the repository CLI. Do not reimplement the pipeline in prompt text.

Workflow:

1. URL input: `cli/import-audio.sh --url <url> --output-dir work/audio --base-name <name>`
2. Local or Audio Hijack input: `cli/import-audio.sh --input <path> --output-dir work/audio --base-name <name>`
3. Transcribe: `cli/transcribe-audio.sh --audio-path <audio> --locale <bcp47> --output <json>`
4. Render: `cli/render-listening-note.py --audio-path <audio> --transcript-json <json> --title <title> --language <label> --output <md>`
5. Edit the Markdown note by completing `Listening Focus`, `Useful Expressions`, and `Study Plan`.

Keep the note plain Markdown. Do not add Obsidian-only syntax, Anki cards, or review scheduling unless explicitly requested.

For Japanese, pay attention to particles, conjugation, politeness, and sound changes. For English, pay attention to weak forms, linking, reductions, phrasal verbs, and intonation. For other languages, use cautious general listening analysis.

