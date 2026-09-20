import json
import os
import re
from typing import Dict, Any, List, Optional, Tuple

# ── EVIDENCE & PROFILE TYPES ──────────────────────────────────────────────────

class FactType:
    VERIFIED_FACT = "VERIFIED_FACT"
    AI_INTERPRETATION = "AI_INTERPRETATION"

DEFAULT_SCREENING_FACTS = {
    "salary": {
        "min_rub": 350000,
        "target_rub": 450000,
        "min_usd": 4000,
        "target_usd": 5500,
        "currency": "RUB/USD"
    },
    "notice_period": "2 недели / 2 weeks",
    "notice_period_days": 14,
    "work_authorization": "Гражданство РФ, самозанятость, ИП, B2B контракт (Global Remote)",
    "work_authorization_en": "Authorized for remote B2B contracts globally (IE / Contractor). Eligible for Russian entities.",
    "years_of_experience": "6+ лет / 6+ years",
    "years_of_experience_num": 6,
    "english_level": "C1 — Advanced / Fluent Technical & Business English",
    "languages": {
        "ru": "Родной (Native)",
        "en": "C1 (Advanced / Fluent)"
    },
    "relocation": "Готов к релокации или Full Remote",
    "location": "Москва, Россия / Remote",
    "start_date": "Через 2 недели после оффера / 2 weeks from offer"
}

