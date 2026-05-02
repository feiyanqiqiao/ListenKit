---
name: foreign-listening-material
description: Generate multilingual listening-study Markdown notes from URL or local audio by using the repository CLI for audio import, Apple Speech transcription, and draft rendering, then applying AI judgment to complete listening focus, useful expressions, and study plan sections.
---

# Foreign Listening Material

Use this skill when the user wants to turn a foreign-language audio/video URL, local audio file, or Audio Hijack recording into a Markdown listening-study note.

## Workflow

1. Identify the input:
   - URL: use `cli/import-audio.sh --url`
   - local audio or Audio Hijack recording: use `cli/import-audio.sh --input`
2. Transcribe with `cli/transcribe-audio.sh --engine apple --locale <bcp47>`.
3. Render a draft note with `cli/render-listening-note.py`.
4. Read the transcript and complete only:
   - `## Listening Focus`
   - `## Useful Expressions`
   - `## Study Plan`

## Rules

- Keep output as plain Markdown.
- Do not add Obsidian frontmatter, wikilinks, Anki cards, or spaced-repetition scheduling unless the user explicitly asks.
- Select 0-8 useful expressions. Leave the section empty if the transcript has no strong candidates.
- For Japanese, consider particles, conjugation, politeness, sound changes, and sentence endings.
- For English, consider weak forms, linking, reductions, phrasal verbs, and intonation.
- For other languages, use general listening blockers and avoid unsupported grammar claims.
- Respect copyright. Do not help redistribute copyrighted transcripts or audio.

## CLI Examples

```bash
cli/import-audio.sh --url "https://example.com/video" --output-dir work/audio --base-name clip
cli/transcribe-audio.sh --audio-path work/audio/clip.m4a --locale ja-JP --output work/clip.json
cli/render-listening-note.py --audio-path work/audio/clip.m4a --transcript-json work/clip.json --title "Clip" --language Japanese --output work/clip.md
```

