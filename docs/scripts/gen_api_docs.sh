#!/usr/bin/env bash
set -euo pipefail

rm -rf docs/reference
mkdir -p docs/reference

# Generate markdown docs using our custom script
python docs/scripts/generate_docs.py