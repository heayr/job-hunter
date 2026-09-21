"""
Objective Testing Suite — Core Unit Tests
==========================================
Tests for the foundational modules: filter, anti_bs_filter, generator utilities.
Each test class targets a specific module with boundary, edge-case, and regression tests.
"""

import sys
import os
import unittest
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.conftest import make_vacancy, make_profile, assert_valid_vacancy


# ═══════════════════════════════════════════════
#  FILTER / profile_filter.py
# ═══════════════════════════════════════════════

class TestProfileFilter(unittest.TestCase):
    """Comprehensive tests for the vacancy qualification filter."""

    def setUp(self):
        from filter.profile_filter import is_qualified_vacancy, detect_vacancy_grade
        self.is_qualified = is_qualified_vacancy
        self.detect_grade = detect_vacancy_grade

    # ── Positive matches ──

    def test_react_frontend_accepted(self):
        ok, reason = self.is_qualified("Senior Frontend Developer", "React, TypeScript", "", "")
        self.assertTrue(ok)
        self.assertIn("MATCHED", reason.upper())

    def test_nextjs_frontend_accepted(self):
        ok, reason = self.is_qualified("Next.js Developer", "Next.js, React", "", "")
        self.assertTrue(ok)

    def test_fullstack_accepted(self):
        ok, reason = self.is_qualified("Full Stack Engineer", "React, Node.js, TypeScript", "", "")
        self.assertTrue(ok)

    def test_web_developer_accepted(self):
        ok, reason = self.is_qualified("Web Developer", "React, HTML, CSS", "", "")
        self.assertTrue(ok)

    def test_ui_engineer_accepted(self):
        ok, reason = self.is_qualified("UI Engineer", "React, Figma", "", "")
        self.assertTrue(ok)

    def test_hyphenated_frontend_accepted(self):
        ok, reason = self.is_qualified("Front-end Developer", "React", "", "")
        self.assertTrue(ok)

    def test_russian_frontend_accepted(self):
        ok, reason = self.is_qualified("Фронтенд разработчик", "React, Vue", "", "")
        self.assertTrue(ok)

    def test_product_engineer_accepted(self):
        ok, reason = self.is_qualified("Product Engineer", "React, TypeScript", "", "")
        self.assertTrue(ok)

    # ── Negative matches (blacklist) ──

    def test_python_rejected(self):
        ok, reason = self.is_qualified("Python Developer", "Python, Django", "", "")
        self.assertFalse(ok)
        self.assertIn("BLACKLIST", reason.upper())

    def test_java_rejected(self):
        ok, reason = self.is_qualified("Java Developer", "Java, Spring", "", "")
        self.assertFalse(ok)

    def test_php_rejected(self):
        ok, reason = self.is_qualified("PHP Developer", "PHP, Laravel", "", "")
        self.assertFalse(ok)

    def test_devops_rejected(self):
        ok, reason = self.is_qualified("DevOps Engineer", "Docker, K8s", "", "")
        self.assertFalse(ok)

    def test_qa_rejected(self):
        ok, reason = self.is_qualified("QA Engineer", "Playwright, Postman", "", "")
        self.assertFalse(ok)

    def test_data_analyst_rejected(self):
        ok, reason = self.is_qualified("Data Analyst", "SQL, Python", "", "")
        self.assertFalse(ok)

    def test_mobile_rejected(self):
        ok, reason = self.is_qualified("Android Developer", "Kotlin, Android SDK", "", "")
        self.assertFalse(ok)

    def test_angular_rejected(self):
        ok, reason = self.is_qualified("Angular Developer", "Angular, TypeScript", "", "")
        self.assertFalse(ok)

    # ── Resume / Candidate exclusion ──

    def test_candidate_resume_rejected(self):
        ok, reason = self.is_qualified("Frontend Developer", "", "Резюме: ищу работу", "Кандидат")
        self.assertFalse(ok)
        self.assertIn("Resume", reason)

    def test_cv_in_header_rejected(self):
        ok, reason = self.is_qualified("#CV Frontend Developer", "React", "", "")
        self.assertFalse(ok)

    def test_looking_for_job_rejected(self):
        ok, reason = self.is_qualified("Frontend Developer", "React", "ищу работу на позицию React", "Telegram")
        self.assertFalse(ok)

    # ── Ad/Event exclusion ──

    def test_webinar_rejected(self):
        ok, reason = self.is_qualified("Frontend Developer", "React", "Приходи на бесплатный вебинар", "TG Channel")
        self.assertFalse(ok)
        self.assertIn("Ad/Event", reason)

    def test_test_interview_rejected(self):
        ok, reason = self.is_qualified("Frontend Developer", "React", "Тестовый собес на Frontend", "TG Channel")
        self.assertFalse(ok)

    # ── Grade detection ──

    def test_grade_senior(self):
        self.assertEqual(self.detect_grade("Senior Frontend Developer"), "Senior")

    def test_grade_lead(self):
        self.assertEqual(self.detect_grade("Lead Frontend Developer"), "Lead")

    def test_grade_junior(self):
        self.assertEqual(self.detect_grade("Junior Frontend Developer"), "Junior")

    def test_grade_intern(self):
        self.assertEqual(self.detect_grade("Frontend Intern"), "Intern")

    def test_grade_middle_default(self):
        self.assertEqual(self.detect_grade("Frontend Developer"), "Middle")

    def test_grade_russian_senior(self):
        self.assertEqual(self.detect_grade("Сеньор Фронтенд разработчик"), "Senior")

    def test_grade_russian_intern(self):
        self.assertEqual(self.detect_grade("Стажер Frontend"), "Intern")

    # ── Edge cases ──

    def test_empty_title_rejected(self):
        ok, reason = self.is_qualified("", "React", "", "")
        self.assertFalse(ok)

    def test_empty_everything_rejected(self):
        ok, reason = self.is_qualified("", "", "", "")
        self.assertFalse(ok)

    def test_fullstack_with_backend_stack_accepted(self):
        ok, reason = self.is_qualified(
            "Full Stack Developer", "React, Python, Django", "", ""
        )
        self.assertTrue(ok, "Fullstack should override blacklist for backend tech")