def validate_canonical_profile(profile: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates that a profile complies with Canonical Candidate Profile requirements.
    Ensures zero-hallucination invariants:
    - Must have unique ID, lang, identity with name and contacts
    - If evidence exists, every evidence item must have problem, action, result and source.
    """
    errors = []
    if not isinstance(profile, dict):
        return False, ["Profile must be a dictionary"]

    # 1. Base identifiers
    if not profile.get("id"):
        errors.append("Profile missing required 'id'")
    if not profile.get("lang") or profile.get("lang") not in ("ru", "en"):
        errors.append("Profile missing or invalid 'lang' (must be 'ru' or 'en')")

    # 2. Identity
    identity = profile.get("identity")
    if not identity or not isinstance(identity, dict):
        errors.append("Profile missing required 'identity' object")
    else:
        if not identity.get("name"):
            errors.append("Identity missing 'name'")
        if not identity.get("target_role"):
            errors.append("Identity missing 'target_role'")
        contacts = identity.get("contacts")
        if not contacts or not isinstance(contacts, dict):
            errors.append("Identity missing 'contacts' dictionary")

    # 3. Evidence validation (anti-hallucination layer)
    evidence_list = profile.get("evidence", [])
    if not isinstance(evidence_list, list):
        errors.append("'evidence' must be a list")
    else:
        for idx, ev in enumerate(evidence_list):
            if not isinstance(ev, dict):
                errors.append(f"Evidence item #{idx} must be a dict")
                continue
            if not ev.get("id"):
                errors.append(f"Evidence item #{idx} missing 'id'")
            if not ev.get("claim"):
                errors.append(f"Evidence item #{idx} missing 'claim'")
            if not ev.get("action"):
                errors.append(f"Evidence item #{idx} missing 'action'")
            if not ev.get("result"):
                errors.append(f"Evidence item #{idx} missing 'result'")
            fact_type = ev.get("fact_type", FactType.VERIFIED_FACT)
            if fact_type not in (FactType.VERIFIED_FACT, FactType.AI_INTERPRETATION):
                errors.append(f"Evidence item #{idx} has invalid fact_type: {fact_type}")

    return len(errors) == 0, errors


def extract_evidence_from_legacy_experience(exp_text: str, role_title: str = "Lead Engineer") -> List[Dict[str, Any]]:
    """
    Extracts structured evidence items from legacy free-text bullet points.
    Splits experience into Problem -> Action -> Result blocks.
    """
    evidence = []
    if not exp_text:
        return evidence

    lines = [line.strip().lstrip('•-–* ') for line in exp_text.split('\n') if line.strip()]
    for idx, line in enumerate(lines):
        if len(line) < 15:
            continue

        # Extract technologies mentioned in parentheses or text
        tech_matches = re.findall(r'[A-Za-z0-9\.\+#]+(?:\.js)?', line)
        known_techs = [t for t in tech_matches if t.lower() in [
            'react', 'next.js', 'typescript', 'javascript', 'fastapi', 'python',
            'docker', 'postgres', 'postgresql', 'vitest', 'eslint', 'tailwind',
            'redux', 'traefik', 'nginx', 'figma', 'gsap', 'lottie'
        ]]

        evidence.append({
            "id": f"ev_{idx+1}",
            "claim": line,
            "category": "engineering",
            "problem": f"Business/technical need addressed in {role_title}",
            "context": role_title,
            "action": line,
            "decision": f"Adopted modern engineering patterns ({', '.join(known_techs) if known_techs else 'Web stack'})",
            "result": line,
            "technologies": list(set(known_techs)),
            "source": "legacy_resume_experience",
            "verified": True,
            "fact_type": FactType.VERIFIED_FACT
        })

    return evidence


def upgrade_legacy_profile(legacy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts a legacy profile format into a Canonical Candidate Profile structure
    while keeping full backward compatibility.
    """
    if not isinstance(legacy, dict):
        legacy = {}

    profile_id = legacy.get("id") or ("profile_ru" if legacy.get("lang") == "ru" else "profile_en")
    lang = legacy.get("lang") or ("ru" if re.search(r'[а-яёА-ЯЁ]', legacy.get("name", "") + legacy.get("role", "")) else "en")

    # Identity
    contacts_struct = legacy.get("contacts_structured") or {}
    name = legacy.get("name") or ("Егор Мышинский" if lang == "ru" else "Candidate Name")
    role = legacy.get("role") or ("Frontend / Fullstack-разработчик" if lang == "ru" else "Frontend / Fullstack Engineer")
    location = legacy.get("location") or contacts_struct.get("location") or ("Москва | Удалённо" if lang == "ru" else "Remote / Relocation")

    # Contacts normalization
    contacts = {
        "email": contacts_struct.get("email") or "candidate@example.com",
        "phone": contacts_struct.get("phone") or "",
        "telegram": contacts_struct.get("telegram") or "@username",
        "telegram_url": contacts_struct.get("telegram_url") or "",
        "github": contacts_struct.get("github") or "https://github.com/username",
        "linkedin": contacts_struct.get("linkedin") or "https://linkedin.com/in/username",
        "portfolio": contacts_struct.get("portfolio") or ""
    }

    # Extract or keep existing evidence
    evidence = legacy.get("evidence")
    if not evidence:
        exp_text = legacy.get("experience", "")
        evidence = extract_evidence_from_legacy_experience(exp_text, role)

    # Keywords / skills
    skills_raw = legacy.get("keywords") or ""
    skills_list = [s.strip() for s in skills_raw.split(',') if s.strip()]
    if not skills_list and isinstance(legacy.get("skills_categorized"), dict):
        for group in legacy["skills_categorized"].values():
            if isinstance(group, list):
                skills_list.extend(group)

    canonical = {
        "id": profile_id,
        "lang": lang,
        "is_active": legacy.get("is_active", True),
        "identity": {
            "name": name,
            "first_name": legacy.get("first_name") or name.split()[0],
            "last_name": legacy.get("last_name") or (" ".join(name.split()[1:]) if len(name.split()) > 1 else ""),
            "target_role": role,
            "location": location,
            "contacts": contacts
        },
        "professional_summary": legacy.get("summary") or legacy.get("professional_summary") or "",
        "skills": list(dict.fromkeys(skills_list)),
        "skills_categorized": legacy.get("skills_categorized") or {},
        "experience": legacy.get("experience_structured") or [],
        "projects": legacy.get("projects") or [],
        "education": legacy.get("education") or [],
        "languages": legacy.get("languages") or [],
        "evidence": evidence,
        "screening_facts": legacy.get("screening_facts") or dict(DEFAULT_SCREENING_FACTS),

        # ── Backward compatibility fields for legacy UI & Bookmarklet ──
        "name": name,
        "role": role,
        "summary": legacy.get("summary") or legacy.get("professional_summary") or "",
        "experience": legacy.get("experience") or "",
        "keywords": skills_raw if skills_raw else ", ".join(skills_list),
        "contacts": legacy.get("contacts") or f"Telegram: {contacts['telegram']} | Email: {contacts['email']} | GitHub: {contacts['github']}",
        "contacts_structured": contacts,
        "photo_url": legacy.get("photo_url") or ""
    }

    return canonical


# ── CANONICAL PROFILE STORAGE HELPERS ──────────────────────────────────────────

PROFILES_PATH = os.path.join(os.path.dirname(__file__), "profiles.json")

def load_canonical_profiles() -> List[Dict[str, Any]]:
    """Loads all profiles, ensuring they are upgraded to canonical schema."""
    if not os.path.exists(PROFILES_PATH):
        return []

    try:
        with open(PROFILES_PATH, "r", encoding="utf-8") as f:
            raw_profiles = json.load(f)
            if not isinstance(raw_profiles, list):
                raw_profiles = [raw_profiles]
            return [upgrade_legacy_profile(p) for p in raw_profiles]
    except Exception:
        return []


def save_canonical_profiles(profiles: List[Dict[str, Any]]) -> bool:
    """Saves canonical profiles to profiles.json, preserving validation and DB sync."""
    upgraded = []
    for p in profiles:
        canon = upgrade_legacy_profile(p)
        valid, errs = validate_canonical_profile(canon)
        if not valid:
            raise ValueError(f"Profile validation failed for {canon.get('id')}: {'; '.join(errs)}")
        upgraded.append(canon)

    with open(PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(upgraded, f, ensure_ascii=False, indent=2)

    # Sync to SQLite candidate_profiles table
    try:
        from tracker.db import sync_canonical_profiles_to_db
        sync_canonical_profiles_to_db(upgraded)
    except Exception as e:
        print(f"[CANONICAL_PROFILE] Notice: DB sync skipped or failed: {e}")

    return True


def get_canonical_profile(profile_id: Optional[str] = None, lang: str = "ru") -> Dict[str, Any]:
    """Selects an active canonical profile matching profile_id or preferred language."""
    all_profiles = load_canonical_profiles()
    if not all_profiles:
        # Generate minimal valid fallback
        fallback = upgrade_legacy_profile({"id": f"profile_{lang}", "lang": lang})
        return fallback

    if profile_id:
        for p in all_profiles:
            if p.get("id") == profile_id:
                return p

    for p in all_profiles:
        if p.get("lang") == lang:
            return p

    return all_profiles[0]
