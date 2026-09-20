#!/usr/bin/env python3
"""
Auto-Enrich: batch CareerOrchestrator pipeline for newly harvested vacancies.

Usage:
    python auto_enrich.py                  # enrich new vacancies only
    python auto_enrich.py --all            # re-enrich all vacancies
    python auto_enrich.py --auto-enqueue   # after enrichment, also auto-enqueue high-score vacancies

Reads vacancies from SQLite where understanding_json IS NULL (not yet enriched),
runs the 6-agent CareerOrchestrator pipeline, saves all artifacts, and optionally
queues tasks for the browser extension.
"""
import os
import sys
import json
import time
import sqlite3

sys.path.insert(0, os.path.dirname(__file__))

from tracker.db import get_db_connection, init_db, create_agent_task
from agents.multi_agent_roles import CareerOrchestrator
from generator.pitch_builder import generate_pitch
from generator.agent_policy import evaluate_vacancy_policy, load_policy_config


def get_vacancies_to_enrich(enrich_all: bool = False) -> list:
    """Fetch vacancies that haven't been enriched yet."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if enrich_all:
            cur.execute("SELECT * FROM vacancies ORDER BY created_at DESC")
        else:
            cur.execute("""
                SELECT * FROM vacancies 
                WHERE understanding_json IS NULL 
                AND status != 'blacklisted'
                ORDER BY created_at DESC
            """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def enrich_vacancy(vacancy: dict, orchestrator: CareerOrchestrator) -> dict:
    """Run the full 6-agent pipeline on a single vacancy."""
    vac_id = vacancy["id"]
    title = vacancy.get("title", "")
    company = vacancy.get("company", "Company")
    description = vacancy.get("description", "")
    url = vacancy.get("url", "")
    lang = vacancy.get("language", "ru")

    print(f"  🤖 Enriching: {title} @ {company}", flush=True)

    try:
        agent_context = orchestrator.process_application({
            "title": title,
            "description": description,
            "company": company,
            "url": url,
            "lang": lang,
            "use_ai": True
        })

        # Also generate AI-enhanced pitch
        pitch_data = generate_pitch(vacancy, use_ai=True)

        return {
            "success": True,
            "vacancy_id": vac_id,
            "agent_context": agent_context,
            "pitch_data": pitch_data
        }
    except Exception as e:
        print(f"  ✗ Failed: {title}: {e}", flush=True)
        return {
            "success": False,
            "vacancy_id": vac_id,
            "error": str(e)
        }


def save_enrichment_results(conn, vac_id: str, result: dict):
    """Save enriched artifacts to the database."""
    cur = conn.cursor()
    agent_context = result["agent_context"]
    pitch_data = result["pitch_data"]

    understanding = agent_context.get("job_understanding", {})
    app_thesis = agent_context.get("application_thesis", {})
    app_strategy = agent_context.get("application_strategy", {})
    ats_report = agent_context.get("ats_report", {})

    # Save deep analysis to vacancies table
    cur.execute("""
        UPDATE vacancies 
        SET understanding_json = ?, application_thesis_json = ?, 
            application_strategy_json = ?, ats_report_json = ?
        WHERE id = ?
    """, (
        json.dumps(understanding, ensure_ascii=False),
        json.dumps(app_thesis, ensure_ascii=False),
        json.dumps(app_strategy, ensure_ascii=False),
        json.dumps(ats_report, ensure_ascii=False),
        vac_id
    ))

    # Replace old pitches with AI-enhanced ones
    cur.execute("DELETE FROM pitches WHERE vacancy_id = ?", (vac_id,))

    lang = pitch_data.get("language", "ru")
    short_dm = agent_context.get("short_dm") or pitch_data.get("short_dm", "")
    cover_letter = agent_context.get("critic_refined_cover_letter") or pitch_data.get("cover_letter", "")
    tailored_cv = agent_context.get("resume_markdown") or pitch_data.get("tailored_cv", "")

    for p_type, content in [("short_dm", short_dm), ("cover_letter", cover_letter), ("tailored_cv", tailored_cv)]:
        cur.execute(
            "INSERT INTO pitches (vacancy_id, pitch_type, language, content, status) VALUES (?, ?, ?, ?, 'DRAFT')",
            (vac_id, p_type, lang, content)
        )

    # Update score and mark as enriched
    score = pitch_data.get("score", 0)
    cur.execute(
        "UPDATE vacancies SET score = ?, status = 'analyzed', language = ? WHERE id = ?",
        (score, lang, vac_id)
    )


def auto_enqueue_enriched(score_threshold: int = 70):
    """Queue agent tasks for enriched vacancies that meet the score threshold."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get enriched vacancies above threshold that haven't been queued yet
        cur.execute("""
            SELECT v.*, p.content as cover_letter
            FROM vacancies v
            LEFT JOIN pitches p ON v.id = p.vacancy_id AND p.pitch_type = 'cover_letter'
            WHERE v.status = 'analyzed' 
            AND v.score >= ?
            AND v.url != ''
            AND v.id NOT IN (SELECT vacancy_id FROM agent_tasks)
            ORDER BY v.score DESC
        """, (score_threshold,))
        vacancies = [dict(row) for row in cur.fetchall()]

        if not vacancies:
            print(f"\n📭 No enriched vacancies with score >= {score_threshold} to enqueue.", flush=True)
            return 0

        queued = 0
        policy = load_policy_config()
        for v in vacancies:
            # Evaluate policy before queuing
            policy_result = evaluate_vacancy_policy(v, policy)
            if not policy_result.can_apply:
                print(f"  ⚠ Skipping (policy violation): {v['title']} @ {v['company']}: {policy_result.violations}", flush=True)
                continue

            cover_letter = v.get("cover_letter") or ""
            source = v.get("source", "web")
            portal = source if source in ("hh", "habr", "linkedin", "greenhouse", "lever", "rabota", "superjob") else "web"

            create_agent_task(
                vacancy_id=v["id"],
                url=v["url"],
                company=v["company"],
                role_title=v["title"],
                portal=portal,
                cover_letter=cover_letter
            )
            cur.execute("UPDATE vacancies SET status = 'queued' WHERE id = ?", (v["id"],))
            queued += 1
            print(f"  ✓ Queued: {v['title']} @ {v['company']} (Score: {v['score']})", flush=True)

        conn.commit()
        return queued
    finally:
        conn.close()


