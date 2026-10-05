#!/usr/bin/env bash
set -e
if [ -z "${HF_TOKEN:-}" ]; then
  echo 'Set HF_TOKEN first: export HF_TOKEN="hf_..."'
  exit 1
fi
python -m pip install --disable-pip-version-check -r requirements.txt
python server.py
