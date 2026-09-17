import unittest
import sys
import os
import json
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scrapers.ats_scraper import ATSScraper
from scrapers.hackernews_scraper import HackerNewsScraper
from scrapers.jobicy_scraper import JobicyScraper
from scrapers.getmatch_scraper import GetMatchScraper
from scrapers.setka_scraper import SetkaScraper
from enricher.ai_parser import heuristic_fallback_parse, ingest_vacancy_with_ai
from tracker.db import DB_PATH


class TestScrapersAndAiParser(unittest.TestCase):

    def test_ats_scraper_relevance_filter(self):
        scraper = ATSScraper()
        # Relevant titles
        self.assertTrue(scraper._is_relevant("Senior Frontend Engineer"))
        self.assertTrue(scraper._is_relevant("Fullstack Developer (React/Node)"))
        self.assertTrue(scraper._is_relevant("Staff Software Engineer - Web Platform"))
        self.assertTrue(scraper._is_relevant("React Native / TypeScript Specialist"))

        # Non-relevant titles should be rejected (Anti-BS)
        self.assertFalse(scraper._is_relevant("Contract Talent Acquisition Sourcer, Sales"))
        self.assertFalse(scraper._is_relevant("Account Executive - EMEA"))
        self.assertFalse(scraper._is_relevant("Corporate Counsel - Commercial Legal"))
        self.assertFalse(scraper._is_relevant("Director of People Operations"))

    def test_jobicy_scraper_instantiation(self):
        scraper = JobicyScraper()
        self.assertEqual(scraper.name, "jobicy")
        self.assertIn("react", scraper.tags)
        self.assertIn("frontend", scraper.tags)

    def test_hackernews_scraper_instantiation(self):
        scraper = HackerNewsScraper()
        self.assertEqual(scraper.name, "hackernews")
        self.assertTrue(scraper.relevant_regex.search("Fullstack Engineer (React/TypeScript)"))
        self.assertFalse(scraper.relevant_regex.search("Account Manager, Sales"))

    def test_ai_parser_heuristic_fallback(self):
        raw_text = """
        Компания: FinTech SuperApp
        Вакансия: Senior Frontend Developer (React / Next.js)
        Локация: Удаленно (Remote)
        Зарплата: 350 000 руб.
        Требования: Опыт с React, Next.js, TypeScript, Zustand, Redux.
        Пишите в Telegram: @fintech_recruiter_olga или на почту jobs@fintechapp.com
        """
        parsed = heuristic_fallback_parse(raw_text)
        self.assertIn("Senior Frontend Developer", parsed["title"])
        self.assertEqual(parsed["is_remote"], 1)
        self.assertEqual(parsed["language"], "ru")
        self.assertTrue(len(parsed["contact_handle"]) > 0)
        self.assertIn(parsed["contact_type"], ["telegram", "email", "portal"])

    def test_ingest_vacancy_with_ai_and_db_persistence(self):
        sample = """
        NextGen Cloud Systems
        Fullstack Engineer (React & TypeScript)
        Remote Worldwide
        Salary: $7,000 - $9,000 / month
        Stack: React, TypeScript, GraphQL, Node.js, Docker
        Contact: jobs@nextgencloud.io
        """
        result = ingest_vacancy_with_ai(sample, is_url=False)
        self.assertTrue(result["success"], msg=f"Ingest failed: {result.get('error')}")
        self.assertIn("vacancy_id", result)
        self.assertGreater(result["score"], 0)

        vac_id = result["vacancy_id"]

        # Verify SQLite persistence
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM vacancies WHERE id = ?", (vac_id,))
        vac_row = cur.fetchone()
        self.assertIsNotNone(vac_row)
        self.assertEqual(vac_row["source"], "ai_import")
        self.assertGreater(vac_row["score"], 0)

        # Verify Pitches generated and persisted
        cur.execute("SELECT * FROM pitches WHERE vacancy_id = ?", (vac_id,))
        pitches = cur.fetchall()
        self.assertGreaterEqual(len(pitches), 3)

        pitch_types = [p["pitch_type"] for p in pitches]
        self.assertIn("short_dm", pitch_types)
        self.assertIn("cover_letter", pitch_types)
        self.assertIn("tailored_cv", pitch_types)

        conn.close()

    def test_getmatch_scraper_instantiation(self):
        scraper = GetMatchScraper()
        self.assertEqual(scraper.name, "getmatch")
        self.assertIn("Frontend", scraper.queries)
        self.assertIn("React", scraper.queries)

    def test_setka_scraper_instantiation(self):
        scraper = SetkaScraper()
        self.assertEqual(scraper.name, "setka")
        self.assertGreater(len(scraper.feed_ids), 0)


if __name__ == "__main__":
    unittest.main()
