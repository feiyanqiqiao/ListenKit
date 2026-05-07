# Audio Hijack

Audio Hijack is an optional capture route for sources that cannot be downloaded directly.

Recommended workflow:

1. Create a session that records the target app or system audio.
2. Save the recording as WAV, AIFF, M4A, or MP3.
3. Stop recording after the clip ends.
4. Generate transcript artifacts from the local file:

```bash
cli/generate-markdown.sh \
  --input ~/Music/AudioHijack/session-recording.wav \
  --language Japanese \
  --output work/my-recording.md \
  --auto-init
```

This writes both `work/my-recording.md` and `work/my-recording.json`.

This project does not automate or configure Audio Hijack in v1.
