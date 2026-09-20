#!/bin/bash
cd "$(dirname "$0")"

# 0. Автоматическая подготовка виртуального окружения при первом запуске
if [ ! -d ".venv" ]; then
    echo "📦 Виртуальное окружение .venv не найдено. Создание и установка зависимостей..."
    PYTHON_CMD=""
    for cmd in python3 python; do
        if command -v "$cmd" > /dev/null 2>&1; then
            PYTHON_CMD="$cmd"
            break
        fi
    done
    if [ -z "$PYTHON_CMD" ]; then
        echo "❌ Ошибка: Python 3 не найден в системе. Установите python3."
        exit 1
    fi
    "$PYTHON_CMD" -m venv .venv
    .venv/bin/pip install --upgrade pip
    if [ -f "requirements.txt" ]; then
        .venv/bin/pip install -r requirements.txt
    fi
fi

# 1. Автоматический запуск Chrome с CDP портом 9222 (если еще не запущен)
if [ -f "./launch_chrome.sh" ]; then
    ./launch_chrome.sh
fi

echo "⚡ Stopping previous CRM instances..."
pkill -f "crm.py" 2>/dev/null || true
sleep 0.5

echo "⚡ Starting Job Hunter CRM..."
exec .venv/bin/python crm.py
