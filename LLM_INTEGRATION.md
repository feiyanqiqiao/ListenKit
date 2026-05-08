# ListenKit LLM Integration Contract

This document is the public contract for external LLM agents and automation
integrations.

## Public Entrypoint

Use one command for normal URL or local media workflows:

```bash
cli/generate-markdown.sh \
  --url "https://example.com/video" \
  --language Japanese \
  --output work/sample-transcript.md \
  --auto-init
```

For local media, replace `--url` with `--input <path>`.

ListenKit owns source acquisition, subtitle selection, ASR fallback, transcript
normalization, and plain transcript rendering behind this entrypoint. External
agents should not reimplement or bypass those stages.

For URL input, the Markdown title defaults to the video's platform title when
available. For local input, the title defaults to the source filename. Use
`--title` only when the caller needs an explicit override.

## Output Contract

For an output path like:

```text
work/sample-transcript.md
```

`cli/generate-markdown.sh` produces:

- `work/sample-transcript.md`: human-readable transcript Markdown
- `work/sample-transcript.json`: structured transcript JSON with normalized text,
  segments, source engine metadata, locale, and timing status

Downstream agents may consume either artifact:

- Use Markdown when the next step needs a readable transcript.
- Use JSON when the next step needs structured text, segments, timing, or engine
  metadata.

## Downstream Transformations

ListenKit stops at transcript normalization and plain transcript rendering. After
the Markdown or JSON exists, downstream agents may transform it into their own
products, such as:

- grammar articles
- learning notes
- summaries
- vocabulary lists
- review cards
- app-specific records

Those transformations are outside the ListenKit contract and should not be
implemented by bypassing ListenKit internals.

## Do Not Bypass The Entrypoint

In normal integrations, do not call these directly:

- `yt-dlp`
- `tools/*`
- `cli/extract-subtitles.sh`
- `cli/transcribe-audio.sh`
- `cli/import-audio.sh`
- `cli/render-listening-note.py`

These are maintenance and debugging interfaces. Calling them directly can skip
ListenKit's subtitle priority, cleanup, ASR fallback, output naming, provenance,
or transcript JSON normalization behavior.

Use direct low-level calls only when debugging ListenKit itself or maintaining
the pipeline. See `docs/debugging.md`.