# ═══════════════════════════════════════════════
#  ANTI-BS FILTER / anti_bs_filter.py
# ═══════════════════════════════════════════════

class TestAntiBSFilter(unittest.TestCase):
    """Tests for the toxic job description detector."""

    def setUp(self):
        from anti_bs_filter import analyze_vacancy_traps
        self.analyze = analyze_vacancy_traps

    def test_clean_description_no_warnings(self):
        desc = "Ищем React разработчика в команду. Опыт от 3 лет."
        warnings = self.analyze(desc)
        self.assertEqual(len(warnings), 0)

    def test_ip_self_employed_warning(self):
        desc = "Оформление как ИП, самозанятость. Б2Б контракт."
        warnings = self.analyze(desc)
        self.assertTrue(any("ИП" in w or "Самозанятость" in w for w in warnings))

    def test_b2b_contract_warning(self):
        desc = "Только B2B contract, no employment."
        warnings = self.analyze(desc)
        self.assertTrue(len(warnings) > 0)

    def test_test_assignment_warning(self):
        desc = "Нужно сделать тестовое задание перед собеседованием."
        warnings = self.analyze(desc)
        self.assertTrue(any("ТЕСТОВОЕ" in w.upper() for w in warnings))

    def test_attention_check_warning(self):
        desc = "Начни сопроводительное письмо со слова кодовое слово"
        warnings = self.analyze(desc)
        self.assertTrue(any("ВНИМАТЕЛЬНОСТЬ" in w.upper() for w in warnings))

    def test_github_check_warning(self):
        desc = "Пришлите ссылку на github профиль"
        warnings = self.analyze(desc)
        self.assertTrue(any("github" in w.lower() for w in warnings))

    def test_english_level_warning(self):
        desc = "Требуется свободный английский, уровень C1 или выше"
        warnings = self.analyze(desc)
        self.assertTrue(any("английский" in w.lower() for w in warnings))

    def test_multiple_warnings(self):
        desc = "Оформление ИП. Сделать тестовое задание. Github профиль обязателен."
        warnings = self.analyze(desc)
        self.assertGreaterEqual(len(warnings), 2)

    def test_case_insensitive(self):
        desc = "Только ИП. ТЕСТОВОЕ ЗАДАНИЕ."
        warnings = self.analyze(desc)
        self.assertGreaterEqual(len(warnings), 1)


