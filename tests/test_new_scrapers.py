import unittest
import sys
import os
import json
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scrapers.crypto_scraper import CryptoScraper
from scrapers.remotive_scraper import RemotiveScraper
from scrapers.remoteok_scraper import RemoteOKScraper
from generator.pitch_builder import determine_language
import tracker.db as db


class TestNewScrapersAndMarkets(unittest.TestCase):
    def test_crypto_scraper_attributes(self):
        scraper = CryptoScraper()
        self.assertEqual(scraper.name, "crypto")
        self.assertTrue(hasattr(scraper, "scrape"))

    def test_remotive_scraper_attributes(self):
        scraper = RemotiveScraper()
        self.assertEqual(scraper.name, "remotive")
        self.assertTrue(hasattr(scraper, "scrape"))

    def test_remoteok_scraper_attributes(self):
        scraper = RemoteOKScraper()
        self.assertEqual(scraper.name, "remoteok")
        self.assertTrue(hasattr(scraper, "scrape"))

    def test_determine_language_explicit(self):
        vac_ru = {"language": "ru", "title": "React Developer", "source": "wwr"}
        vac_en = {"language": "en", "title": "Разработчик React", "source": "habr"}
        self.assertEqual(determine_language(vac_ru), "ru")
        self.assertEqual(determine_language(vac_en), "en")

    def test_determine_language_by_source(self):
        vac_crypto = {"source": "crypto", "title": "Frontend Engineer", "company": "Kraken"}
        vac_remotive = {"source": "remotive", "title": "React Lead", "company": "Lemon.io"}
        vac_habr = {"source": "habr", "title": "Senior Frontend Developer", "company": "Яндекс"}
        
        self.assertEqual(determine_language(vac_crypto), "en")
        self.assertEqual(determine_language(vac_remotive), "en")
        self.assertEqual(determine_language(vac_habr), "ru")

    def test_database_language_storage(self):
        original_db_path = db.DB_PATH
        test_db = os.path.join(os.path.dirname(__file__), "test_market.db")
        if os.path.exists(test_db):
            os.remove(test_db)
        
        try:
            db.set_db_path(test_db)
            db.init_db()
            
            vac_ru = {
                "id": "test_ru_1",
                "title": "Фронтенд разработчик",
                "company": "Тест Компания",
                "url": "https://example.com/ru-1",
                "source": "telegram",
                "language": "ru",
                "salary": "300 000 руб.",
                "description": "Описание вакансии",
                "score": 85,
            }
            vac_en = {
                "id": "test_en_1",
                "title": "Senior React Engineer",
                "company": "Global Crypto",
                "url": "https://example.com/en-1",
                "source": "crypto",
                "language": "en",
                "salary": "$120k",
                "description": "Remote vacancy description",
                "score": 90,
            }

            db.save_vacancy(vac_ru)
            db.save_vacancy(vac_en)

            conn = sqlite3.connect(test_db)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT language, source, title FROM vacancies ORDER BY id ASC")
            rows = cur.fetchall()
            conn.close()

            self.assertEqual(len(rows), 2)
            # test_en_1 comes before test_ru_1 alphabetically
            by_id = {r["source"]: r["language"] for r in rows}
            self.assertEqual(by_id["telegram"], "ru")
            self.assertEqual(by_id["crypto"], "en")
        finally:
            db.set_db_path(original_db_path)
            if os.path.exists(test_db):
                os.remove(test_db)


if __name__ == "__main__":
    unittest.main()
