#!/usr/bin/env bash
# Rebuild dist/brand-pack.zip the way claude.ai expects it:
# the brand-pack/ folder at the zip root, no __pycache__ or .DS_Store, no "@" or spaces in any path.
set -euo pipefail
cd "$(dirname "$0")/.."
desc=$(grep -m1 '^description:' brand-pack/SKILL.md | sed 's/^description: *//')
if [ "${#desc}" -gt 200 ]; then echo "SKILL.md description is ${#desc} chars; claude.ai allows 200." >&2; exit 1; fi
bad=$(find brand-pack -type f | grep -E '[^A-Za-z0-9._/-]' || true)
if [ -n "$bad" ]; then echo "Paths with characters claude.ai rejects:" >&2; echo "$bad" >&2; exit 1; fi
mkdir -p dist && rm -f dist/brand-pack.zip
zip -qr dist/brand-pack.zip brand-pack -x "*.DS_Store" "*__pycache__*"
unzip -l dist/brand-pack.zip | tail -1
echo "wrote dist/brand-pack.zip"
