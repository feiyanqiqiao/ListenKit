# Examples

The examples in this repository are synthetic and safe to redistribute.

No sample audio files are bundled. These examples use the lower-level render-only command against synthetic transcript JSON. The high-level `cli/generate-markdown.sh` command is for URL or local media input.

## Japanese Sample

```bash
cli/render-listening-note.py \
  --source-ref examples/sample-ja.m4a \
  --transcript-json examples/sample-transcript-ja.json \
  --title "Japanese Cafe Description" \
  --language Japanese \
  --output examples/sample-note-ja.md
```

## English Sample

```bash
cli/render-listening-note.py \
  --source-ref examples/sample-en.m4a \
  --transcript-json examples/sample-transcript-en.json \
  --title "English Library Description" \
  --language English \
  --output examples/sample-note-en.md
```

## Expected Markdown Shape

Every rendered Markdown file contains:

- `Source`
- `Transcript`

The renderer does not add learning-analysis sections. Downstream projects can build their own note templates from the transcript JSON or Markdown.
