#!/usr/bin/env python3
import argparse
import json
import os
import random
import sys
import time
from typing import Dict, Any, Optional

from platforms.hh.auth import HHAuth
from platforms.hh.client import HHClient
from platforms.superjob.auth import SuperJobAuth
from platforms.superjob.client import SuperJobClient
from tracker.history import (
    is_already_processed,
    record_apply_attempt,
    get_daily_applied_count,
    get_recent_applies
)
from llm_helper import generate_cover_letter


def load_config(path: str = "config.json") -> Dict[str, Any]:
    if not os.path.exists(path):
        example_path = "config.example.json"
        if os.path.exists(example_path):
            print(f"[!] Конфиг {path} не найден. Используется шаблон из {example_path}")
            with open(example_path, "r", encoding="utf-8") as f:
                return json.load(f)
        print(f"[!] Ошибка: создайте {path} перед запуском.")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_platform_adapter(platform_name: str, config: Dict[str, Any]):
    if platform_name == "hh":
        hh_cfg = config.get("hh", {})
        client_id = hh_cfg.get("client_id", "")
        client_secret = hh_cfg.get("client_secret", "")
        redirect_uri = hh_cfg.get("redirect_uri", "https://httpbin.org/get")
        user_agent_email = hh_cfg.get("user_agent_email", "applicant@example.com")
        auth = HHAuth(client_id, client_secret, redirect_uri)
        client = HHClient(auth, user_agent_email=user_agent_email)
        return auth, client
    elif platform_name == "superjob":
        sj_cfg = config.get("superjob", {})
        client_id = sj_cfg.get("client_id", "")
        client_secret = sj_cfg.get("client_secret", "")
        redirect_uri = sj_cfg.get("redirect_uri", "https://httpbin.org/get")
        auth = SuperJobAuth(client_id, client_secret, redirect_uri)
        client = SuperJobClient(auth)
        return auth, client
    else:
        raise ValueError(f"Неизвестная платформа: {platform_name}")


def handle_auth(auth, code: Optional[str] = None):
    """Interactive OAuth code exchange."""
    url = auth.get_authorization_url()
    print("\n" + "=" * 60)
    print("🔐 АВТОРИЗАЦИЯ")
    print("=" * 60)
    print("1. Откройте эту ссылку в вашем браузере:")
    print(f"\n   {url}\n")
    print("2. Войдите в свой аккаунт и нажмите 'Разрешить доступ'.")
    print("3. Браузер перенаправит вас на страницу вида: https://httpbin.org/get?code=ВАШ_КОД")
    print("=" * 60)

    if not code:
        try:
            code = input("\nВставьте полученный код (параметр 'code' из ссылки): ").strip()
        except EOFError:
            print("[!] Ввод завершен.")
            return

    if not code:
        print("[!] Код не был передан. Авторизация отменена.")
        return

    print("🔄 Обмениваем код на токен доступа...")
    try:
        tokens = auth.exchange_code_for_token(code)
        print("✅ Успешно! Токен получен и сохранен в локальный файл.")
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")


def handle_list_resumes(client, platform_name: str):
    """Lists resumes available on platform."""
    print(f"\n📋 Загружаем список ваших резюме на {platform_name.upper()}...")
    try:
        resumes = client.get_resumes()
        if not resumes:
            print("ℹ Резюме на аккаунте не найдены.")
            return

        print(f"\nНайдено резюме: {len(resumes)}")
        for idx, r in enumerate(resumes, 1):
            print(f" {idx}. ID: {r['id']}")
            print(f"    Название: {r['title']}")
            print(f"    Статус:   {r.get('status', 'не указан')}")
            if r.get('url'):
                print(f"    Ссылка:   {r['url']}")
            print("-" * 40)
    except Exception as e:
        print(f"❌ Ошибка при получении резюме: {e}")


