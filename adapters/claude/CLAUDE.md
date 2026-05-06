# ListenKit

Use the repository CLI. Do not reimplement the pipeline in prompt text.

Workflow:

1. URL input: `cli/import-audio.sh --url <url> --output-dir work/audio --base-name <name>`
2. Local or Audio Hijack input: `cli/import-audio.sh --input <path> --output-dir work/audio --base-name <name>`
3. Transcribe: `cli/transcribe-audio.sh --audio-path <audio> --locale <bcp47> --output <json> --auto-init`; add `--engine apple` only when Apple Speech is requested.
4. Render: `cli/render-listening-note.py --audio-path <audio> --transcript-json <json> --title <title> --language <label> --output <md>`

Keep the output to transcript JSON or plain transcript Markdown. Do not add learning-note templates, Obsidian-only syntax, Anki cards, or review scheduling unless a downstream project explicitly requests that transformation.
