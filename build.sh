#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT_DIR"

export FORTYFOUR_VERSION="${FORTYFOUR_VERSION:-$(date +%Y.%m.%d)}"

python3 - <<'PY'
from pathlib import Path
import subprocess
import sys

requirements_path = Path.cwd() / "requirements.txt"

freeze_output = subprocess.run(
    [sys.executable, "-m", "pip", "freeze"],
    check=True,
    capture_output=True,
    text=True,
).stdout.splitlines()

installed_versions = {}
for line in freeze_output:
    if "==" not in line:
        continue
    package_name, version = line.split("==", 1)
    installed_versions[package_name.lower().replace("-", "_")] = version

updated_lines = []
for raw_line in requirements_path.read_text().splitlines():
    stripped_line = raw_line.strip()
    if not stripped_line or stripped_line.startswith("#") or "==" not in stripped_line:
        updated_lines.append(raw_line)
        continue

    package_name, _ = stripped_line.split("==", 1)
    normalized_name = package_name.lower().replace("-", "_")
    version = installed_versions.get(normalized_name)
    if version is None:
        raise SystemExit(f"Unable to freeze requirement for {package_name}")

    updated_lines.append(f"{package_name}=={version}")

requirements_path.write_text("\n".join(updated_lines) + "\n")
PY

rm -rf build dist

if ! python3 -m build --version >/dev/null 2>&1; then
    python3 -m pip install --quiet --upgrade build
fi

python3 -m build