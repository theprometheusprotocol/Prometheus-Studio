#!/usr/bin/env bash
set -euo pipefail

# Load .env if present
if [ -f ".env" ]; then
  set -a
  source .env
  set +a
fi

BRAND_LOWER=$(echo "${BRAND:-default}" | tr '[:upper:]' '[:lower:]')
THEME_SRC=".streamlit/brands/${BRAND_LOWER}.toml"
THEME_DST=".streamlit/config.toml"

mkdir -p .streamlit

if [ -f "$THEME_SRC" ]; then
  cp "$THEME_SRC" "$THEME_DST"
else
  echo "No theme for BRAND='${BRAND_LOWER}', falling back to default."
  cp ".streamlit/brands/default.toml" "$THEME_DST"
fi

# Activate venv if available (optional)
if [ -f "$HOME/.venvs/prometheus/bin/activate" ]; then
  source "$HOME/.venvs/prometheus/bin/activate"
fi

exec python -m streamlit run app/app.py

