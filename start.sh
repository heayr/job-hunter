#!/bin/bash
cd "$(dirname "$0")"

# 1. Автоматический запуск Chrome с CDP портом 9222 (если еще не запущен)
if [ -f "./launch_chrome.sh" ]; then
    ./launch_chrome.sh
fi

echo "⚡ Stopping previous CRM instances..."
pkill -f "crm.py" 2>/dev/null || true
sleep 0.5

echo "⚡ Starting Job Hunter CRM..."
exec .venv/bin/python crm.py
