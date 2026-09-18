#!/bin/bash
# Запуск Google Chrome с отдельным профилем для Job Hunter и открытым CDP портом 9222.
# Твои логины на HH, Habr, LinkedIn сохраняются в ~/.jobhunter-chrome навсегда.

CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA_DIR="$HOME/.jobhunter-chrome"
CDP_PORT=9222

if curl -s "http://127.0.0.1:${CDP_PORT}/json/version" > /dev/null 2>&1; then
    echo "✅ Chrome уже запущен с CDP на порту ${CDP_PORT}."
    exit 0
fi

echo "🚀 Запуск Google Chrome для агента (профиль: ${USER_DATA_DIR}, порт: ${CDP_PORT})..."
mkdir -p "${USER_DATA_DIR}"

nohup "${CHROME_BIN}" \
    --remote-debugging-port="${CDP_PORT}" \
    --user-data-dir="${USER_DATA_DIR}" \
    --no-first-run \
    --no-default-browser-check \
    > /dev/null 2>&1 &

# Ожидание готовности порта
for i in {1..20}; do
    if curl -s "http://127.0.0.1:${CDP_PORT}/json/version" > /dev/null 2>&1; then
        echo "✅ Chrome готов к работе с AI-агентом на порту ${CDP_PORT}."
        exit 0
    fi
    sleep 0.3
done

echo "⚠️ Предупреждение: Chrome запущен, но порт 9222 пока не ответил."
