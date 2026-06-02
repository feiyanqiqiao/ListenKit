# ListenKit Agent Instructions

Use ListenKit only through the public high-level transcript command during normal integrations.

## Normal Workflow

For a URL:

```bash
cli/generate-markdown.sh \
  --url "<url>" \
  --language <label> \
  --output <md> \
  --auto-init
```

For a local audio or video file:

```bash
cli/generate-markdown.sh \
  --input <path> \
  --language <label> \
  --output <md> \
  --auto-init
```

Rules:

- Provide exactly one input source: `--url` or `--input`.
- Always provide `--language` and `--output`.
- Use `--auto-init` unless the user explicitly chooses a different backend setup.
- For `--output path/name.md`, expect both `path/name.md` and `path/name.json`.
- If the user does not specify an output path, prefer `work/<safe-source-stem>-transcript.md`; if no stable source stem is available, use `work/transcript.md`.

Do not call these directly as an integration shortcut:

- `yt-dlp`
- `ffmpeg`
- `cli/import-audio.sh`
- `cli/extract-subtitles.sh`
- `cli/transcribe-audio.sh`
- `cli/render-listening-note.py`
- `tools/*`

Those are dependency, maintenance, or debugging interfaces. If `yt-dlp`, `ffmpeg`, Python, or backend initialization is missing, ask the user to install or authorize the missing dependency instead of bypassing `cli/generate-markdown.sh`.

ListenKit stops at plain transcript Markdown and same-stem transcript JSON. Downstream summaries, learning notes, vocabulary lists, cards, or app-specific records are separate transformations after ListenKit output exists.

If a downstream workflow has already selected explicit time ranges, export clips through the supported supplemental interface instead of calling `ffmpeg` directly:

```bash
cli/export-audio-slices.py \
  --input <audio> \
  --manifest <json> \
  --output-dir <dir> \
  --padding-seconds 0.15
```

The downstream workflow remains responsible for deciding what each time range means.
