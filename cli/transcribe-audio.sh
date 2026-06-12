#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  cli/transcribe-audio.sh --audio-path <path> --locale <bcp47> [--engine faster-whisper|apple] [--output <json>] [--auto-init]

Options:
  --audio-path <path>      Local audio file to transcribe
  --locale <bcp47>         Speech locale, for example ja-JP or en-US
  --engine <name>          ASR backend. Defaults to faster-whisper
  --output <json>          Optional output JSON path
  --auto-init              Allow ListenKit to create .venv and install faster-whisper when missing
  --help                   Show this help
EOF
}

audio_path=""
locale=""
engine="faster-whisper"
output_path=""
auto_init="false"

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
    --auto-init)
      auto_init="true"
      shift
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
  if awk '
    {
      gsub(/[[:space:]]/, "", $0)
      compact = compact $0
      if (length(compact) >= 9) {
        found = compact ~ /^\{"error":/
        exit
      }
    }
    END {
      exit found ? 0 : 1
    }
  ' "$payload_path"; then
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
repo_venv_python="${LISTENKIT_FASTER_WHISPER_VENV_PYTHON:-$repo_root/.venv/bin/python}"
init_script="${LISTENKIT_INIT_FASTER_WHISPER:-$repo_root/cli/init-faster-whisper.sh}"
faster_whisper_model="small"
import_timeout_seconds="${LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS:-60}"

if [[ ! "$import_timeout_seconds" =~ ^[1-9][0-9]*$ ]]; then
  echo "LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS must be a positive integer." >&2
  exit 1
fi

python_can_import_faster_whisper() {
  local candidate="$1"
  local pid elapsed=0
  [[ -x "$candidate" ]] || return 1
  "$candidate" -c 'import faster_whisper' >/dev/null 2>&1 &
  pid=$!
  while kill -0 "$pid" 2>/dev/null; do
    if (( elapsed >= import_timeout_seconds )); then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      return 124
    fi
    sleep 1
    ((elapsed += 1))
  done
  wait "$pid"
}

initialize_faster_whisper() {
  if [[ ! -x "$init_script" ]]; then
    echo "faster-whisper init script is not executable: $init_script" >&2
    return 1
  fi
  "$init_script"
}

hf_hub_cache_dir() {
  if [[ -n "${HF_HUB_CACHE:-}" ]]; then
    printf '%s\n' "$HF_HUB_CACHE"
  elif [[ -n "${HF_HOME:-}" ]]; then
    printf '%s\n' "${HF_HOME%/}/hub"
  else
    printf '%s\n' "$HOME/.cache/huggingface/hub"
  fi
}

faster_whisper_model_is_cached() {
  local model="$1"
  local model_root
  model_root="$(hf_hub_cache_dir)/models--Systran--faster-whisper-${model}/snapshots"
  [[ -d "$model_root" ]] || return 1
  find "$model_root" -mindepth 2 -maxdepth 2 -name model.bin -type f -print -quit | grep -q .
}

enable_offline_hf_if_cached() {
  if faster_whisper_model_is_cached "$faster_whisper_model"; then
    export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
    export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"
  fi
}

python_executable="${FASTER_WHISPER_PYTHON:-}"

if [[ -n "$python_executable" ]]; then
  if python_can_import_faster_whisper "$python_executable"; then
    :
  else
    import_status=$?
    if [[ "$import_status" -eq 124 ]]; then
      echo "FASTER_WHISPER_PYTHON import timed out after ${import_timeout_seconds} seconds: $python_executable" >&2
    else
      echo "FASTER_WHISPER_PYTHON cannot import faster_whisper: $python_executable" >&2
    fi
    exit 1
  fi
else
  if python_can_import_faster_whisper "$repo_venv_python"; then
    python_executable="$repo_venv_python"
  else
    import_status=$?
    if [[ "$import_status" -eq 124 ]]; then
      echo "ListenKit faster-whisper import timed out after ${import_timeout_seconds} seconds: $repo_venv_python" >&2
      exit 1
    fi
    if [[ "$auto_init" == "true" || "${LISTENKIT_AUTO_INIT:-}" == "1" ]]; then
      python_executable="$(initialize_faster_whisper)"
    elif [[ -t 0 ]]; then
      printf 'ListenKit needs faster-whisper installed in %s. Install now? [y/N] ' "$repo_root/.venv" >&2
      read -r answer
      case "$answer" in
        y|Y|yes|YES)
          python_executable="$(initialize_faster_whisper)"
          ;;
        *)
          cat >&2 <<EOF
faster-whisper initialization was not approved.

Run one of:
  cli/transcribe-audio.sh --audio-path <path> --locale <bcp47> --auto-init
  cli/init-faster-whisper.sh

Use --engine apple to force the Apple Speech backend instead.
EOF
          exit 1
          ;;
      esac
    else
      cat >&2 <<EOF
faster-whisper is not initialized for ListenKit.

Run one of:
  cli/transcribe-audio.sh --audio-path <path> --locale <bcp47> --auto-init
  LISTENKIT_AUTO_INIT=1 cli/transcribe-audio.sh --audio-path <path> --locale <bcp47>
  cli/init-faster-whisper.sh

Or set:
  FASTER_WHISPER_PYTHON=/path/to/python

Use --engine apple to force the Apple Speech backend instead.
EOF
      exit 1
    fi
  fi
fi

if python_can_import_faster_whisper "$python_executable"; then
  :
else
  import_status=$?
  if [[ "$import_status" -eq 124 ]]; then
    echo "faster-whisper import timed out after ${import_timeout_seconds} seconds: $python_executable" >&2
    exit 1
  fi
  cat >&2 <<EOF
faster-whisper is not importable from:
  $python_executable

Run:
  cli/init-faster-whisper.sh

Or set:
  FASTER_WHISPER_PYTHON=/path/to/python

Use --engine apple to force the Apple Speech backend instead.
EOF
  exit 1
fi

if [[ ! -f "$helper" ]]; then
  echo "faster-whisper helper is not installed at: $helper" >&2
  exit 1
fi

enable_offline_hf_if_cached

run_and_write "$python_executable" "$helper" "$audio_path" \
  --locale "$locale" \
  --model "$faster_whisper_model" \
  --compute-type int8 \
  --beam-size 5
