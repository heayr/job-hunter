import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentPolicyConfig:
    """Configurable guardrail policy for Autonomous and Supervised agent application."""
    remote_only: bool = True
    min_salary_rub: int = 300000
    min_salary_usd: int = 3500
    allowed_locations: List[str] = field(default_factory=lambda: [
        "remote", "worldwide", "удаленно", "удалённо", "любая локация",
        "москва", "россия", "ереван", "тбилиси", "белград", "кипр", "eu"
    ])
    disallowed_locations: List[str] = field(default_factory=lambda: [
        "on-site us only", "us citizenship required", "security clearance", "strict office"
    ])
    forbidden_terms: List[str] = field(default_factory=lambda: [
        "неоплачиваемое тестовое", "тестовое задание до собеседования", "работа за процент без оклада"
    ])
    daily_application_limit: int = 25
    unknown_question_policy: str = "HONEST_ADJACENT"  # "ASK_USER" | "HONEST_ADJACENT" | "POLITE_SKIP"
    approval_policy: str = "SUPERVISED"  # "SUPERVISED" (always require user click) | "AUTONOMOUS"


def load_policy_config() -> AgentPolicyConfig:
    """Loads AgentPolicyConfig merged with persisted values from config.json."""
    import os
    import json
    cfg = AgentPolicyConfig()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "policy_min_salary_rub" in data:
                    cfg.min_salary_rub = int(data["policy_min_salary_rub"])
                if "policy_min_salary_usd" in data:
                    cfg.min_salary_usd = int(data["policy_min_salary_usd"])
                if "policy_remote_only" in data:
                    cfg.remote_only = bool(data["policy_remote_only"])
                if "policy_daily_limit" in data:
                    cfg.daily_application_limit = int(data["policy_daily_limit"])
        except Exception:
            pass
    return cfg


@dataclass
class PolicyEvaluationResult:
    can_apply: bool
    requires_approval: bool
    violations: List[str]
    warnings: List[str]
    daily_count: int
    daily_limit: int


def get_daily_application_count() -> int:
    """Returns the count of applications submitted today from SQLite."""
    from tracker.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT COUNT(*) as cnt FROM application_history
        WHERE date(applied_at) = date('now')
        """)
        row = cursor.fetchone()
        return row["cnt"] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


def evaluate_vacancy_policy(
    vacancy: Dict[str, Any],
    policy: Optional[AgentPolicyConfig] = None
) -> PolicyEvaluationResult:
    """
    Evaluates whether an agent is authorized to apply to a vacancy under Autonomous Policy.
    Enforces location, salary, remote/hybrid, daily rate limits, and red flag invariants.
    """
    if policy is None:
        policy = load_policy_config()

    violations = []
    warnings = []

    # 1. Daily rate limit check
    daily_count = get_daily_application_count()
    if daily_count >= policy.daily_application_limit:
        violations.append(f"Daily application limit reached ({daily_count}/{policy.daily_application_limit}). Autonomous submissions halted.")

    title = (vacancy.get("title") or "").lower()
    description = (vacancy.get("description") or "").lower()
    location = (vacancy.get("location") or "").lower()
    is_remote = bool(vacancy.get("is_remote", False)) or any(w in description for w in ["remote", "удаленн", "удалённ", "worldwide"])

    # 2. Remote / Hybrid Policy
    if policy.remote_only and not is_remote:
        # Check if office is required
        if any(w in description for w in ["только офис", "strict on-site", "office only", "работа в офисе"]):
            violations.append("Vacancy requires mandatory on-site office presence, violating remote-only policy.")
        else:
            warnings.append("Vacancy remote status is unconfirmed; manual review recommended.")

    # 3. Disallowed Locations
    for dis in policy.disallowed_locations:
        if dis in location or dis in description:
            violations.append(f"Disallowed location requirement detected: '{dis}'")

    # 4. Anti-BS & Forbidden terms
    for term in policy.forbidden_terms:
        if term in description:
            violations.append(f"Forbidden predatory condition detected: '{term}'")

    # 5. Salary Floor Policy
    salary_str = str(vacancy.get("salary") or "").lower()
    if salary_str and salary_str not in ("не указана", "по договоренности", "nan", "none", ""):
        # Extract digits, removing thousand separators like comma or space
        cleaned_sal = salary_str.replace('\xa0', '').replace(' ', '').replace(',', '')
        digits = re.findall(r'\d+', cleaned_sal)
        if digits:
            try:
                max_sal = int(digits[-1])
                if "$" in salary_str or "usd" in salary_str:
                    if max_sal < policy.min_salary_usd:
                        violations.append(f"Offered salary ${max_sal} is below policy floor ${policy.min_salary_usd}")
                elif "₽" in salary_str or "rub" in salary_str or "руб" in salary_str:
                    if max_sal < policy.min_salary_rub:
                        violations.append(f"Offered salary {max_sal} RUB is below policy floor {policy.min_salary_rub} RUB")
            except Exception:
                pass

    can_apply = len(violations) == 0
    # If policy is SUPERVISED, human approval is always required
    requires_approval = (policy.approval_policy == "SUPERVISED") or (len(warnings) > 0)

    return PolicyEvaluationResult(
        can_apply=can_apply,
        requires_approval=requires_approval,
        violations=violations,
        warnings=warnings,
        daily_count=daily_count,
        daily_limit=policy.daily_application_limit
    )