# ═══════════════════════════════════════════════
#  GENERATOR UTILITIES
# ═══════════════════════════════════════════════

class TestGeneratorUtilities(unittest.TestCase):
    """Tests for generator helper functions."""

    def test_extract_target_keywords_react(self):
        from generator.pitch_builder import extract_target_keywords
        kws = extract_target_keywords("React Developer", "React, TypeScript", "Build React apps")
        self.assertIn("React", kws)
        self.assertIn("TypeScript", kws)

    def test_extract_target_keywords_always_includes_core(self):
        from generator.pitch_builder import extract_target_keywords
        kws = extract_target_keywords("Frontend Developer", "HTML, CSS", "")
        # React, TypeScript, JavaScript are always injected
        self.assertIn("React", kws)

    def test_determine_language_ru(self):
        from generator.pitch_builder import determine_language
        vac = {"company": "Яндекс", "title": "Фронтенд разработчик", "description": "Ищем разработчика", "source": "habr"}
        self.assertEqual(determine_language(vac), "ru")

    def test_determine_language_en(self):
        from generator.pitch_builder import determine_language
        vac = {"company": "Google", "title": "Frontend Developer", "description": "We need a developer", "source": "wwr"}
        self.assertEqual(determine_language(vac), "en")

    def test_determine_language_cyrillic(self):
        from generator.pitch_builder import determine_language
        vac = {"company": "Test", "title": "Разработчик", "description": "опыт работы", "source": "unknown"}
        self.assertEqual(determine_language(vac), "ru")

    def test_determine_language_latin(self):
        from generator.pitch_builder import determine_language
        vac = {"company": "Test", "title": "Developer", "description": "experience required", "source": "unknown"}
        self.assertEqual(determine_language(vac), "en")

    def test_calculate_match_score_react_vacancy(self):
        from generator.pitch_builder import calculate_match_score
        vac = {
            "title": "Senior Frontend Developer (React)",
            "description": "React, TypeScript, Next.js experience required",
            "skills": "React, TypeScript, Next.js, Redux"
        }
        score = calculate_match_score(vac)
        self.assertGreaterEqual(score, 60, "React vacancy should score >= 60")

    def test_calculate_match_score_qa_vacancy_low(self):
        from generator.pitch_builder import calculate_match_score
        vac = {
            "title": "QA Automation Engineer",
            "description": "Playwright, Selenium testing",
            "skills": "Playwright, Python"
        }
        score = calculate_match_score(vac)
        self.assertLess(score, 30, "QA vacancy should score < 30")

    def test_calculate_match_score_bounds(self):
        from generator.pitch_builder import calculate_match_score
        vac = {"title": "Frontend Developer", "description": "React", "skills": "React, TypeScript"}
        score = calculate_match_score(vac)
        self.assertGreaterEqual(score, 5)
        self.assertLessEqual(score, 98)

    def test_simple_markdown_to_html(self):
        from crm import simple_markdown_to_html
        md = "## Header\n**Bold** text\n• item1\n• item2"
        html = simple_markdown_to_html(md)
        self.assertIn("<h2>", html)
        self.assertIn("<strong>Bold</strong>", html)
        self.assertIn("&#8226;", html)

    def test_simple_markdown_escapes_html(self):
        from crm import simple_markdown_to_html
        html = simple_markdown_to_html("<script>alert('xss')</script>")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


# ═══════════════════════════════════════════════
#  LLM GENERATOR UTILITIES
# ═══════════════════════════════════════════════

