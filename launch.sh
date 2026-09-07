#!/bin/bash
# YouTube Agent Engine Launcher
# Run this to start the web UI. Add to your applications menu for easy access.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "WARNING: .env file not found!"
    echo "Please create a .env file with your GEMINI_API_KEY:"
    echo ""
    echo "  GEMINI_API_KEY=your_key_here"
    echo ""
    echo "Or run with --demo mode (no API key needed):"
    echo ""
fi

# Start the app
echo "Starting YouTube Agent Engine..."
echo ""
python app.py "$@"
