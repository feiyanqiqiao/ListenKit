#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  cli/transcribe-audio.sh --audio-path <path> --locale <bcp47> [--engine apple] [--output <json>]

Options:
  --audio-path <path>      Local audio file to transcribe
  --locale <bcp47>         Speech locale, for example ja-JP or en-US
  --engine apple           Apple Speech backend (only backend implemented in v1)
  --output <json>          Optional output JSON path
  --help                   Show this help
EOF
}

audio_path=""
locale=""
engine="apple"
output_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --audio-path)
      [[ $# -ge 2 ]] || { echo "Missing value for --audio-path" >&2; exit 1; }
      audio_path="$2"
      shift 2
      ;;
    --locale)
      [[ $# -ge 2 ]] || { echo "Missing value for --locale" >&2; exit 1; }
      locale="$2"
      shift 2
      ;;
    --engine)
      [[ $# -ge 2 ]] || { echo "Missing value for --engine" >&2; exit 1; }
      engine="$2"
      shift 2
      ;;
    --output)
      [[ $# -ge 2 ]] || { echo "Missing value for --output" >&2; exit 1; }
      output_path="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$audio_path" || -z "$locale" ]]; then
  echo "--audio-path and --locale are required." >&2
  usage >&2
  exit 1
fi

if [[ "$engine" != "apple" ]]; then
  echo "Unsupported engine: $engine" >&2
  echo "v1 only implements --engine apple. See docs/backends.md for extension notes." >&2
  exit 1
fi

if [[ ! -f "$audio_path" ]]; then
  echo "Audio file not found: $audio_path" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
helper="${APPLE_SPEECH_HELPER:-$repo_root/tools/apple-speech-helper/run-apple-speech-helper.sh}"

if [[ ! -x "$helper" ]]; then
  cat >&2 <<EOF
Apple Speech helper is not installed at:
  $helper

This open-source scaffold keeps Apple Speech as the v1 backend contract.
Add or symlink a helper that accepts:
  --audio-path <path> --locale <bcp47>
and prints transcript JSON with engine, locale, full_text, segments, and timing_complete.
EOF
  exit 1
fi

if [[ -n "$output_path" ]]; then
  mkdir -p "$(dirname "$output_path")"
  "$helper" --audio-path "$audio_path" --locale "$locale" > "$output_path"
  printf '%s\n' "$output_path"
else
  "$helper" --audio-path "$audio_path" --locale "$locale"
fi
