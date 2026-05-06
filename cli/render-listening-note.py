#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render transcript JSON as plain Markdown.")
    parser.add_argument("--audio-path", required=True)
    parser.add_argument("--transcript-json", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load_transcript(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid transcript JSON: {path}: {exc}") from exc

    if payload.get("error"):
        error = payload["error"]
        if isinstance(error, dict):
            error_type = error.get("type", "error")
            message = error.get("message", "transcription failed")
            raise SystemExit(f"Transcript JSON contains ASR error: {error_type}: {message}")
        raise SystemExit(f"Transcript JSON contains ASR error: {error}")

    required = ["engine", "locale", "full_text", "segments", "timing_complete"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise SystemExit(f"Transcript JSON is missing required keys: {', '.join(missing)}")
    if not isinstance(payload["segments"], list):
        raise SystemExit("Transcript JSON field 'segments' must be a list.")
    return payload


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def transcript_from_payload(payload: dict[str, Any]) -> str:
    full_text = clean_text(str(payload.get("full_text", "")))
    if full_text:
        return full_text

    parts: list[str] = []
    for segment in payload.get("segments", []):
        if isinstance(segment, dict):
            text = clean_text(str(segment.get("text", "")))
            if text:
                parts.append(text)
    return "\n".join(parts).strip() or "_No transcript text was generated._"


def render(args: argparse.Namespace, payload: dict[str, Any]) -> str:
    audio_path = Path(args.audio_path)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    transcript = transcript_from_payload(payload)
    timing_note = "yes" if payload.get("timing_complete") else "partial or unavailable"

    return "\n".join(
        [
            f"# {args.title}",
            "",
            "## Source",
            "",
            f"- Audio: `{audio_path.name}`",
            f"- Language: {args.language}",
            f"- Locale: `{payload.get('locale')}`",
            f"- ASR engine: `{payload.get('engine')}`",
            f"- Timing complete: {timing_note}",
            f"- Generated at: {generated_at}",
            "",
            "## Transcript",
            "",
            transcript,
            "",
        ]
    )


def main() -> None:
    args = parse_args()
    payload = load_transcript(Path(args.transcript_json))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(args, payload), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
