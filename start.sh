#!/bin/bash
cd "$(dirname "$0")"

# 1. Запуск Chrome с открытым портом CDP 9222 (если не запущен)
if [ -f "./launch_chrome.sh" ]; then
    ./launch_chrome.sh
fi

# 2. Запуск браузерного авто-отклика
PYTHON_BIN="python3"
if [ -d ".venv/bin" ] && [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
fi

echo "🚀 Запуск Browser Auto-Applier (CDP)..."
exec "$PYTHON_BIN" browser_applier.py "$@"
