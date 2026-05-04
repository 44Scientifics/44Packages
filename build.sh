#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT_DIR"

export FORTYFOUR_VERSION="${FORTYFOUR_VERSION:-$(date +%Y.%m.%d)}"

# On utilise uv pour la gestion du lockfile si nécessaire
uv lock

rm -rf build dist

# On utilise uv build pour construire le package
uv build
