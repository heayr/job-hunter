"""
Objective Testing Framework — Shared Fixtures & Utilities
=========================================================
Provides reusable test infrastructure for the Job Hunter CRM project:
- In-memory SQLite database fixtures
- Factory functions for test data (vacancies, profiles, pitches)
- Mock helpers for external services (Gemini API, scrapers)
- Coverage-aware assertions and metric tracking
"""

import os
import sys
import json
import sqlite3
import tempfile
import unittest
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ─────────────────────────────────────────────
#  In-Memory Database Fixture
# ─────────────────────────────────────────────

@pytest.fixture
def in_memory_db():
    """Creates a fresh in-memory SQLite database with full schema for each test."""
    from tracker.db import init_db, set_db_path, reset_db_path

    set_db_path(":memory:")
    init_db(":memory:")
    yield ":memory:"
    reset_db_path()


@pytest.fixture
def temp_db_file(tmp_path):
    """Creates a temporary SQLite database file."""
    from tracker.db import init_db, set_db_path, reset_db_path

    db_path = str(tmp_path / "test_jobs.db")
    set_db_path(db_path)
    init_db(db_path)
    yield db_path
    reset_db_path()


# ─────────────────────────────────────────────
#  Factory Functions for Test Data
# ─────────────────────────────────────────────

def make_vacancy(
    vid: str = "test_vac_001",
    title: str = "Senior Frontend Developer (React)",
    company: str = "TechCorp",
    url: str = "https://example.com/jobs/1",
    source: str = "test",
    description: str = "We need a React developer with TypeScript experience.",
    skills: str = "React, TypeScript, Next.js",
    salary: str = "200 000 - 300 000 руб.",
    location: str = "Moscow",
    language: str = "ru",
    grade: str = "Senior",
    **overrides
) -> Dict[str, Any]:
    """Factory for vacancy test data."""
    base = {
        "id": vid,
        "title": title,
        "company": company,
        "url": url,
        "source": source,
        "description": description,
        "skills": skills,
        "salary": salary,
        "location": location,
        "language": language,
        "grade": grade,
        "is_remote": False,
        "contact_name": "",
        "contact_handle": "",
        "contact_type": "",
    }
    base.update(overrides)
    return base


def make_profile(
    profile_id: str = "test_profile_ru",
    lang: str = "ru",
    name: str = "Тест Кандидат",
    target_role: str = "Frontend Engineer",
    **overrides
) -> Dict[str, Any]:
    """Factory for candidate profile test data."""
    base = {
        "id": profile_id,
        "lang": lang,
        "name": name,
        "target_role": target_role,
        "identity": {
            "name": name,
            "target_role": target_role,
            "contacts": {
                "telegram": "@test_user",
                "email": "test@example.com",
                "github": "https://github.com/testuser",
                "linkedin": "https://linkedin.com/in/testuser",
            }
        },
        "evidence": [
            {
                "id": "ev_001",
                "claim": "Built high-performance React dashboard",
                "action": "Architected and implemented a real-time dashboard with React 18, TypeScript, and WebSocket",
                "result": "Achieved 100/100 Core Web Vitals score",
                "fact_type": "VERIFIED_FACT",
                "tags": ["react", "typescript", "performance"],
                "technologies": ["React", "TypeScript", "WebSocket"],
            }
        ],
        "keywords": "React, Next.js, TypeScript, JavaScript, Redux Toolkit, Tailwind CSS",
        "summary": "Frontend Engineer with 6+ years of experience building production web applications.",
        "experience": "• Built high-performance React applications\n• Delivered production-ready microservices\n• Integrated modern auth and state management",
        "key_achievements": [
            {
                "id": "ach_001",
                "action": "Built real-time dashboard",
                "result": "100/100 Core Web Vitals",
                "metric": "100",
                "metric_unit": "score",
                "tags": ["react", "performance"],
                "technologies": ["React", "TypeScript"],
                "defensibility": "HIGH",
            }
        ],
        "contacts": f"Telegram: @test_user | Email: test@example.com | GitHub: https://github.com/testuser",
        "contacts_structured": {
            "telegram": "@test_user",
            "email": "test@example.com",
            "github": "https://github.com/testuser",
            "linkedin": "https://linkedin.com/in/testuser",
        },
    }
    base.update(overrides)
    return base