def handle_search(client, config: Dict[str, Any]):
    """Searches vacancies and displays previews."""
    search_cfg = config.get("search", {})
    query = search_cfg.get("query", "Python")
    print(f"\n🔎 Поиск вакансий по запросу: '{query}'...")

    try:
        vacancies = client.search_vacancies(
            query=query,
            experience=search_cfg.get("experience"),
            schedule=search_cfg.get("schedule"),
            salary=search_cfg.get("salary"),
            only_with_salary=search_cfg.get("only_with_salary", False),
            period=search_cfg.get("period_days", 7)
        )
        print(f"✅ Найдено вакансий: {len(vacancies)}\n")
        for idx, v in enumerate(vacancies[:15], 1):
            remote_tag = " [Удаленка]" if v.is_remote else ""
            test_tag = " [⚠️ Тест]" if v.has_test else ""
            print(f"{idx}. {v.title} — {v.company}{remote_tag}{test_tag}")
            print(f"   Зарплата: {v.salary} | Город: {v.location}")
            print(f"   Ссылка:   {v.url}")
            print("-" * 50)
    except Exception as e:
        print(f"❌ Ошибка при поиске: {e}")


def handle_apply(client, platform_name: str, config: Dict[str, Any], dry_run: bool = False):
    """Executes safe auto-apply flow."""
    safety_cfg = config.get("safety", {})
    max_daily = safety_cfg.get("max_daily_applies", 50)
    delay_min = safety_cfg.get("delay_min_seconds", 15)
    delay_max = safety_cfg.get("delay_max_seconds", 35)
    skip_tests = safety_cfg.get("skip_tests", True)

    today_applied = get_daily_applied_count(platform_name)
    print(f"\n📊 Статистика за сегодня ({platform_name}): {today_applied} из {max_daily} откликов.")
    if today_applied >= max_daily:
        print(f"🛑 Достигнут суточный лимит безопасных откликов ({max_daily}). До завтра!")
        return

    # Determine target resume
    resumes = client.get_resumes()
    if not resumes:
        print("❌ Не найдено ни одного резюме на аккаунте!")
        return

    target_title = config.get(platform_name, {}).get("resume_title", "").strip().lower()
    selected_resume = None

    if target_title:
        for r in resumes:
            if target_title in r["title"].lower():
                selected_resume = r
                break

    if not selected_resume:
        selected_resume = resumes[0]
        print(f"ℹ Используем первое доступное резюме: '{selected_resume['title']}' (ID: {selected_resume['id']})")
    else:
        print(f"🎯 Выбрано резюме: '{selected_resume['title']}' (ID: {selected_resume['id']})")

    # Search for vacancies
    search_cfg = config.get("search", {})
    stop_words = [w.lower() for w in search_cfg.get("stop_words", [])]
    blacklist = [b.lower() for b in search_cfg.get("company_blacklist", [])]

    print(f"\n🔎 Загружаем свежие вакансии по запросу: '{search_cfg.get('query', '')}'...")
    vacancies = client.search_vacancies(
        query=search_cfg.get("query", "Python"),
        experience=search_cfg.get("experience"),
        schedule=search_cfg.get("schedule"),
        salary=search_cfg.get("salary"),
        only_with_salary=search_cfg.get("only_with_salary", False),
        period=search_cfg.get("period_days", 7)
    )

    default_letter = config.get("cover_letter", {}).get("default_text", "")
    applied_in_session = 0

    print(f"🚀 Найдено {len(vacancies)} вакансий. Начинаем обработку...\n")

    for v in vacancies:
        if today_applied + applied_in_session >= max_daily:
            print(f"\n🛑 Достигнут суточный лимит ({max_daily} откликов). Сессия завершена.")
            break

        # Check local DB cache
        if is_already_processed(platform_name, v.id):
            continue

        # Check blacklist
        if any(b in v.company.lower() for b in blacklist):
            print(f"⏭ Пропуск (компания в черном списке): {v.company}")
            record_apply_attempt(platform_name, v.id, "skipped_blacklist", v.title, v.company, v.url)
            continue

        # Check stop words in title
        title_lower = v.title.lower()
        if any(sw in title_lower for sw in stop_words):
            print(f"⏭ Пропуск (стоп-слово в названии): {v.title}")
            record_apply_attempt(platform_name, v.id, "skipped_stopword", v.title, v.company, v.url)
            continue

        # Check tests/quizzes
        if v.has_test and skip_tests:
            print(f"⏭ Пропуск (требуется тест работодателя): {v.title} в {v.company}")
            record_apply_attempt(platform_name, v.id, "skipped_test", v.title, v.company, v.url)
            continue

        # Prepare cover letter
        cover_letter = generate_cover_letter(
            vacancy_title=v.title,
            company=v.company,
            description=v.description,
            user_skills=", ".join(selected_resume.get("skills", [])),
            default_template=default_letter
        )

        print("=" * 60)
        print(f"📌 Кандидат на отклик: {v.title} в {v.company}")
        print(f"   Ссылка: {v.url}")
        print(f"   Зарплата: {v.salary}")
        if cover_letter:
            print(f"   Письмо: {cover_letter[:120]}...")

        if dry_run:
            print("   [DRY-RUN] Отклик НЕ отправлен (тестовый режим).")
            continue

        # Send application
        result = client.apply(
            vacancy_id=v.id,
            resume_id=selected_resume["id"],
            message=cover_letter
        )

        record_apply_attempt(
            platform=platform_name,
            vacancy_id=v.id,
            status=result.status,
            title=v.title,
            company=v.company,
            url=v.url,
            resume_id=selected_resume["id"],
            message=result.message
        )

        if result.success:
            applied_in_session += 1
            print(f"   ✅ {result.message}! (Всего за сегодня: {today_applied + applied_in_session})")
        elif result.status == "limit_exceeded":
            print(f"   🛑 {result.message}. Останавливаем работу.")
            break
        elif result.status == "already_applied":
            print(f"   ℹ {result.message}.")
        else:
            print(f"   ❌ {result.message}")

        # Human-like delay
        delay = random.uniform(delay_min, delay_max)
        print(f"   ⏳ Пауза перед следующим откликом: {delay:.1f} сек...")
        time.sleep(delay)

    print(f"\n🏁 Завершено. Отправлено откликов за сессию: {applied_in_session}")


