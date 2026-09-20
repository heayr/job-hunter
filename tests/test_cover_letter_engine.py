import unittest
import json
from generator.candidate_profile import get_canonical_profile
from generator.job_understanding import heuristic_job_understanding
from generator.company_researcher import heuristic_company_dossier
from generator.thesis_generator import heuristic_application_thesis
from generator.evidence_retriever import heuristic_evidence_retrieval
from generator.application_strategy import heuristic_application_strategy
from generator.cover_letter_engine import (
    validate_cover_letter_output,
    fact_check_cover_letter,
    critic_refine_letter,
    heuristic_cover_letter,
    generate_cover_letter
)
from generator.pitch_builder import generate_pitch

class TestCoverLetterEngine(unittest.TestCase):
    def setUp(self):
        self.profile_ru = get_canonical_profile(lang="ru")
        self.profile_en = get_canonical_profile(lang="en")

    def test_validate_valid_cover_letter(self):
        valid = {
            "cover_letter": "Здравствуйте! Откликаюсь на позицию Senior Frontend Developer в TechCorp. Специализируюсь на продуктовом фронтенде с фокусом на масштабируемую архитектуру. Ключевые результаты: Next.js 16, React 19, PageSpeed 100/100. Буду рад обсудить задачи!",
            "short_dm": "Привет! Откликаюсь на позицию Senior Frontend Developer. Мой стек (React 19, Next.js 16) напрямую закрывает задачи. Буду рад пообщаться!",
            "core_hook": "Специализируюсь на продуктовой веб-разработке.",
            "tone_assessment": "Pragmatic, peer-to-peer",
            "critique_notes": ["Removed generic fluff"],
            "fact_check_status": "VERIFIED"
        }
        is_valid, errors = validate_cover_letter_output(valid)
        self.assertTrue(is_valid, f"Validation failed: {errors}")
        self.assertEqual(len(errors), 0)

    def test_validate_rejects_empty_fields(self):
        broken = {
            "cover_letter": "Short",
            "short_dm": ""
        }
        is_valid, errors = validate_cover_letter_output(broken)
        self.assertFalse(is_valid)
        self.assertTrue(any("cover_letter" in e or "short_dm" in e for e in errors))

    def test_critic_refine_letter_replaces_cliches_and_subservience(self):
        fluffy_draft = "Меня зовут Егор, и я хочу предложить свою кандидатуру на вакансию. Я опытный специалист и быстро обучаем. Буду бесконечно рад любой возможности пообщаться."
        strategy = {"deliberate_omissions": []}
        refined, notes = critic_refine_letter(fluffy_draft, strategy, lang="ru")
        
        self.assertNotIn("опытный специалист", refined.lower())
        self.assertNotIn("быстро обучаем", refined.lower())
        self.assertNotIn("хочу предложить свою кандидатуру", refined.lower())
        self.assertIn("Откликаюсь на позицию", refined)
        self.assertGreater(len(notes), 0)

    def test_critic_refine_letter_replaces_captain_obvious_openers(self):
        obvious_dm = "Привет! Вижу, что в Top Selection ищут Senior на .NET + Angular для enterprise-продуктов. Мой стек закрывает задачи."
        strategy = {"deliberate_omissions": []}
        refined, notes = critic_refine_letter(obvious_dm, strategy, lang="ru")
        self.assertNotIn("вижу, что", refined.lower())
        self.assertNotIn("ищут", refined.lower())
        self.assertGreater(len(notes), 0)

        obvious_dm_2 = "Привет! Увидел вакансию «Senior Frontend» в TechCorp. Буду рад пообщаться!"
        refined_2, notes_2 = critic_refine_letter(obvious_dm_2, strategy, lang="ru")
        self.assertNotIn("увидел вакансию", refined_2.lower())
        self.assertIn("Откликаюсь на позицию", refined_2)

    def test_fact_check_flags_unverified_dangerous_tech(self):
        clean_text = "Experienced in React 19, Next.js 16, TypeScript, Docker, and FastAPI."
        ok, warnings = fact_check_cover_letter(clean_text, self.profile_ru)
        self.assertTrue(ok)
        self.assertEqual(len(warnings), 0)

        dangerous_text = "I architected distributed Kubernetes cluster and Kafka cluster with Solidity smart contracts."
        ok_danger, warnings_danger = fact_check_cover_letter(dangerous_text, self.profile_ru)
        self.assertFalse(ok_danger)
        self.assertTrue(any("kubernetes" in w or "kafka" in w or "solidity" in w for w in warnings_danger))

    def test_heuristic_cover_letter_generates_authentic_peer_voice(self):
        ju = heuristic_job_understanding("Senior Frontend Engineer", "React 19, Next.js 16, PageSpeed", "FinTechScale")
        cd = heuristic_company_dossier("FinTechScale", "fintechscale.com", "Financial SaaS")
        re = heuristic_evidence_retrieval(self.profile_ru, ju, lang="ru")
        thesis = heuristic_application_thesis(self.profile_ru, ju, re, lang="ru")
        strategy = heuristic_application_strategy(self.profile_ru, ju, cd, thesis, lang="ru")

        res = heuristic_cover_letter(self.profile_ru, ju, strategy, thesis, lang="ru")
        is_valid, errors = validate_cover_letter_output(res)
        self.assertTrue(is_valid, f"Heuristic cover letter invalid: {errors}")

        cl = res["cover_letter"]
        dm = res["short_dm"]

        self.assertIn("Здравствуйте!", cl)
        self.assertIn("FinTechScale", cl)
        self.assertIn("Telegram:", cl)
        self.assertNotIn("фаундер", cl.lower())
        self.assertNotIn("основатель", cl.lower())

        self.assertIn("Привет!", dm)
        self.assertIn("FinTechScale", dm)

    def test_pitch_builder_delegates_to_cover_letter_engine(self):
        vac = {
            "id": "vac_test_cl_01",
            "title": "Lead Frontend Engineer",
            "company": "NextGenCorp",
            "skills": "React 19, Next.js 16, TypeScript",
            "description": "Build high-load client apps with Next.js."
        }
        pitch = generate_pitch(vac, use_ai=False)
        cl = pitch["cover_letter"]
        dm = pitch["short_dm"]

        self.assertIn("NextGenCorp", cl)
        self.assertIn("React 19", cl)
        self.assertIn("Telegram:", cl)
        self.assertIn("Email:", cl)
        self.assertNotIn("фаундер", cl.lower())

if __name__ == "__main__":
    unittest.main()
