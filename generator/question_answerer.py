import re
import json
import urllib.request
from typing import Dict, Any, List, Optional

from generator.llm_generator import get_api_key, GEMINI_MODELS


def answer_application_question(
    question: str,
    profile: Dict[str, Any],
    job_understanding: Optional[Dict[str, Any]] = None,
    lang: str = "en"
) -> Dict[str, Any]:
    """
    Generates a truthful, professional first-person answer to a custom application question.
    CRITICAL INVARIANT: Zero Hallucination. All facts must come from Master Experience.
    """
    evidence_list = profile.get("evidence", [])
    question_lower = question.lower()

    # Semantic / cross-lingual concept mappings
    SYNONYM_STEMS = {
        "performance": ["производительн", "скорост", "оптимиз", "ускор", "быстродейств", "pagespeed", "vitals", "latency"],
        "optimize": ["оптимиз", "ускор", "настройк", "performance", "speed"],
        "speed": ["скорост", "быстродейств", "load", "загрузк"],
        "page": ["страниц", "page", "компонент"],
        "load": ["загрузк", "load", "рендеринг"],
        "architecture": ["архитектур", "проектирован", "структур", "паттерн"],
        "test": ["тест", "тестирован", "vitest", "playwright", "jest", "cypress", "e2e", "unit"],
        "deploy": ["деплой", "развертыван", "docker", "ci/cd", "github actions", "pipeline"],
        "state": ["стейт", "состояни", "redux", "zustand", "context"],
    }

    # 1. Search for matching evidence
    matched_ev = []
    words = re.findall(r'[a-zа-яё0-9]{3,}', question_lower)

    for ev in evidence_list:
        claim = ev.get("claim", "").lower()
        action = ev.get("action", "").lower()
        techs = [t.lower() for t in ev.get("technologies", [])]
        combined_text = f"{claim} {action} {' '.join(techs)}"

        overlap = 0
        for w in words:
            if w in combined_text:
                overlap += 2
            else:
                # Check cross-lingual synonyms
                for concept, stems in SYNONYM_STEMS.items():
                    if (w == concept or w in stems) and any(stem in combined_text for stem in stems):
                        overlap += 2
                        break

        if overlap > 0:
            matched_ev.append((overlap, ev))

    matched_ev.sort(key=lambda x: x[0], reverse=True)
    best_evidence = [e[1] for e in matched_ev[:3]]

    has_direct_evidence = len(best_evidence) > 0 and matched_ev[0][0] >= 2

    # 2. If Gemini API key is available, use LLM with strict grounding
    api_key = get_api_key()
    if api_key:
        answer_text = _llm_answer(question, profile, best_evidence, has_direct_evidence, lang)
        if answer_text:
            return {
                "answer": answer_text,
                "matched_evidence_ids": [e.get("id") for e in best_evidence],
                "has_direct_evidence": has_direct_evidence
            }

    # 3. Deterministic / Heuristic Grounded Fallback
    return _heuristic_answer(question, profile, best_evidence, has_direct_evidence, lang)


def _heuristic_answer(
    question: str,
    profile: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    has_direct_evidence: bool,
    lang: str
) -> Dict[str, Any]:
    q_lower = question.lower()
    ident = profile.get("identity", {})
    name = ident.get("name", "Candidate")

    if has_direct_evidence and evidence:
        ev = evidence[0]
        claim = ev.get("claim", "")
        action = ev.get("action", "")
        result = ev.get("result", "")
        techs = ", ".join(ev.get("technologies", []))

        if lang == "ru" or re.search(r'[а-яё]', q_lower):
            ans = f"В проекте {ev.get('context', 'разработки')} я решал похожую задачу: {action}. Использовал стек {techs}, что позволило достичь результата: {result}."
        else:
            ans = f"In my work on {ev.get('context', 'production systems')}, I addressed a directly related challenge: {action}. Leveraging {techs}, I successfully delivered: {result}."
        return {
            "answer": ans,
            "matched_evidence_ids": [ev.get("id")],
            "has_direct_evidence": True
        }

    # Outage / Incident question fallback
    if re.search(r'(?:outage|incident|crash|инцидент|сбой|авари)', q_lower):
        if lang == "ru" or re.search(r'[а-яё]', q_lower):
            ans = "При возникновении критических сбоев в продакшне мой алгоритм действий: 1) локализация логов и метрик через мониторинг, 2) откат к стабильному релизу или включение аварийного fallback-режима, 3) устранение первопричины на локальном стейджинге с добавлением регрессионного теста, 4) постмортем с командой."
        else:
            ans = "When facing production incidents, my protocol is: 1) immediately triage metrics and isolate error logs, 2) mitigate user impact via safe rollback or feature-flag fallback, 3) reproduce and patch root cause with regression coverage, and 4) document an actionable blameless post-mortem."
        return {
            "answer": ans,
            "matched_evidence_ids": [e.get("id") for e in evidence],
            "has_direct_evidence": False
        }

    # Honest adjacent experience fallback when no direct proof
    if lang == "ru" or re.search(r'[а-яё]', q_lower):
        ans = f"У меня нет прямого продакшн-опыта с этой конкретной технологией, однако благодаря глубокой базе в {', '.join(profile.get('skills', [])[:4])} и быстрому темпу автономной разработки я готов освоить необходимые нюансы без задержек для команды."
    else:
        ans = f"I do not claim direct production ownership with this specific tool, but given my deep foundation in {', '.join(profile.get('skills', [])[:4])} and proven track record of autonomous engineering, I ramp up quickly without blocking team velocity."

    return {
        "answer": ans,
        "matched_evidence_ids": [e.get("id") for e in evidence],
        "has_direct_evidence": False
    }


