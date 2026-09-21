"""
Objective Testing Suite — Property-Based Tests
===============================================
Uses Hypothesis to generate random inputs and verify invariants.
Tests core logic properties that must hold for ALL valid inputs.
"""

import sys
import os
import re
import string
import unittest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import rule, invariant, initialize, RuleBasedStateMachine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ═══════════════════════════════════════════════
#  FILTER INVARIANTS
# ═══════════════════════════════════════════════

class TestFilterProperties(unittest.TestCase):
    """Property-based tests for the vacancy filter."""

    @given(st.text(min_size=0, max_size=200))
    def test_filter_never_crashes_on_random_input(self, title):
        """Filter must never raise exceptions on arbitrary input."""
        from filter.profile_filter import is_qualified_vacancy
        try:
            is_qualified_vacancy(title, "", "", "")
        except Exception as e:
            self.fail(f"Filter crashed on title '{title}': {e}")

    @given(st.text(min_size=1, max_size=100))
    def test_grade_detection_never_crashes(self, title):
        """Grade detection must never raise exceptions."""
        from filter.profile_filter import detect_vacancy_grade
        try:
            result = detect_vacancy_grade(title)
            self.assertIn(result, ["Intern", "Junior", "Middle", "Senior", "Lead"])
        except Exception as e:
            self.fail(f"Grade detection crashed on '{title}': {e}")

    @given(st.sampled_from([
        "Python Developer", "Java Developer", "PHP Developer",
        "DevOps Engineer", "QA Engineer", "Ruby Developer",
        "C++ Developer", "Go Developer", "Rust Developer"
    ]))
    def test_blacklist_always_rejects_known_bad_roles(self, title):
        """Blacklisted roles must always be rejected."""
        from filter.profile_filter import is_qualified_vacancy
        ok, reason = is_qualified_vacancy(title, "", "", "")
        self.assertFalse(ok, f"Blacklisted role '{title}' should be rejected, got reason: {reason}")

    @given(st.sampled_from([
        "Senior Frontend Developer", "React Developer",
        "Full Stack Engineer", "Next.js Developer",
        "UI Engineer", "Web Developer"
    ]))
    def test_positive_roles_always_accepted(self, title):
        """Known positive roles must always be accepted."""
        from filter.profile_filter import is_qualified_vacancy
        ok, reason = is_qualified_vacancy(title, "React, TypeScript", "", "")
        self.assertTrue(ok, f"Positive role '{title}' should be accepted, got: {reason}")

    @given(st.integers(min_value=0, max_value=10000))
    def test_vacancy_id_always_string(self, numeric_id):
        """Vacancy ID must be converted to string safely."""
        from filter.profile_filter import is_qualified_vacancy
        ok, reason = is_qualified_vacancy(str(numeric_id), "", "", "")
        self.assertIsInstance(ok, bool)


# ═══════════════════════════════════════════════
#  ANTI-BS FILTER INVARIANTS
# ═══════════════════════════════════════════════

class TestAntiBSFilterProperties(unittest.TestCase):
    """Property-based tests for the anti-BS filter."""

    @given(st.text(min_size=0, max_size=5000))
    def test_analyze_never_crashes(self, description):
        """Anti-BS analyzer must never crash on any input."""
        from anti_bs_filter import analyze_vacancy_traps
        try:
            result = analyze_vacancy_traps(description)
            self.assertIsInstance(result, list)
        except Exception as e:
            self.fail(f"Anti-BS filter crashed: {e}")

    @given(st.text(min_size=1, max_size=2000))
    def test_warnings_always_strings(self, description):
        """All warnings must be strings."""
        from anti_bs_filter import analyze_vacancy_traps
        warnings = analyze_vacancy_traps(description)
        for w in warnings:
            self.assertIsInstance(w, str)
            self.assertGreater(len(w), 0)

    @given(st.sampled_from([
        "Оформление как ИП", "самозанятость", "B2B contract",
        "только ИП", "индивидуальный предприниматель", "самозанятый"
    ]))
    def test_ip_keywords_always_warn(self, keyword):
        """IP/self-employed keywords must always trigger warnings."""
        from anti_bs_filter import analyze_vacancy_traps
        warnings = analyze_vacancy_traps(f"Работа: {keyword}")
        self.assertGreater(len(warnings), 0, f"Keyword '{keyword}' should trigger a warning")


