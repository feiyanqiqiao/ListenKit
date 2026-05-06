#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  cli/init-faster-whisper.sh

Create or reuse ListenKit's repo-local .venv, install faster-whisper,
verify that it can be imported, and print the Python executable path.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
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

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
venv_dir="$repo_root/.venv"
python_executable="$venv_dir/bin/python"

if [[ ! -x "$python_executable" ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required to create ListenKit's faster-whisper environment." >&2
    exit 1
  fi
  python3 -m venv "$venv_dir"
fi

"$python_executable" -m pip install --upgrade pip >&2
"$python_executable" -m pip install faster-whisper >&2

if ! "$python_executable" -c 'import faster_whisper' >/dev/null 2>&1; then
  echo "Installed faster-whisper, but it cannot be imported from: $python_executable" >&2
  exit 1
fi

printf '%s\n' "$python_executable"
