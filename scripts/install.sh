#!/usr/bin/env bash
set -Eeuo pipefail

if [[ -L "${BASH_SOURCE[0]}" ]]; then
  echo "Refusing symlinked invocation; run the repository's scripts/install.sh directly." >&2
  exit 2
fi

script_dir="$(cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  python_command=(python3)
elif command -v python >/dev/null 2>&1; then
  python_command=(python)
else
  echo "Production Pit Crew for Codex requires Python 3.11 or newer." >&2
  exit 2
fi

exec "${python_command[@]}" "$script_dir/install_core.py" "$@"
