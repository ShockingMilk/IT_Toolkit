#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
export IT_TOOLKIT_LAUNCHER_SHELL="${SHELL##*/}"

echo
echo "=========================================="
echo "              IT TOOLKIT"
echo "=========================================="
echo

PYTHON_CMD=""

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python)"
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python was not detected."
    echo "Python 3.10 or newer is required."

    exit 1
fi

"$PYTHON_CMD" -c \
    "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"

if [ $? -ne 0 ]; then
    echo "ERROR: Python 3.10 or newer is required."
    exit 1
fi

echo "Python detected:"
"$PYTHON_CMD" --version

echo 
"$PYTHON_CMD" -m it_toolkit.main

exit $?