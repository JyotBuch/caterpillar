#!/bin/bash
set -e

# Copy .env.example to .env if not present
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env — add your GROQ_API_KEY before running."
  exit 1
fi

# Install deps
pip install -r requirements.txt -q

# Start server
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
