#!/usr/bin/env bash
# Build the static site and update the files published by GitHub Pages.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

exec npm run build -- --pages
