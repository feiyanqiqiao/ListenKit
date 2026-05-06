---
name: generate-markdown
description: Generate plain transcript Markdown from an existing ListenKit transcript JSON file.
---

# Generate Markdown

Use this skill when the user already has a ListenKit transcript JSON file and wants to render it as plain transcript Markdown.

## Workflow

1. Confirm the input transcript JSON path.
2. Choose the source audio path, title, language label, and output Markdown path.
3. Render transcript Markdown with `cli/render-listening-note.py`.

## Rules

- Keep output as plain Markdown.
- Do not import audio, download media, or run ASR transcription from this skill.
- Do not add learning-note templates, Obsidian frontmatter, wikilinks, Anki cards, or review scheduling unless a downstream project explicitly asks.
- Keep language-learning analysis outside this generic transcription skill.
- Respect copyright. Do not help redistribute copyrighted transcripts or audio.

## CLI Examples

```bash
cli/render-listening-note.py --audio-path work/audio/clip.mp3 --transcript-json work/clip.json --title "Clip" --language Japanese --output work/clip.md
```
