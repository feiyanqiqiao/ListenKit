#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  cli/transcribe-audio.sh --audio-path <path> --locale <bcp47> [--engine faster-whisper|apple] [--output <json>]

Options:
  --audio-path <path>      Local audio file to transcribe
  --locale <bcp47>         Speech locale, for example ja-JP or en-US
  --engine <name>          ASR backend. Defaults to faster-whisper
  --output <json>          Optional output JSON path
  --help                   Show this help
EOF
}

audio_path=""
locale=""
engine="faster-whisper"
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

if [[ "$engine" != "faster-whisper" && "$engine" != "apple" ]]; then
  echo "Unsupported engine: $engine" >&2
  echo "Supported engines: faster-whisper, apple." >&2
  exit 1
fi

if [[ ! -f "$audio_path" ]]; then
  echo "Audio file not found: $audio_path" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

reject_error_payload() {
  local payload_path="$1"
  if grep -Eq '^[[:space:]]*\{[[:space:]]*"error"[[:space:]]*:' "$payload_path"; then
    echo "ASR backend returned error payload." >&2
    cat "$payload_path" >&2
    return 1
  fi
  return 0
}

run_and_write() {
  if [[ -n "$output_path" ]]; then
    mkdir -p "$(dirname "$output_path")"
    local temp_output
    temp_output="$(mktemp)"
    if "$@" > "$temp_output"; then
      if ! reject_error_payload "$temp_output"; then
        rm -f "$temp_output"
        return 1
      fi
      mv "$temp_output" "$output_path"
      printf '%s\n' "$output_path"
    else
      local status=$?
      rm -f "$temp_output"
      return "$status"
    fi
  else
    local temp_output
    temp_output="$(mktemp)"
    if "$@" > "$temp_output"; then
      if ! reject_error_payload "$temp_output"; then
        rm -f "$temp_output"
        return 1
      fi
      cat "$temp_output"
      rm -f "$temp_output"
    else
      local status=$?
      rm -f "$temp_output"
      return "$status"
    fi
  fi
}

if [[ "$engine" == "apple" ]]; then
  helper="${APPLE_SPEECH_HELPER:-$repo_root/tools/apple-speech-helper/run-apple-speech-helper.sh}"

  if [[ ! -x "$helper" ]]; then
    cat >&2 <<EOF
Apple Speech helper is not installed at:
  $helper

Add or symlink a helper that accepts:
  --audio-path <path> --locale <bcp47>
and prints transcript JSON with engine, locale, full_text, segments, and timing_complete.
EOF
    exit 1
  fi

  run_and_write "$helper" --audio-path "$audio_path" --locale "$locale"
  exit $?
fi

helper="${LISTENKIT_FASTER_WHISPER_HELPER:-$repo_root/tools/faster-whisper/transcribe.py}"
python_executable="${FASTER_WHISPER_PYTHON:-}"

if [[ -z "$python_executable" ]]; then
  cat >&2 <<EOF
FASTER_WHISPER_PYTHON is required for the faster-whisper backend.

Create a Python environment with faster-whisper installed, then run:
  FASTER_WHISPER_PYTHON=/path/to/venv/bin/python cli/transcribe-audio.sh --audio-path <path> --locale <bcp47>

Use --engine apple to force the Apple Speech backend instead.
EOF
  exit 1
fi

if [[ ! -x "$python_executable" ]]; then
  echo "FASTER_WHISPER_PYTHON is not executable: $python_executable" >&2
  exit 1
fi

if [[ ! -f "$helper" ]]; then
  echo "faster-whisper helper is not installed at: $helper" >&2
  exit 1
fi

run_and_write "$python_executable" "$helper" "$audio_path" \
  --locale "$locale" \
  --model small \
  --compute-type int8 \
  --beam-size 5
