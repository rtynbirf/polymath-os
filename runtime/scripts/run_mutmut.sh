#!/bin/bash
# Wrapper for mutmut that pre-creates needed subdirs (mutmut 3.x bug:
# shutil.copy2 fails if destination directory doesn't exist).
set -euo pipefail
cd "$(dirname "$0")/.."  # runtime/

# Pre-create mutants/ subdirectories that also_copy will target
mkdir -p mutants/schemas mutants/tests mutants/experiments mutants/prototype mutants/docs

# Run mutmut
exec mutmut run "$@"
