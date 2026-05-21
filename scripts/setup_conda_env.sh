#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/environment.yml"
ENV_NAME="${1:-reasoningbank}"

if command -v mamba >/dev/null 2>&1; then
  CONDA_CMD="mamba"
elif command -v conda >/dev/null 2>&1; then
  CONDA_CMD="conda"
else
  echo "conda or mamba is required" >&2
  exit 1
fi

if "$CONDA_CMD" env list | awk '{print $1}' | grep -Fxq "$ENV_NAME"; then
  "$CONDA_CMD" env update --name "$ENV_NAME" --file "$ENV_FILE" --prune
else
  "$CONDA_CMD" env create --file "$ENV_FILE" --name "$ENV_NAME"
fi

echo "environment ready: $ENV_NAME"
echo "activate with: conda activate $ENV_NAME"
