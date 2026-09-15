#!/usr/bin/env bash
set -euo pipefail

target="${1:?target path is required}"
backup="${2:-${target}.bak}"

if [[ ! -f "$backup" ]]; then
  echo "backup not found: $backup" >&2
  exit 2
fi

cp -- "$backup" "$target"
echo "restored $target from $backup"