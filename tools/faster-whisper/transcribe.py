#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe one audio file with faster-whisper.")
    parser.add_argument("audio_path")
    parser.add_argument("--locale", default="ja-JP")
    parser.add_argument("--model", default="small")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--beam-size", type=int, default=5)
    return parser.parse_args()


def locale_to_language(locale: str) -> str | None:
    if not locale:
        return None
    return locale.split("-", 1)[0].lower()


def emit(payload: dict, status: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return status


def main() -> int:
    args = parse_args()
    audio_path = Path(args.audio_path)
    if not audio_path.exists():
        return emit(
            {
                "schema_version": 1,
                "error": {
                    "type": "file_not_found",
                    "message": f"Audio file not found: {audio_path}",
                }
            },
            1,
        )

    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(args.model, device="cpu", compute_type=args.compute_type)
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=locale_to_language(args.locale),
            beam_size=args.beam_size,
            condition_on_previous_text=False,
            vad_filter=False,
        )
        segments = [
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            }
            for segment in segments_iter
            if segment.text.strip()
        ]
        return emit(
            {
                "schema_version": 1,
                "engine": "faster-whisper",
                "model": args.model,
                "compute_type": args.compute_type,
                "locale": args.locale,
                "language": info.language,
                "language_probability": info.language_probability,
                "full_text": "\n".join(segment["text"] for segment in segments),
                "segments": segments,
                "timing_complete": True,
            }
        )
    except Exception as exc:
        print(f"faster-whisper failed: {exc}", file=sys.stderr)
        return emit(
            {
                "schema_version": 1,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                }
            },
            1,
        )


if __name__ == "__main__":
    raise SystemExit(main())
