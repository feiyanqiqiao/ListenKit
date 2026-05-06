# Install

## Dependencies

```bash
brew install yt-dlp ffmpeg
```

Python 3.10+ is required for `cli/render-listening-note.py` and tests.

The optional Apple Speech backend requires macOS with Speech APIs and Xcode command line tools for the bundled Swift helper build.

## faster-whisper Backend

The default ASR backend is `faster-whisper`:

```bash
cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP --auto-init
```

`--auto-init` authorizes ListenKit to create repo-local `ListenKit/.venv`, install `faster-whisper`, and continue transcription. For a one-time manual setup, run this script from anywhere:

```bash
cli/init-faster-whisper.sh
```

Do not initialize with `python3 -m venv .venv` from a parent directory. That command depends on your current working directory and can create a misplaced environment such as `<vault-parent>/.venv`. The ListenKit init script derives the target directory from its own path.

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