class TestLLMGenerator(unittest.TestCase):
    """Tests for LLM helper functions."""

    def test_extract_json_payload_valid(self):
        from generator.llm_generator import extract_json_payload
        result = extract_json_payload('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_extract_json_payload_markdown_codeblock(self):
        from generator.llm_generator import extract_json_payload
        text = 'Here is the result:\n```json\n{"score": 75}\n```\nDone.'
        result = extract_json_payload(text)
        self.assertEqual(result, {"score": 75})

    def test_extract_json_payload_embedded(self):
        from generator.llm_generator import extract_json_payload
        text = 'Prefix {"key": "val"} suffix'
        result = extract_json_payload(text)
        self.assertEqual(result, {"key": "val"})

    def test_extract_json_payload_invalid(self):
        from generator.llm_generator import extract_json_payload
        result = extract_json_payload("not json at all")
        self.assertIsNone(result)

    def test_extract_json_payload_empty(self):
        from generator.llm_generator import extract_json_payload
        result = extract_json_payload("")
        self.assertIsNone(result)

    def test_extract_json_payload_none(self):
        from generator.llm_generator import extract_json_payload
        result = extract_json_payload(None)
        self.assertIsNone(result)

    def test_get_api_key_returns_string(self):
        from generator.llm_generator import get_api_key
        key = get_api_key()
        self.assertIsInstance(key, str)


# ═══════════════════════════════════════════════
#  COVER LETTER ENGINE
# ═══════════════════════════════════════════════

class TestCoverLetterEngine(unittest.TestCase):
    """Tests for cover letter validation and fact-checking."""

    def test_validate_valid_cover_letter(self):
        from generator.cover_letter_engine import validate_cover_letter_output
        data = {
            "cover_letter": "A" * 200,
            "short_dm": "B" * 60,
            "core_hook": "React performance",
            "tone_assessment": "Professional",
            "critique_notes": ["Removed generic fluff"],
            "fact_check_status": "VERIFIED",
        }
        ok, errors = validate_cover_letter_output(data)
        self.assertTrue(ok)
        self.assertEqual(len(errors), 0)

    def test_validate_missing_cover_letter(self):
        from generator.cover_letter_engine import validate_cover_letter_output
        data = {"short_dm": "B" * 60, "core_hook": "x", "tone_assessment": "y", "critique_notes": [], "fact_check_status": "z"}
        ok, errors = validate_cover_letter_output(data)
        self.assertFalse(ok)

    def test_validate_short_cover_letter(self):
        from generator.cover_letter_engine import validate_cover_letter_output
        data = {
            "cover_letter": "Too short",
            "short_dm": "Also short",
            "core_hook": "x", "tone_assessment": "y", "critique_notes": [], "fact_check_status": "z"
        }
        ok, errors = validate_cover_letter_output(data)
        self.assertFalse(ok)

    def test_fact_check_kubernetes_hallucination(self):
        from generator.cover_letter_engine import fact_check_cover_letter
        text = "Deployed Kubernetes cluster with 50 nodes for production workloads"
        profile = {"evidence": []}
        passed, warnings = fact_check_cover_letter(text, profile)
        self.assertFalse(passed)
        self.assertTrue(any("kubernetes" in w.lower() for w in warnings))

    def test_fact_check_founder_trap(self):
        from generator.cover_letter_engine import fact_check_cover_letter
        text = "As a founder of my startup, I built the entire platform from scratch"
        profile = {"evidence": []}
        passed, warnings = fact_check_cover_letter(text, profile)
        self.assertFalse(passed)
        self.assertTrue(any("founder" in w.lower() or "startup" in w.lower() for w in warnings))

    def test_fact_check_clean_text(self):
        from generator.cover_letter_engine import fact_check_cover_letter
        text = "Built production React applications with TypeScript and delivered measurable results."
        profile = {"evidence": [{"claim": "Built React apps", "tags": ["react"]}]}
        passed, warnings = fact_check_cover_letter(text, profile)
        self.assertTrue(passed)
        self.assertEqual(len(warnings), 0)


if __name__ == "__main__":
    unittest.main()
