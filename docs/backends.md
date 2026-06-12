# Backends

This is a maintenance reference for ListenKit internals. External LLM agents
should follow `LLM_INTEGRATION.md` and call `cli/generate-markdown.sh` instead
of calling backend commands directly.

## v1

Two local ASR backends and one URL subtitle backend are supported:

- `faster-whisper` is the default
- `apple` is optional and uses the bundled Apple Speech helper by default
- `yt-dlp-subtitles` is used by the high-level URL workflow when platform subtitles are available

The default CLI boundary is:

```bash
cli/transcribe-audio.sh --audio-path <path> --locale <bcp47> --auto-init
```

The faster-whisper Python selection order is:

1. `FASTER_WHISPER_PYTHON`
2. `LISTENKIT_FASTER_WHISPER_VENV_PYTHON`, when explicitly set
3. `~/Library/Caches/ListenKit/venvs/cpython-314/bin/python`
4. authorized initialization through `--auto-init`, `LISTENKIT_AUTO_INIT=1`, or an interactive TTY prompt

Non-interactive callers should pass `--auto-init` or run `cli/init-faster-whisper.sh` before transcription.

The Cache runtime is owned exclusively by ListenKit. Downstream projects must call ListenKit through its CLI and JSON contract; they must not import packages from this environment. `cli/check-runtime.sh` verifies Python 3.14, the runtime location, the installed faster-whisper distribution, and a bounded import without modifying the environment.

The runtime must not live under iCloud Drive (`Library/Mobile Documents`). It contains native libraries and model dependencies that need predictable local filesystem access. `LISTENKIT_FASTER_WHISPER_VENV_DIR` can override the default root, but the initializer and health check reject iCloud-backed targets.

Avoid documenting or using raw `python3 -m venv .venv` setup commands. They bypass the supported runtime path and health checks.

Fixed faster-whisper defaults:

- model: `small`
- device: `cpu`
- compute type: `int8`
- beam size: `5`

Apple Speech can be forced with:

```bash
cli/transcribe-audio.sh --audio-path <path> --locale <bcp47> --engine apple
```

The bundled helper is built from `tools/apple-speech-helper/` on first use. It launches a local macOS app through `/usr/bin/open` so Speech permission prompts can be shown. Set `APPLE_SPEECH_HELPER=/path/to/helper` only when you want to override the bundled helper.

Any helper must return:

- `schema_version` (`1` for current built-in backends)
- `engine`
- `locale`
- `full_text`
- `segments`
- `timing_complete`

The subtitle backend uses the same transcript JSON shape. It is only used for URL input by `cli/generate-markdown.sh`; `cli/transcribe-audio.sh` remains a local audio ASR command.

Readers accept legacy payloads without `schema_version` as v1 for compatibility. An explicit version other than `1` is unsupported and must fail before rendering or downstream processing.

If a backend fails after producing JSON, it should return an `error` object as the first top-level field:

```json
{
  "error": {
    "type": "backend_error",
    "message": "human-readable failure reason"
  }
}
```

An error payload is terminal. Renderers and adapters must not render it as a transcript; they should surface the error and ask the user to fix the backend or rerun transcription. The shell CLI checks for this leading top-level `error` shape without requiring Python on the Apple Speech path.

## Future Backends

Potential future engines:

- cloud ASR APIs

Any future backend should preserve the same transcript JSON shape so adapters and renderers do not fork.
