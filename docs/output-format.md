# Output Format

Rendered transcript Markdown uses a fixed section contract:

```markdown
# Title

## Source

## Transcript
```

## Section Rules

- `Source`: source reference or audio filename, language, locale, ASR engine, timing status, generation time.
- `Transcript`: ASR text, lightly cleaned for spacing and paragraph breaks.

The format is plain Markdown. ListenKit does not add learning-analysis sections; downstream projects can transform the transcript into their own note format.
