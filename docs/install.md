# Install

This document covers system dependencies, backend initialization, and troubleshooting. Normal users and external agents should run `cli/generate-markdown.sh`; commands such as `cli/transcribe-audio.sh` are backend or debugging references, not the public agent entrypoint.

## Dependencies

```bash
brew install yt-dlp ffmpeg
```

Linux users should install equivalent `yt-dlp` and `ffmpeg` packages with their system package manager.

Homebrew Python 3.14 is required for the faster-whisper runtime. Other lightweight maintenance scripts remain compatible with Python 3.10+, but the supported ASR environment is `~/Library/Caches/ListenKit/venvs/cpython-314`, built from Python 3.14.

The runtime is deliberately stored outside the repository and outside iCloud Drive. It contains large native libraries whose loading can stall while iCloud is hydrating or coordinating files. Do not place the runtime under `Library/Mobile Documents`.

The optional Apple Speech backend requires macOS with Speech APIs and Xcode command line tools for the bundled Swift helper build.

## faster-whisper Backend

The default ASR backend is `faster-whisper`:

```bash
cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP --auto-init
```

`--auto-init` authorizes ListenKit to create the local Cache runtime, install `faster-whisper`, and continue transcription. For a one-time manual setup, run this script from anywhere:

```bash
cli/init-faster-whisper.sh
```

The initializer installs the direct dependency pinned in `requirements-faster-whisper.txt`. Transitive packages such as CTranslate2, ONNX Runtime, and PyAV are selected by faster-whisper's dependency constraints. The runtime snapshot under `docs/runtime-snapshot-python314.txt` is diagnostic evidence only and is not an installation lock file.

Check an existing environment without changing it:

```bash
cli/check-runtime.sh
```

Do not initialize with `python3 -m venv .venv` in the repository. Use the ListenKit initializer so the native runtime remains outside iCloud and uses the supported Python version.

To use a different runtime location, set `LISTENKIT_FASTER_WHISPER_VENV_DIR`. The target must remain outside iCloud Drive:

```bash
LISTENKIT_FASTER_WHISPER_VENV_DIR=/path/outside/icloud \
  cli/init-faster-whisper.sh
```

Advanced users can use an external Python environment:

```bash
FASTER_WHISPER_PYTHON=/path/to/python \
  cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP
```

Default settings:

- model: `small`
- device: `cpu`
- compute type: `int8`
- beam size: `5`

This is the recommended starting point for an 8 GB Mac. The first run may download the model and take significantly longer than later cached runs.

Common faster-whisper failures:

- auto-init was not authorized in a non-interactive shell
- `faster-whisper` is not installed in the selected Python environment
- model download is blocked or incomplete
- the audio file is missing or unreadable
- the selected runtime is not Python 3.14
- the selected runtime is stored in iCloud Drive
- the import health check exceeds 60 seconds

## Apple Speech Backend

Apple Speech is an optional local macOS backend. ListenKit bundles a small helper app that is built on first use and launched through `/usr/bin/open` so macOS can show Speech permission prompts.

The default helper lives at:

```text
tools/apple-speech-helper/run-apple-speech-helper.sh
```

Use it with:

```bash
cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP --engine apple
```

You can still point to an external helper:

```bash
APPLE_SPEECH_HELPER=/path/to/run-apple-speech-helper.sh \
  cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP --engine apple
```

The helper contract is:

```bash
run-apple-speech-helper.sh --audio-path <path> --locale <bcp47>
```

It must print JSON with:

```json
{
  "engine": "apple",
  "locale": "ja-JP",
  "full_text": "...",
  "segments": [{"start": 0.0, "end": 1.2, "text": "..."}],
  "timing_complete": true
}
```

Common Apple Speech failures:

- Speech recognition permission denied
- macOS version too old for the selected Speech APIs
- Locale not supported on the current Mac
- Required speech assets are not installed
- Audio file path is missing or unreadable
- Xcode command line tools or the macOS SDK are missing

## Audio Hijack

Audio Hijack is optional. Use it to record system or app audio into a local file, then pass that file to:

```bash
cli/import-audio.sh --input <recording> --output-dir work/audio
```
