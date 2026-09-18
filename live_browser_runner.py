#!/usr/bin/env python3
"""
Live Browser Runner & Monitor for Job Hunter CDP Agent.
Connects directly to the user's running Google Chrome (port 9222),
attaches real-time console/network error listeners, executes the apply flow,
and saves review screenshots.
"""

import sys
import json
import time
from agents.cdp_browser import CDPBrowserDriver
from agents.cdp_logger import CDPLogger
from agents.adapters.habr_adapter import HabrCDPAdapter

def main():
    print("=" * 60)
    print("🚀 JOB HUNTER: Live CDP Browser Runner & Monitor")
    print("=" * 60)

    logger = CDPLogger.get_instance()
    logger.clear()
    driver = CDPBrowserDriver.get_instance()

    print("\n[1/5] 🔌 Подключение к Chrome на порту 9222...")
    if not driver.connect():
        print("❌ Ошибка: Не удалось подключиться к Chrome через CDP на порту 9222.")
        print("   Убедись, что запущен ./launch_chrome.sh")
        sys.exit(1)

    print("✅ Успешно подключено к Chrome DevTools Protocol!")

    # Find Habr tab or focus active
    habr_page = None
    if driver._context:
        for p in driver._context.pages:
            if "career.habr.com/vacancies" in p.url:
                habr_page = p
                break

    if not habr_page:
        habr_page = driver.get_active_page()

    habr_page.bring_to_front()
    logger.attach_to_page(habr_page)

    print(f"\n[2/5] 🌐 Активная вкладка:")
    print(f"   URL:   {habr_page.url}")
    print(f"   Title: {habr_page.title()}")

    # Real cover letter text tailored for this Frontend React vacancy
    sample_cover_letter = (
        "Здравствуйте!\n\n"
        "Меня заинтересовала вакансия Frontend-разработчика (React). "
        "Обладаю опытом коммерческой разработки высоконагруженных веб-сервисов на React, TypeScript и современными инструментами сборки. "
        "Умею проектировать масштабируемую архитектуру компонентов, писать чистый и тестируемый код, оптимизировать Core Web Vitals.\n\n"
        "С удовольствием детальнее расскажу о релевантных кейсах на техническом интервью.\n\n"
        "С уважением,\nЕгор Мышинский"
    )

    print("\n[3/5] 🤖 Запуск HabrCDPAdapter (наблюдай за окном Chrome!)...")
    adapter = HabrCDPAdapter(driver=driver, logger=logger)

    result = adapter.apply(
        vacancy_url=habr_page.url,
        cover_letter=sample_cover_letter,
        salary="250000",
        auto_submit=False  # Safety first: human checkpoint
    )

    print("\n[4/5] 📋 Результат работы агента:")
    print(f"   Success:        {result.get('success')}")
    print(f"   Stage:          {result.get('stage')}")
    print(f"   Platform:       {result.get('platform')}")
    print(f"   Approval Token: {result.get('approval_token')}")
    if result.get("cover_letter_preview"):
        print(f"   Letter Preview: {result.get('cover_letter_preview')}")
    if result.get("error"):
        print(f"   Error:          {result.get('error')}")

    # Save screenshot if present
    if result.get("screenshot_base64"):
        import base64
        img_data = base64.b64decode(result["screenshot_base64"])
        screenshot_path = "static/live_habr_filled.png"
        with open(screenshot_path, "wb") as f:
            f.write(img_data)
        print(f"📸 Скриншот формы сохранен в: {screenshot_path}")

    print("\n[5/5] 📊 Логи и мониторинг ошибок (Browser Console & Agent):")
    recent_logs = logger.get_recent_logs(limit=25)
    for entry in recent_logs:
        lvl = entry["level"]
        src = entry["source"]
        msg = entry["message"]
        color = "🔴" if lvl == "ERROR" else ("🟡" if lvl == "WARN" else "🟢")
        print(f"   {color} [{entry['timestamp']}] [{src}] {msg}")

    print("\n" + "=" * 60)
    print("✨ Выполнение завершено! Форма заполнена прямо в твоем Chrome.")
    print("=" * 60)

if __name__ == "__main__":
    main()
