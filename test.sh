#!/usr/bin/env bash
set -e

MODE="$1"

if [[ "$MODE" != "base" && "$MODE" != "new" ]]; then
  echo "Usage: $0 [base|new]"
  exit 2
fi

echo "Running tests in '$MODE' mode"
echo

echo "Astroid version:"
python - << 'EOF'
from astroid import __pkginfo__
print(__pkginfo__.version)
EOF
echo

# Run ONLY the relevant test file
pytest -q tests/test_builder.py