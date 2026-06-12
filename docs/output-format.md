# Output Format

Rendered transcript Markdown uses a fixed section contract:

```markdown
# Title

## Source

## Transcript
```

## Section Rules

- `Source`: source reference or audio filename, language, locale, transcript engine, timing status, generation time.
- `Transcript`: ASR text, lightly cleaned for spacing and paragraph breaks.

The format is plain Markdown. ListenKit does not add learning-analysis sections; downstream projects can transform the transcript into their own note format.

## Transcript JSON

Built-in backends emit schema version 1:

```json
{
  "schema_version": 1,
  "engine": "faster-whisper",
  "locale": "ja-JP",
  "full_text": "...",
  "segments": [{"start": 0.0, "end": 1.2, "text": "..."}],
  "timing_complete": true
}
```

The required semantic fields are `engine`, `locale`, `full_text`, `segments`, and `timing_complete`. Readers accept older payloads without `schema_version` as legacy v1. They reject an explicit unknown schema version instead of guessing how to interpret it.