# ═══════════════════════════════════════════════
#  MATCH SCORE INVARIANTS
# ═══════════════════════════════════════════════

class TestMatchScoreProperties(unittest.TestCase):
    """Property-based tests for the match score calculator."""

    @given(st.dictionaries(
        keys=st.sampled_from(["title", "description", "skills"]),
        values=st.text(min_size=0, max_size=500),
        min_size=1, max_size=3
    ))
    def test_score_always_in_bounds(self, vacancy):
        """Score must always be between 5 and 98."""
        from generator.pitch_builder import calculate_match_score
        score = calculate_match_score(vacancy)
        self.assertGreaterEqual(score, 5, "Score must be >= 5")
        self.assertLessEqual(score, 98, "Score must be <= 98")

    @given(st.text(min_size=0, max_size=300))
    def test_score_never_crashes(self, title):
        """Score calculator must never crash."""
        from generator.pitch_builder import calculate_match_score
        try:
            vac = {"title": title, "description": "", "skills": ""}
            score = calculate_match_score(vac)
            self.assertIsInstance(score, int)
        except Exception as e:
            self.fail(f"Score calculator crashed on '{title}': {e}")

    def test_qa_role_always_low_score(self):
        """QA-related titles must always score low."""
        from generator.pitch_builder import calculate_match_score
        qa_titles = ["QA Engineer", "QA Automation", "SDET", "Test Engineer"]
        for title in qa_titles:
            score = calculate_match_score({"title": title, "description": "", "skills": ""})
            self.assertLess(score, 30, f"QA title '{title}' should score < 30, got {score}")

    def test_react_senior_always_high_score(self):
        """React senior roles must always score high."""
        from generator.pitch_builder import calculate_match_score
        score = calculate_match_score({
            "title": "Senior Frontend Developer (React)",
            "description": "React, TypeScript, Next.js",
            "skills": "React, TypeScript, Next.js, Redux"
        })
        self.assertGreaterEqual(score, 65, f"React senior should score >= 65, got {score}")


# ═══════════════════════════════════════════════
#  KEYWORD EXTRACTION INVARIANTS
# ═══════════════════════════════════════════════

class TestKeywordExtractionProperties(unittest.TestCase):
    """Property-based tests for keyword extraction."""

    @given(st.text(min_size=0, max_size=1000))
    def test_extraction_never_crashes(self, text):
        """Keyword extraction must never crash."""
        from generator.pitch_builder import extract_target_keywords
        try:
            result = extract_target_keywords(text, "", "")
            self.assertIsInstance(result, list)
        except Exception as e:
            self.fail(f"Keyword extraction crashed: {e}")

    @given(st.text(min_size=0, max_size=1000))
    def test_always_returns_list(self, text):
        """Must always return a list."""
        from generator.pitch_builder import extract_target_keywords
        result = extract_target_keywords(text, "", "")
        self.assertIsInstance(result, list)

    @given(st.text(min_size=0, max_size=1000))
    def test_always_includes_core_tech(self, text):
        """React, TypeScript, JavaScript must always be in results."""
        from generator.pitch_builder import extract_target_keywords
        result = extract_target_keywords(text, "", "")
        self.assertIn("React", result)
        self.assertIn("TypeScript", result)
        self.assertIn("JavaScript", result)

    @given(st.text(min_size=0, max_size=500))
    def test_deduplication(self, text):
        """Results must not contain duplicates."""
        from generator.pitch_builder import extract_target_keywords
        result = extract_target_keywords(text, text, text)
        self.assertEqual(len(result), len(set(result)), "Keywords must be deduplicated")


# ═══════════════════════════════════════════════
#  LANGUAGE DETECTION INVARIANTS
# ═══════════════════════════════════════════════

