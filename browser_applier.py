#!/usr/bin/env python3
"""
Browser Auto-Applier for Job Hunter.
Connects directly to your running Google Chrome via CDP (port 9222).
Automates vacancy search, cover letter generation via Local AI (LM Studio/Ollama/DeepSeek),
and safe, human-like clicking on HH.ru and Habr Career.
"""

import argparse
import json
import os
import random
import re
import sys
import time
from typing import Dict, Any, List, Optional

from agents.cdp_browser import CDPBrowserDriver
from agents.adapters.hh_adapter import HeadHunterCDPAdapter
from agents.adapters.habr_adapter import HabrCDPAdapter
from tracker.history import (
    is_already_processed,
    record_apply_attempt,
    get_daily_applied_count,
    get_recent_applies
)
from llm_helper import generate_cover_letter, get_llm_config


def load_config(path: str = "config.json") -> Dict[str, Any]:
    if not os.path.exists(path):
        example_path = "config.example.json"
        if os.path.exists(example_path):
            with open(example_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class BrowserApplier:
    def __init__(self, config: Dict[str, Any], dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.driver = CDPBrowserDriver.get_instance()
        self.hh_adapter = HeadHunterCDPAdapter(driver=self.driver)
        self.habr_adapter = HabrCDPAdapter(driver=self.driver)

    def connect_browser(self) -> bool:
        print("[1/3] 🔌 Проверка подключения к Google Chrome (порт 9222)...")
        if not self.driver.is_cdp_available():
            print("   Запуск Chrome с вашим профилем через ./launch_chrome.sh...")
            if not self.driver.launch_chrome_if_needed():
                print("❌ Не удалось запустить Chrome. Запустите вручную: ./launch_chrome.sh")
                return False

        if not self.driver.connect():
            print("❌ Ошибка подключения к Chrome через CDP.")
            return False

        print("✅ Успешно подключено к живому браузеру Chrome!")
        return True

    def run_hh(self, max_applies: int = 30):
        """Automates HH.ru vacancy search and responses in browser."""
        page = self.driver.get_active_page(avoid_crm=True)
        search_cfg = self.config.get("search", {})
        query = search_cfg.get("query", "Python")
        stop_words = [w.lower() for w in search_cfg.get("stop_words", [])]
        blacklist = [b.lower() for b in search_cfg.get("company_blacklist", [])]
        default_letter = self.config.get("cover_letter", {}).get("default_text", "")

        safety_cfg = self.config.get("safety", {})
        delay_min = safety_cfg.get("delay_min_seconds", 15)
        delay_max = safety_cfg.get("delay_max_seconds", 35)

        # Build HH search URL
        encoded_query = query.replace(" ", "+")
        search_url = f"https://hh.ru/search/vacancy?text={encoded_query}&search_field=name&order_by=publication_time"
        if search_cfg.get("schedule") == "remote":
            search_url += "&schedule=remote"

        print(f"\n🌐 Открываем поиск HH.ru: {search_url}")
        page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2500)

        # Check login
        if page.locator('[data-qa="account-login-input"], [data-qa="login-submit-form"]').count() > 0:
            print("⚠️ Вы не авторизованы на HH.ru! Пожалуйста, войдите в аккаунт в окне Chrome.")
            return

        applied_count = 0
        cards = page.locator('[data-qa="vacancy-serp__vacancy"]').all()
        print(f"📋 Найдено карточек вакансий на первой странице: {len(cards)}")

        for idx, card in enumerate(cards, 1):
            if applied_count >= max_applies:
                print(f"🛑 Достигнут лимит на сессию ({max_applies}). Остановка.")
                break

            try:
                # Extract vacancy info from card
                title_elem = card.locator('[data-qa="serp-item__title"]')
                if title_elem.count() == 0:
                    continue

                title = title_elem.first.inner_text().strip()
                href = title_elem.first.get_attribute("href") or ""
                vacancy_id_match = re.search(r'/vacancy/(\d+)', href)
                if not vacancy_id_match:
                    continue
                vac_id = vacancy_id_match.group(1)

                employer_elem = card.locator('[data-qa="vacancy-serp__vacancy-employer"]')
                company = employer_elem.first.inner_text().strip() if employer_elem.count() > 0 else "Компания на HH"

                # Check if already applied on site
                card_text = card.inner_text()
                if "Вы откликнулись" in card_text or card.locator('[data-qa="vacancy-response-link-view-topic"]').count() > 0:
                    continue

                # Check local DB
                if is_already_processed("hh", vac_id):
                    continue

                # Check blacklist
                if any(b in company.lower() for b in blacklist):
                    print(f"⏭ Пропуск (черный список): {company}")
                    continue

                # Check stop words
                if any(sw in title.lower() for sw in stop_words):
                    print(f"⏭ Пропуск (стоп-слово): {title}")
                    continue

                print("\n" + "=" * 60)
                print(f"🎯 [{applied_count + 1}/{max_applies}] Вакансия: {title} в {company}")
                print(f"   URL: https://hh.ru/vacancy/{vac_id}")

                # Generate cover letter via Local AI
                cover_letter = generate_cover_letter(
                    vacancy_title=title,
                    company=company,
                    description=title,
                    default_template=default_letter
                )
                if cover_letter:
                    print(f"   🤖 Письмо: {cover_letter[:120]}...")

                if self.dry_run:
                    print("   [DRY-RUN] Эмуляция: отклик не отправляется.")
                    applied_count += 1
                    continue

                # Use HH adapter to apply
                apply_url = f"https://hh.ru/vacancy/{vac_id}"
                res = self.hh_adapter.apply(
                    vacancy_url=apply_url,
                    cover_letter=cover_letter,
                    auto_submit=True
                )

                if res.get("success"):
                    applied_count += 1
                    record_apply_attempt("hh", vac_id, "applied", title, company, apply_url)
                    print(f"   ✅ Отклик успешно отправлен!")
                else:
                    err = res.get("error", "Неизвестная ошибка")
                    record_apply_attempt("hh", vac_id, "error", title, company, apply_url, message=err)
                    print(f"   ❌ Ошибка: {err}")

                # Human jitter delay
                delay = random.uniform(delay_min, delay_max)
                print(f"   ⏳ Пауза {delay:.1f} сек...")
                time.sleep(delay)

            except Exception as e:
                print(f"   ⚠️ Ошибка обработки карточки #{idx}: {e}")
                continue

        print(f"\n🏁 Сессия HH.ru завершена. Отправлено: {applied_count}")

    def run_habr(self, max_applies: int = 20):
        """Automates Habr Career vacancy search and responses in browser."""
        page = self.driver.get_active_page(avoid_crm=True)
        search_cfg = self.config.get("search", {})
        query = search_cfg.get("query", "Python")
        stop_words = [w.lower() for w in search_cfg.get("stop_words", [])]
        default_letter = self.config.get("cover_letter", {}).get("default_text", "")

        encoded_query = query.replace(" ", "+")
        search_url = f"https://career.habr.com/vacancies?q={encoded_query}&type=all&sort=date"

        print(f"\n🌐 Открываем поиск Хабр Карьеры: {search_url}")
        page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2500)

        applied_count = 0
        cards = page.locator('.vacancy-card').all()
        print(f"📋 Найдено карточек на Хабр Карьере: {len(cards)}")

        for idx, card in enumerate(cards, 1):
            if applied_count >= max_applies:
                break

            try:
                title_elem = card.locator('.vacancy-card__title a')
                if title_elem.count() == 0:
                    continue

                title = title_elem.first.inner_text().strip()
                href = title_elem.first.get_attribute("href") or ""
                full_url = f"https://career.habr.com{href}" if href.startswith("/") else href

                id_m = re.search(r'/vacancies/(\d+)', full_url)
                vac_id = id_m.group(1) if id_m else str(abs(hash(full_url)))

                company_elem = card.locator('.vacancy-card__company-title a')
                company = company_elem.first.inner_text().strip() if company_elem.count() > 0 else "Хабр Компания"

                # Check stop words
                if any(sw in title.lower() for sw in stop_words):
                    continue

                # Check if already applied
                if is_already_processed("habr", vac_id):
                    continue

                print("\n" + "=" * 60)
                print(f"🎯 [Хабр] {title} в {company}")
                print(f"   URL: {full_url}")

                cover_letter = generate_cover_letter(
                    vacancy_title=title,
                    company=company,
                    description=title,
                    default_template=default_letter
                )

                if self.dry_run:
                    print("   [DRY-RUN] Эмуляция.")
                    applied_count += 1
                    continue

                res = self.habr_adapter.apply(
                    vacancy_url=full_url,
                    cover_letter=cover_letter,
                    auto_submit=True
                )

                if res.get("success"):
                    applied_count += 1
                    record_apply_attempt("habr", vac_id, "applied", title, company, full_url)
                    print("   ✅ Отклик отправлен на Хабре!")
                else:
                    print(f"   ❌ {res.get('error')}")

                delay = random.uniform(15, 30)
                print(f"   ⏳ Пауза {delay:.1f} сек...")
                time.sleep(delay)

            except Exception as e:
                print(f"   ⚠️ Ошибка карточки #{idx}: {e}")
                continue

        print(f"\n🏁 Сессия Хабр Карьеры завершена. Отправлено: {applied_count}")


def main():
    parser = argparse.ArgumentParser(description="Авто-отклик через живой Chrome (CDP)")
    parser.add_argument("--platform", choices=["hh", "habr"], default="hh", help="Платформа (hh или habr)")
    parser.add_argument("--limit", type=int, default=30, help="Лимит откликов на этот запуск")
    parser.add_argument("--dry-run", action="store_true", help="Режим эмуляции без нажатия отправки")
    parser.add_argument("--local-ai", action="store_true", help="Использовать локальный LM Studio / Ollama")

    args = parser.parse_args()
    config = load_config("config.json")

    if args.local_ai:
        if "llm" not in config:
            config["llm"] = {}
        config["llm"]["enabled"] = True
        config["llm"]["provider"] = "lm_studio"
        config["llm"]["lm_studio_url"] = "http://127.0.0.1:1234/v1"

    applier = BrowserApplier(config, dry_run=args.dry_run)
    if not applier.connect_browser():
        sys.exit(1)

    if args.platform == "hh":
        applier.run_hh(max_applies=args.limit)
    elif args.platform == "habr":
        applier.run_habr(max_applies=args.limit)


if __name__ == "__main__":
    main()
