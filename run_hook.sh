#!/bin/bash
# Mini Claude Hook launcher
# This wrapper handles paths with spaces for the enforcement hooks

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/venv/bin/python" -m mini_claude.hooks.remind "$@"
