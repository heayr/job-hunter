import unittest
import os
import json
import tempfile
from generator.candidate_profile import (
    validate_canonical_profile,
    upgrade_legacy_profile,
    load_canonical_profiles,
    save_canonical_profiles,
    get_canonical_profile,
    FactType
)
from tracker.db import init_db, get_db_connection, sync_canonical_profiles_to_db, get_candidate_profile_from_db

class TestCandidateProfile(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_validate_valid_canonical_profile(self):
        valid_data = {
            "id": "profile_test_1",
            "lang": "ru",
            "identity": {
                "name": "Иван Тестов",
                "target_role": "Senior Frontend Developer",
                "location": "Москва | Remote",
                "contacts": {
                    "email": "ivan@example.com",
                    "telegram": "@ivantest",
                    "github": "https://github.com/ivantest"
                }
            },
            "evidence": [
                {
                    "id": "ev_01",
                    "claim": "100/100 Core Web Vitals on Next.js 16",
                    "category": "performance",
                    "problem": "Slow initial hydration on high traffic pages",
                    "context": "Lead Frontend at E-commerce platform",
                    "action": "Migrated to Next.js 16 App Router streaming architecture",
                    "decision": "Replaced heavy client bundle with React Server Components",
                    "result": "PageSpeed score reached 100/100, LCP down to 0.8s",
                    "technologies": ["Next.js", "React", "TypeScript"],
                    "source": "experience_entry_1",
                    "verified": True,
                    "fact_type": FactType.VERIFIED_FACT
                }
            ]
        }
        is_valid, errors = validate_canonical_profile(valid_data)
        self.assertTrue(is_valid, f"Validation errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_validate_rejects_missing_identity_or_id(self):
        invalid_data = {
            "lang": "ru"
        }
        is_valid, errors = validate_canonical_profile(invalid_data)
        self.assertFalse(is_valid)
        self.assertTrue(any("id" in err for err in errors))
        self.assertTrue(any("identity" in err for err in errors))

    def test_validate_rejects_malformed_evidence(self):
        invalid_evidence_profile = {
            "id": "prof_ev_fail",
            "lang": "en",
            "identity": {
                "name": "John Tester",
                "target_role": "Fullstack Engineer",
                "contacts": {"email": "john@example.com"}
            },
            "evidence": [
                {
                    "id": "ev_broken",
                    "claim": "Something without action or result"
                }
            ]
        }
        is_valid, errors = validate_canonical_profile(invalid_evidence_profile)
        self.assertFalse(is_valid)
        self.assertTrue(any("action" in err for err in errors))
        self.assertTrue(any("result" in err for err in errors))

    def test_upgrade_legacy_profile(self):
        legacy = {
            "id": "legacy_prof_1",
            "lang": "ru",
            "name": "Петр Разработчик",
            "role": "Frontend Developer",
            "summary": "Разработчик с 5 годами опыта",
            "experience": "• Разработал дизайн-систему на React и TypeScript\n• Оптимизировал скорость загрузки на 30%",
            "keywords": "React, TypeScript, Docker"
        }
        canonical = upgrade_legacy_profile(legacy)
        is_valid, errors = validate_canonical_profile(canonical)
        self.assertTrue(is_valid, f"Upgraded profile invalid: {errors}")

        self.assertEqual(canonical["id"], "legacy_prof_1")
        self.assertEqual(canonical["identity"]["name"], "Петр Разработчик")
        self.assertEqual(canonical["identity"]["target_role"], "Frontend Developer")
        self.assertGreaterEqual(len(canonical["evidence"]), 2)
        # Verify backward compatibility fields
        self.assertEqual(canonical["name"], "Петр Разработчик")
        self.assertEqual(canonical["role"], "Frontend Developer")
        self.assertIn("React", canonical["keywords"])

    def test_multi_profile_retrieval(self):
        profiles = load_canonical_profiles()
        self.assertIsInstance(profiles, list)
        if profiles:
            p_ru = get_canonical_profile(lang="ru")
            self.assertIsNotNone(p_ru)
            self.assertIn("identity", p_ru)
            self.assertIn("evidence", p_ru)

    def test_database_sync_isolated(self):
        test_profile = upgrade_legacy_profile({
            "id": "db_test_profile_ru",
            "lang": "ru",
            "name": "Тестовый Кандидат",
            "role": "Tech Lead",
            "experience": "• Руководил командой из 6 инженеров"
        })
        sync_canonical_profiles_to_db([test_profile])
        db_p = get_candidate_profile_from_db("db_test_profile_ru")
        self.assertIsNotNone(db_p)
        self.assertEqual(db_p["id"], "db_test_profile_ru")
        self.assertEqual(db_p["identity"]["name"], "Тестовый Кандидат")

if __name__ == "__main__":
    unittest.main()
