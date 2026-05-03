# Backends

## v1

Two local ASR backends are supported:

- `faster-whisper` is the default
- `apple` is optional and requires an external Apple Speech helper

The default CLI boundary is:

```bash
FASTER_WHISPER_PYTHON=/path/to/venv/bin/python \
  cli/transcribe-audio.sh --audio-path <path> --locale <bcp47>
```

Fixed faster-whisper defaults:

- model: `small`
- device: `cpu`
- compute type: `int8`
- beam size: `5`

Apple Speech can be forced with:

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

- cloud ASR APIs
- subtitle extraction when a source already has captions

Any future backend should preserve the same transcript JSON shape so adapters and renderers do not fork.