class TestLanguageDetectionProperties(unittest.TestCase):
    """Property-based tests for language detection."""

    @given(st.text(min_size=0, max_size=500))
    def test_detection_never_crashes(self, text):
        """Language detection must never crash."""
        from generator.pitch_builder import determine_language
        try:
            result = determine_language({"company": text, "title": text, "description": text, "source": "test"})
            self.assertIn(result, ["ru", "en"])
        except Exception as e:
            self.fail(f"Language detection crashed: {e}")

    def test_cyrillic_always_ru(self):
        """Cyrillic text must always detect as Russian."""
        from generator.pitch_builder import determine_language
        cyrillic_texts = ["Привет", "Разработчик", "Москва", "Тест"]
        for text in cyrillic_texts:
            result = determine_language({"company": "", "title": text, "description": "", "source": ""})
            self.assertEqual(result, "ru", f"Cyrillic '{text}' should detect as ru")

    def test_latin_always_en(self):
        """Pure Latin text must always detect as English."""
        from generator.pitch_builder import determine_language
        latin_texts = ["Hello", "Developer", "New York", "Test"]
        for text in latin_texts:
            result = determine_language({"company": "", "title": text, "description": "", "source": ""})
            self.assertEqual(result, "en", f"Latin '{text}' should detect as en")


# ═══════════════════════════════════════════════
#  LLM JSON EXTRACTION INVARIANTS
# ═══════════════════════════════════════════════

class TestLLMJSONExtractionProperties(unittest.TestCase):
    """Property-based tests for JSON extraction from LLM output."""

    @given(st.text(min_size=0, max_size=2000))
    def test_extraction_never_crashes(self, text):
        """JSON extraction must never crash."""
        from generator.llm_generator import extract_json_payload
        try:
            result = extract_json_payload(text)
            if result is not None:
                self.assertIn(type(result), [dict, list, int, float, str, bool, type(None)])
        except Exception as e:
            self.fail(f"JSON extraction crashed: {e}")

    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=20, alphabet=string.ascii_lowercase),
        values=st.text(min_size=1, max_size=50),
        min_size=1, max_size=5
    ))
    def test_valid_json_always_extracted(self, data):
        """Valid JSON must always be extracted."""
        from generator.llm_generator import extract_json_payload
        import json
        text = json.dumps(data)
        result = extract_json_payload(text)
        self.assertEqual(result, data)

    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=20, alphabet=string.ascii_lowercase),
        values=st.text(min_size=1, max_size=50),
        min_size=1, max_size=5
    ))
    def test_markdown_wrapped_json_extracted(self, data):
        """JSON wrapped in markdown codeblock must be extracted."""
        from generator.llm_generator import extract_json_payload
        import json
        text = f"Here is the result:\n```json\n{json.dumps(data)}\n```\nDone."
        result = extract_json_payload(text)
        self.assertEqual(result, data)


# ═══════════════════════════════════════════════
#  MARKDOWN TO HTML INVARIANTS
# ═══════════════════════════════════════════════

class TestMarkdownToHTMLProperties(unittest.TestCase):
    """Property-based tests for markdown-to-HTML converter."""

    @given(st.text(min_size=0, max_size=2000))
    def test_conversion_never_crashes(self, text):
        """Markdown conversion must never crash."""
        from crm import simple_markdown_to_html
        try:
            result = simple_markdown_to_html(text)
            self.assertIsInstance(result, str)
        except Exception as e:
            self.fail(f"Markdown conversion crashed: {e}")

    @given(st.text(min_size=0, max_size=2000))
    def test_html_tags_escaped(self, text):
        """Raw HTML tags in input must be escaped in output."""
        from crm import simple_markdown_to_html
        result = simple_markdown_to_html(text)
        if "<script>" in text.lower():
            self.assertNotIn("<script>", result.lower(), "Script tags must be escaped")

    @given(st.text(min_size=1, max_size=500))
    def test_output_size_reasonable(self, text):
        """Output should not be massively larger than input."""
        from crm import simple_markdown_to_html
        result = simple_markdown_to_html(text)
        self.assertLess(len(result), len(text) * 10, "Output is unreasonably large")


if __name__ == "__main__":
    unittest.main()
