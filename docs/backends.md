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

If a backend fails after producing JSON, it should return an `error` object as the first top-level field:

```json
{
  "error": {
    "type": "backend_error",
    "message": "human-readable failure reason"
  }
}
```

An error payload is terminal. Renderers and adapters must not turn it into a study note; they should surface the error and ask the user to fix the backend or rerun transcription. The shell CLI checks for this leading top-level `error` shape without requiring Python on the Apple Speech path.

## Future Backends

Potential future engines:

- cloud ASR APIs
- subtitle extraction when a source already has captions

Any future backend should preserve the same transcript JSON shape so adapters and renderers do not fork.
