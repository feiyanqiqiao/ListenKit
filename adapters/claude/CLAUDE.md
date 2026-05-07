# ListenKit

Use the repository CLI. Do not reimplement the pipeline in prompt text.

Normal workflow:

```bash
cli/generate-markdown.sh \
  --url <url> \
  --language <label> \
  --output <md> \
  --auto-init
```

The high-level command also accepts `--input <path>` as the single input source. It derives the ASR locale from `--language` and derives the Markdown title from the source filename unless optional overrides are provided.

For `--output path/name.md`, consume `path/name.md` as the readable transcript and `path/name.json` as the structured transcript artifact.

For URL input, the high-level command tries platform subtitles first and still attempts to import local audio. If subtitles are unavailable, it falls back to imported audio plus ASR.

Do not call lower-level import, subtitle extraction, ASR, rendering, raw downloader, or `tools/*` workflows in normal integrations. They are ListenKit debugging and maintenance interfaces only.

Keep the output to transcript JSON or plain transcript Markdown. Do not add learning-note templates, Obsidian-only syntax, Anki cards, or review scheduling unless a downstream project explicitly requests that transformation.
