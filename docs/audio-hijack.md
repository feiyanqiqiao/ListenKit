# Audio Hijack

Audio Hijack is an optional capture route for sources that cannot be downloaded directly.

Recommended workflow:

1. Create a session that records the target app or system audio.
2. Save the recording as WAV, AIFF, M4A, or MP3.
3. Stop recording after the clip ends.
4. Import the local file:

```bash
cli/import-audio.sh \
  --input ~/Music/AudioHijack/session-recording.wav \
  --output-dir work/audio \
  --base-name my-recording \
  --format m4a
```

This project does not automate or configure Audio Hijack in v1.

