import unittest
from generator.candidate_profile import get_canonical_profile
from generator.job_understanding import heuristic_job_understanding
from generator.evidence_retriever import heuristic_evidence_retrieval
from generator.thesis_critic import (
    detect_generic_fluff,
    heuristic_critique,
    evaluate_and_refine_thesis
)

class TestThesisCritic(unittest.TestCase):
    def setUp(self):
        self.profile_ru = get_canonical_profile(lang="ru")
        self.profile_en = get_canonical_profile(lang="en")

    def test_detect_generic_fluff(self):
        fluffy_text = "Я опытный специалист и быстро обучаем, идеально подхожу для вашей вакансии."
        fluff = detect_generic_fluff(fluffy_text)
        self.assertGreaterEqual(len(fluff), 2)

        clean_text = "Спроектировал микросервисную архитектуру на Next.js 16 и достиг 100/100 PageSpeed."
        no_fluff = detect_generic_fluff(clean_text)
        self.assertEqual(len(no_fluff), 0)

    def test_critique_rejects_fluffy_thesis(self):
        fluffy_thesis = {
            "thesis": "Я опытный специалист, быстро обучаем и идеально подхожу вашей компании.",
            "strategic_rationale": "Шаблонная аргументация",
            "supporting_evidence": []
        }
        job_understanding = {
            "role_overview": {"title": "Frontend Engineer", "company": "TechCorp"},
            "reasoning": {"likely_team_problems": ["Slow performance"]}
        }
        critique = heuristic_critique(fluffy_thesis, self.profile_ru, job_understanding, lang="ru")
        self.assertEqual(critique["verdict"], "REJECTED")
        self.assertTrue(critique["fluff_detected"])
        self.assertLess(critique["score"], 0.6)

    def test_critique_approves_strong_evidence_backed_thesis(self):
        strong_thesis = {
            "thesis": "Кандидат обладает подтвержденным опытом оптимизации Core Web Vitals до 100/100 на Next.js 16 (App Router), что напрямую решает задачу TechCorp по ускорению рендеринга.",
            "strategic_rationale": "Удар в техническую боль с доказанным решением.",
            "supporting_evidence": ["ev_01: Next.js 16 RSC streaming & PageSpeed 100/100"]
        }
        job_understanding = {
            "role_overview": {"title": "Senior Frontend Developer", "company": "TechCorp"},
            "reasoning": {"likely_team_problems": ["Просадка LCP и производительности"]}
        }
        critique = heuristic_critique(strong_thesis, self.profile_ru, job_understanding, lang="ru")
        self.assertEqual(critique["verdict"], "APPROVED")
        self.assertFalse(critique["fluff_detected"])
        self.assertGreaterEqual(critique["score"], 0.75)

    def test_evaluate_and_refine_loop(self):
        job_understanding = heuristic_job_understanding(
            "Senior Frontend Developer",
            "Ищем Senior инженера на Next.js 16 и React 19 для модернизации платформы.",
            "FintechApp"
        )
        reframed_ev = heuristic_evidence_retrieval(self.profile_ru, job_understanding, lang="ru")
        result = evaluate_and_refine_thesis(self.profile_ru, job_understanding, reframed_ev, lang="ru", use_ai=False)

        self.assertIn("thesis", result)
        self.assertIn("critique", result)
        self.assertIn("verdict", result["critique"])
        self.assertGreaterEqual(result["critique"]["score"], 0.1)
        self.assertLessEqual(result["critique"]["score"], 1.0)
        self.assertTrue(len(result["thesis"]) > 20)

if __name__ == "__main__":
    unittest.main()
