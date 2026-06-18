#!/bin/zsh
set -e

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found."
  echo "Install Python 3 from https://www.python.org/downloads/ or with Homebrew."
  read -r "?Press Enter to close..."
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "No .env file found."
  echo "Creating .env from .env.example..."
  cp .env.example .env
  echo ""
  echo "Open .env and replace your_api_key_here with your OpenAI API key."
  echo "Then run this file again."
  open -e .env
  read -r "?Press Enter to close..."
  exit 0
fi

echo "Starting PolarAs..."
echo "Open http://127.0.0.1:8001 in your browser."
echo "Press Control + C in this window to stop the server."
echo ""

python3 app.py