def handle_stats():
    """Prints recent application stats."""
    applies = get_recent_applies(limit=30)
    print("\n" + "=" * 60)
    print("📈 ПОСЛЕДНИЕ СОБЫТИЯ ОТКЛИКОВ")
    print("=" * 60)
    if not applies:
        print("История откликов пуста.")
        return

    for a in applies:
        status_icon = "✅" if a["status"] == "applied" else "⏭" if "skip" in a["status"] else "❌"
        print(f"{status_icon} [{a['platform'].upper()}] {a['applied_date']} | {a['title']} ({a['company']})")
        print(f"   Статус: {a['status']} | {a['url']}")


def main():
    parser = argparse.ArgumentParser(description="Автоматический отклик на HeadHunter и SuperJob через официальный API")
    parser.add_argument("--platform", choices=["hh", "superjob"], default="hh", help="Платформа (по умолчанию: hh)")
    parser.add_argument("--config", default="config.json", help="Путь к файлу конфигурации")
    parser.add_argument("--auth", action="store_true", help="Запустить авторизацию аккаунта (OAuth 2.0)")
    parser.add_argument("--code", type=str, help="Код авторизации (если получен заранее)")
    parser.add_argument("--resumes", action="store_true", help="Показать список моих резюме на платформе")
    parser.add_argument("--search", action="store_true", help="Поиск вакансий без отклика (предпросмотр)")
    parser.add_argument("--apply", action="store_true", help="Запустить цикл автоматического отклика")
    parser.add_argument("--dry-run", action="store_true", help="Эмуляция отклика без реальной отправки")
    parser.add_argument("--stats", action="store_true", help="Показать историю откликов")

    args = parser.parse_args()

    if args.stats:
        handle_stats()
        return

    config = load_config(args.config)
    auth, client = get_platform_adapter(args.platform, config)

    if args.auth:
        handle_auth(auth, code=args.code)
    elif args.resumes:
        handle_list_resumes(client, args.platform)
    elif args.search:
        handle_search(client, config)
    elif args.apply:
        handle_apply(client, args.platform, config, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
