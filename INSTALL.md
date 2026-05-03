# Install

## Dependencies

```bash
brew install yt-dlp ffmpeg
```

Python 3.10+ is required for `cli/render-listening-note.py` and tests.

## faster-whisper Backend

The default ASR backend is `faster-whisper`:

```bash
python3 -m venv .venv
.venv/bin/pip install faster-whisper
export FASTER_WHISPER_PYTHON="$PWD/.venv/bin/python"
```

ListenKit calls:

```bash
cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP
```

Default settings:

- model: `small`
- device: `cpu`
- compute type: `int8`
- beam size: `5`

This is the recommended starting point for an 8 GB Mac. The first run may download the model and take significantly longer than later cached runs.

Common faster-whisper failures:

- `FASTER_WHISPER_PYTHON` is not set
- `faster-whisper` is not installed in that Python environment
- model download is blocked or incomplete
- the audio file is missing or unreadable

## Apple Speech Backend

Apple Speech is an optional backend.

`cli/transcribe-audio.sh` expects an executable helper at:

```text
tools/apple-speech-helper/run-apple-speech-helper.sh
```

You can also point to an external helper:

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

## Audio Hijack

Audio Hijack is optional. Use it to record system or app audio into a local file, then pass that file to:

```bash
cli/import-audio.sh --input <recording> --output-dir work/audio
```