def make_pitch(
    vacancy_id: str = "test_vac_001",
    pitch_type: str = "cover_letter",
    lang: str = "ru",
    content: str = "Тестовое сопроводительное письмо для позиции. " * 10,
    rating: int = 0,
    status: str = "DRAFT",
) -> Dict[str, Any]:
    """Factory for pitch test data."""
    return {
        "vacancy_id": vacancy_id,
        "pitch_type": pitch_type,
        "language": lang,
        "content": content,
        "rating": rating,
        "status": status,
    }


# ─────────────────────────────────────────────
#  Mock Helpers
# ─────────────────────────────────────────────

@pytest.fixture
def mock_gemini_api():
    """Mock Gemini API responses for testing AI-dependent code paths."""
    mock_response = {
        "success": True,
        "short_dm": "Привет! Откликаюсь на позицию React разработчика. Имею 6+ лет опыта.",
        "cover_letter": (
            "Здравствуйте!\n\n"
            "Меня зовут Тест Кандидат, откликаюсь на вакансию React разработчика.\n\n"
            "Специализируюсь на фронтенде и фуллстек-разработке (React, Next.js, TypeScript). "
            "Фокусируюсь на чистой архитектуре, высокой производительности и надежности в production.\n\n"
            "Буду рад обсудить задачи с командой!\n\n"
            "Контакты:\nTelegram: @test_user | Email: test@example.com"
        ),
        "score": 75,
        "language": "ru",
    }
    with patch("generator.llm_generator.generate_ai_pitch", return_value=mock_response):
        yield mock_response


@pytest.fixture
def mock_http_request():
    """Generic mock for urllib.request.urlopen."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        yield mock_resp


# ─────────────────────────────────────────────
#  Coverage Metrics Tracking
# ─────────────────────────────────────────────

class CoverageTracker:
    """Tracks test execution metrics for objective quality assessment."""

    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.tests_skipped = 0
        self.coverage_by_module = {}
        self.execution_times = []

    def record_test(self, passed: bool, skipped: bool = False, duration: float = 0):
        self.tests_run += 1
        if skipped:
            self.tests_skipped += 1
        elif passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
        self.execution_times.append(duration)

    def quality_score(self) -> float:
        """Objective quality score: 0-100 based on pass rate and coverage."""
        if self.tests_run == 0:
            return 0.0
        pass_rate = self.tests_passed / self.tests_run
        avg_coverage = (
            sum(self.coverage_by_module.values()) / len(self.coverage_by_module)
            if self.coverage_by_module else 0
        )
        # Weighted: 60% pass rate + 40% average coverage
        return round(pass_rate * 60 + (avg_coverage / 100) * 40, 1)


@pytest.fixture
def coverage_tracker():
    """Shared coverage tracker instance."""
    return CoverageTracker()


# ─────────────────────────────────────────────
#  Reusable Assertion Helpers
# ─────────────────────────────────────────────

def assert_valid_vacancy(vac: Dict[str, Any]):
    """Assert a vacancy dict has all required fields."""
    required = ["id", "title", "company", "url", "source", "description"]
    for field in required:
        assert field in vac, f"Vacancy missing required field: {field}"
    assert isinstance(vac["title"], str) and len(vac["title"]) > 0
    assert isinstance(vac["company"], str) and len(vac["company"]) > 0


def assert_valid_profile(profile: Dict[str, Any]):
    """Assert a profile dict has all required fields."""
    required = ["id", "lang", "name"]
    for field in required:
        assert field in profile, f"Profile missing required field: {field}"
    assert profile["lang"] in ("ru", "en"), f"Invalid lang: {profile['lang']}"


def assert_valid_pitch(pitch: Dict[str, Any]):
    """Assert a pitch dict has all required fields."""
    required = ["vacancy_id", "pitch_type", "content"]
    for field in required:
        assert field in pitch, f"Pitch missing required field: {field}"
    assert pitch["pitch_type"] in ("short_dm", "cover_letter", "tailored_cv")
    assert len(pitch["content"]) > 0, "Pitch content must not be empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
