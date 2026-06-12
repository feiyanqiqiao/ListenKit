#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any


TIMING_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}(?::\d{2})?[.,]\d{3})\s+-->\s+"
    r"(?P<end>\d{2}:\d{2}(?::\d{2})?[.,]\d{3})"
)
TAG_RE = re.compile(r"<[^>]+>")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a WebVTT subtitle file to ListenKit transcript JSON.")
    parser.add_argument("--vtt", required=True)
    parser.add_argument("--locale", required=True)
    parser.add_argument("--subtitle-kind", required=True, choices=["manual", "auto"])
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def parse_timestamp(value: str) -> float:
    value = value.replace(",", ".")
    parts = value.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        hours = "0"
    else:
        hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def clean_text(lines: list[str]) -> str:
    text = " ".join(line.strip() for line in lines if line.strip())
    text = TAG_RE.sub("", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_vtt(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    segments: list[dict[str, Any]] = []
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        timing = TIMING_RE.search(line)
        if not timing:
            index += 1
            continue

        start = parse_timestamp(timing.group("start"))
        end = parse_timestamp(timing.group("end"))
        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index])
            index += 1
        text = clean_text(text_lines)
        if text:
            segments.append({"start": start, "end": end, "text": text})
        index += 1

    return segments


def main() -> int:
    args = parse_args()
    segments = parse_vtt(Path(args.vtt))
    if not segments:
        raise SystemExit(f"No usable subtitle cues found in: {args.vtt}")

    payload = {
        "schema_version": 1,
        "engine": "yt-dlp-subtitles",
        "locale": args.locale,
        "subtitle_kind": args.subtitle_kind,
        "full_text": "\n".join(segment["text"] for segment in segments),
        "segments": segments,
        "timing_complete": True,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
