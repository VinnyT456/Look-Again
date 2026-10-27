#!/usr/bin/env bash
# Run from repo root: ./export_and_copy_mobile.sh [run_name]
exec "$(cd "$(dirname "$0")" && pwd)/ml/scripts/export_and_copy_mobile.sh" "$@"