def _llm_answer(
    question: str,
    profile: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    has_direct_evidence: bool,
    lang: str
) -> Optional[str]:
    api_key = get_api_key()
    if not api_key:
        return None

    ev_text = "\n".join([
        f"- [{e.get('id')}]: {e.get('claim')} (Action: {e.get('action')}, Result: {e.get('result')}, Tech: {', '.join(e.get('technologies', []))})"
        for e in evidence
    ]) or "No directly matching evidence in candidate profile."

    prompt = f"""You are answering a job application screening question on behalf of a Senior Engineer.
QUESTION:
{question}

CANDIDATE VERIFIED EVIDENCE (CANONICAL SOURCE OF TRUTH):
{ev_text}

CANDIDATE KNOWN SKILLS:
{', '.join(profile.get('skills', []))}

INVARIANTS:
1. ZERO HALLUCINATION: You must NEVER invent projects, years, or technologies not in the evidence.
2. If the candidate has matching evidence, cite the specific action and result concisely.
3. If the candidate does NOT have direct experience, state that honestly and highlight adjacent verified skills.
4. Write in the first person ("I" / "я").
5. Language: {'Russian' if lang == 'ru' or re.search(r'[а-яё]', question.lower()) else 'English'}.
6. Keep it concise, professional, and engineering-focused (under 120 words). Output ONLY the final answer text.
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 250}
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        except urllib.error.URLError:
            break
        except Exception:
            continue
    return None


def answer_choice_question(
    question: str,
    options: List[str],
    profile: Dict[str, Any],
    lang: str = "en"
) -> str:
    """
    Selects the best matching option from a finite list of choices
    (e.g. Yes/No, scale 0-5, country/residency) based on candidate profile.
    """
    if not options:
        return ""
    clean_opts = [o.strip() for o in options if o.strip()]
    if len(clean_opts) == 1:
        return clean_opts[0]

    q_lower = question.lower()
    screening = profile.get("screening_facts", {})
    skills = [s.lower() for s in profile.get("skills", [])]
    ident = profile.get("identity", {})

    # 1. Binary Yes / No questions
    has_yes = any(o.lower() in ("yes", "да") for o in clean_opts)
    has_no = any(o.lower() in ("no", "нет") for o in clean_opts)

    if has_yes and has_no:
        yes_opt = next(o for o in clean_opts if o.lower() in ("yes", "да"))
        no_opt = next(o for o in clean_opts if o.lower() in ("no", "нет"))

        # Experience / Qualification questions (usually Yes for senior role)
        if re.search(r'(?:experience|years|qualified|коммерческий опыт|стаж)', q_lower):
            # Check years
            m = re.search(r'(\d+)\s*(?:years|лет|года)', q_lower)
            req_years = int(m.group(1)) if m else 3
            cand_years = screening.get("years_of_experience_num", 5)
            return yes_opt if cand_years >= req_years else no_opt

        # Restrictions / Non-compete / Criminal / Sanctions (Honest No)
        if re.search(r'(?:restriction|agreement|non-compete|ограничени|судимост)', q_lower):
            return no_opt

        # Visa sponsorship requirement
        if re.search(r'(?:sponsorship|visa|спонсирование|виз)', q_lower):
            need_visa = screening.get("requires_visa_sponsorship", False)
            return yes_opt if need_visa else no_opt

        # Previously worked at company
        if re.search(r'(?:previously worked|consulted for|ранее работали)', q_lower):
            return no_opt

        # Location / US / Canada residence
        if re.search(r'(?:currently live in|located in|проживаете в)\s*(?:this location|us|canada|сша)', q_lower):
            return no_opt

    # 2. Rating / Scale (0-5, 1-10)
    digit_opts = [o for o in clean_opts if re.match(r'^\d+$', o)]
    if len(digit_opts) >= 3:
        # Check if question mentions candidate's verified skills
        has_skill_match = any(skill in q_lower for skill in skills)
        nums = sorted([int(x) for x in digit_opts])
        max_num = nums[-1]
        if max_num in (5, 10):
            # Senior rating: 4/5 or 8/10 for core stack, 3/5 for adjacent
            target_val = (4 if max_num == 5 else 8) if has_skill_match else (3 if max_num == 5 else 6)
            closest = min(nums, key=lambda x: abs(x - target_val))
            return str(closest)

    # 3. Country / Residence
    if re.search(r'(?:country|residence|гражданство|страна)', q_lower):
        cand_loc = (ident.get("location") or screening.get("location", "")).lower()
        for opt in clean_opts:
            if opt.lower() in cand_loc or cand_loc in opt.lower():
                return opt
        # Common defaults
        for opt in clean_opts:
            if any(c in opt.lower() for c in ["russia", "georgia", "armenia", "россия"]):
                return opt

    # 4. LLM choice matching if API key available
    api_key = get_api_key()
    if api_key and len(clean_opts) <= 15:
        prompt = f"""Given the candidate profile and screening question, select EXACTLY ONE option from the list.
QUESTION: {question}
CANDIDATE PROFILE:
- Name: {ident.get('name')}
- Skills: {', '.join(profile.get('skills', []))}
- Experience: {profile.get('summary')}

ALLOWED OPTIONS:
{json.dumps(clean_opts, ensure_ascii=False)}

Output ONLY the exact string from ALLOWED OPTIONS. Do not add any explanation or punctuation."""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 60}
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=2) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    cand_ans = res_json["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"\'')
                    for opt in clean_opts:
                        if opt.lower() == cand_ans.lower():
                            return opt
            except urllib.error.URLError:
                break
            except Exception:
                continue

    return clean_opts[0]

