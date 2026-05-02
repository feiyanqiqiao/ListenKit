# Backends

## v1

Only Apple Speech is implemented as an ASR backend.

The CLI boundary is:

```bash
cli/transcribe-audio.sh --audio-path <path> --locale <bcp47> --engine apple
```

The helper must return:

- `engine`
- `locale`
- `full_text`
- `segments`
- `timing_complete`

## Future Backends

Potential future engines:

- local Whisper
- cloud ASR APIs
- subtitle extraction when a source already has captions

Any future backend should preserve the same transcript JSON shape so adapters and renderers do not fork.

