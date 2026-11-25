#!/usr/bin/env bash
cd "$(dirname "$0")"
echo "Starting Producer Reborn Studio GUI..."
if [ -f ".venv/bin/python" ]; then
    ".venv/bin/python" ".agents/plugins/producer-reborn/studio_gui.py"
else
    python3 ".agents/plugins/producer-reborn/studio_gui.py"
fi
