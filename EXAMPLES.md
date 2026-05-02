# Examples

The examples in this repository are synthetic and safe to redistribute.

## Japanese Sample

```bash
cli/render-listening-note.py \
  --audio-path examples/sample-ja.m4a \
  --transcript-json examples/sample-transcript-ja.json \
  --title "Japanese Cafe Description" \
  --language Japanese \
  --output examples/sample-note-ja.md
```

## English Sample

```bash
cli/render-listening-note.py \
  --audio-path examples/sample-en.m4a \
  --transcript-json examples/sample-transcript-en.json \
  --title "English Library Description" \
  --language English \
  --output examples/sample-note-en.md
```

## Expected Note Shape

Every note contains:

- `Source`
- `Transcript`
- `Listening Focus`
- `Useful Expressions`
- `Study Plan`

The renderer creates a draft. An agent or human should complete the learning analysis.

