#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  cli/import-audio.sh --url <url> --output-dir <dir> [options]
  cli/import-audio.sh --input <path> --output-dir <dir> [options]

Options:
  --url <url>                    yt-dlp-supported video or audio URL
  --input <path>                 Existing local audio file, including Audio Hijack output
  --output-dir <dir>             Destination directory
  --base-name <name>             Output base name without extension
  --format <mp3|m4a|wav>         Output format (default: m4a)
  --playlist                     Download a full playlist instead of one item
  --help                         Show this help

The default URL behavior is single-item mode via yt-dlp --no-playlist.
EOF
}

url=""
input_path=""
output_dir=""
base_name=""
audio_format="m4a"
playlist_mode="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      [[ $# -ge 2 ]] || { echo "Missing value for --url" >&2; exit 1; }
      url="$2"
      shift 2
      ;;
    --input)
      [[ $# -ge 2 ]] || { echo "Missing value for --input" >&2; exit 1; }
      input_path="$2"
      shift 2
      ;;
    --output-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for --output-dir" >&2; exit 1; }
      output_dir="$2"
      shift 2
      ;;
    --base-name)
      [[ $# -ge 2 ]] || { echo "Missing value for --base-name" >&2; exit 1; }
      base_name="$2"
      shift 2
      ;;
    --format)
      [[ $# -ge 2 ]] || { echo "Missing value for --format" >&2; exit 1; }
      audio_format="$2"
      shift 2
      ;;
    --playlist)
      playlist_mode="true"
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

if [[ -n "$url" && -n "$input_path" ]]; then
  echo "Use either --url or --input, not both." >&2
  exit 1
fi

if [[ -z "$url" && -z "$input_path" ]]; then
  echo "One of --url or --input is required." >&2
  usage >&2
  exit 1
fi

if [[ -z "$output_dir" ]]; then
  echo "--output-dir is required." >&2
  exit 1
fi

case "$audio_format" in
  mp3|m4a|wav) ;;
  *)
    echo "--format must be one of: mp3, m4a, wav" >&2
    exit 1
    ;;
esac

mkdir -p "$output_dir"

if [[ -n "$input_path" ]]; then
  if [[ ! -f "$input_path" ]]; then
    echo "Input audio file not found: $input_path" >&2
    exit 1
  fi
  if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Missing required command: ffmpeg" >&2
    echo "Install it first, for example: brew install ffmpeg" >&2
    exit 1
  fi

  if [[ -z "$base_name" ]]; then
    base_name="$(basename "$input_path")"
    base_name="${base_name%.*}"
  fi

  output_path="${output_dir%/}/${base_name}.${audio_format}"
  input_abs="$(cd "$(dirname "$input_path")" && pwd -P)/$(basename "$input_path")"
  output_abs="$(cd "$(dirname "$output_path")" && pwd -P)/$(basename "$output_path")"
  if [[ "$input_abs" == "$output_abs" ]]; then
    printf '%s\n' "$output_path"
    exit 0
  fi

  ffmpeg_log="$(mktemp)"
  if ! ffmpeg -y -i "$input_path" -vn "$output_path" >/dev/null 2>"$ffmpeg_log"; then
    cat "$ffmpeg_log" >&2
    rm -f "$ffmpeg_log"
    exit 1
  fi
  rm -f "$ffmpeg_log"
  printf '%s\n' "$output_path"
  exit 0
fi

missing=()
for dependency in yt-dlp ffmpeg; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    missing+=("$dependency")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "Missing required commands: ${missing[*]}" >&2
  echo "Install them first, for example: brew install yt-dlp ffmpeg" >&2
  exit 1
fi

template="%(title)s.%(ext)s"
if [[ -n "$base_name" ]]; then
  template="${base_name}.%(ext)s"
fi

command=(
  yt-dlp
  --extract-audio
  --audio-format "$audio_format"
  --audio-quality 0
  --add-metadata
  --embed-metadata
  --no-mtime
  --paths "$output_dir"
  --output "$template"
)

if [[ "$playlist_mode" == "true" ]]; then
  command+=(--yes-playlist)
else
  command+=(--no-playlist)
fi

command+=("$url")
"${command[@]}"