def run(enrich_all: bool = False, auto_enqueue: bool = False, score_threshold: int = 70):
    """Main entry point for batch enrichment."""
    init_db()

    vacancies = get_vacancies_to_enrich(enrich_all=enrich_all)
    total = len(vacancies)

    if total == 0:
        print("✅ No new vacancies to enrich.", flush=True)
        print(f"PROGRESS:enriched=0:total=0:queued=0:name=completed", flush=True)
        return

    print(f"🚀 Enriching {total} vacancies with 6-agent pipeline...\n", flush=True)
    print(f"PROGRESS:enriched=0:total={total}:queued=0:name=started", flush=True)

    orchestrator = CareerOrchestrator()
    enriched = 0
    failed = 0

    conn = get_db_connection()
    try:
        for i, vacancy in enumerate(vacancies, 1):
            result = enrich_vacancy(vacancy, orchestrator)

            if result["success"]:
                save_enrichment_results(conn, vacancy["id"], result)
                enriched += 1
                print(f"  ✓ [{i}/{total}] Enriched: {vacancy.get('title')} @ {vacancy.get('company')}", flush=True)
            else:
                failed += 1
                print(f"  ✗ [{i}/{total}] Failed: {vacancy.get('title')}: {result['error']}", flush=True)

            conn.commit()

            # Progress marker for CRM UI polling
            if i % 5 == 0 or i == total:
                print(f"PROGRESS:enriched={enriched}:total={total}:failed={failed}:name=enriching", flush=True)

    finally:
        conn.close()

    # Auto-enqueue if requested
    queued = 0
    if auto_enqueue:
        print(f"\n📬 Auto-enqueuing vacancies with score >= {score_threshold}...", flush=True)
        queued = auto_enqueue_enriched(score_threshold)

    print(f"\n✅ Done: Enriched: {enriched} | Failed: {failed} | Queued: {queued}", flush=True)
    print(f"PROGRESS:enriched={enriched}:total={total}:failed={failed}:queued={queued}:name=completed", flush=True)


if __name__ == "__main__":
    enrich_all = "--all" in sys.argv
    auto_enqueue = "--auto-enqueue" in sys.argv
    score_threshold = 70

    for arg in sys.argv:
        if arg.startswith("--score="):
            try:
                score_threshold = int(arg.split("=")[1])
            except ValueError:
                pass

    run(enrich_all=enrich_all, auto_enqueue=auto_enqueue, score_threshold=score_threshold)
