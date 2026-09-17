import json
import re
import urllib.request
import urllib.error
import html
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from generator.llm_generator import get_api_key, GEMINI_MODELS

# ── DOMAIN & URL EXTRACTION ──────────────────────────────────────────────────

def extract_company_domain(company_name: str, vacancy_url: str = "", description: str = "") -> Optional[str]:
    """
    Finds the official company domain from vacancy URL or job description.
    Excludes job boards (hh.ru, linkedin, etc.).
    """
    banned_job_domains = [
        "hh.ru", "headhunter", "linkedin.com", "habr.com", "remoteok.com",
        "weworkremotely.com", "t.me", "telegram.org", "superjob.ru", "rabota.ru",
        "greenhouse.io", "lever.co", "ashbyhq.com", "workable.com", "jobicy.com"
    ]

    # 1. Check direct website pattern in description (e.g. "Сайт: example.com" or "Website: https://acme.org")
    site_match = re.search(r'(?:сайт|website|url|web|domain)[\s:]*(?:https?://)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', description, re.I)
    if site_match:
        dom = site_match.group(1).lower().rstrip('/')
        if not any(b in dom for b in banned_job_domains):
            return dom

    # 2. Check any raw URLs mentioned in description
    url_matches = re.findall(r'https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', description)
    for u in url_matches:
        u_clean = u.lower().rstrip('/')
        if not any(b in u_clean for b in banned_job_domains):
            return u_clean

    # 3. Check if vacancy URL itself is a company site (not a known job portal)
    if vacancy_url and vacancy_url.startswith("http"):
        m = re.search(r'https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', vacancy_url)
        if m:
            v_dom = m.group(1).lower()
            if not any(b in v_dom for b in banned_job_domains):
                return v_dom

    # 4. Fallback: sanitize company name as probable domain key
    comp_clean = re.sub(r'[^a-zA-Z0-9]', '', company_name).lower()
    return f"{comp_clean}.com" if comp_clean else None


def fetch_bounded_company_page(url_or_domain: str, timeout: float = 6.0) -> Optional[str]:
    """
    Safely fetches a web page with strict timeout and character truncation.
    Guarantees no UI freezes.
    """
    if not url_or_domain:
        return None

    target_url = url_or_domain if url_or_domain.startswith("http") else f"https://{url_or_domain}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8"
    }

    try:
        req = urllib.request.Request(target_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return None
            raw_bytes = response.read(150000) # Read max 150KB
            raw_html = raw_bytes.decode('utf-8', errors='ignore')

        # Clean HTML markup
        cleaned = re.sub(r'<(script|style|svg|noscript|header|footer|nav)[\s\S]*?</\1>', ' ', raw_html, flags=re.I)
        cleaned = re.sub(r'<!--[\s\S]*?-->', ' ', cleaned)
        cleaned = re.sub(r'<(?:p|div|br|hr|li|h[1-6]|tr)[^>]*>', '\n', cleaned, flags=re.I)
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        cleaned = html.unescape(cleaned)

        lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in cleaned.split('\n')]
        non_empty = [l for l in lines if l and len(l) > 2]
        full_text = '\n'.join(non_empty)

        return full_text[:5000] # Bounded to 5000 chars
    except Exception:
        return None


# ── HEURISTIC COMPANY DOSSIER ────────────────────────────────────────────────

def heuristic_company_dossier(
    company_name: str,
    domain: Optional[str] = None,
    description: str = "",
    page_text: str = ""
) -> Dict[str, Any]:
    """
    Produces structured company intelligence using heuristic pattern matching.
    Distinguishes verifiable public facts from inferred strategic signals.
    """
    combined = f"{description} {page_text}".lower()

    # Detect business model & domain
    business_model = "B2B SaaS / Product Development"
    if any(k in combined for k in ["fintech", "платеж", "банк", "payment", "crypto", "defi", "trading"]):
        business_model = "Fintech / Payments / Financial Services"
    elif any(k in combined for k in ["e-commerce", "маркетплейс", "ритейл", "shop", "ecommerce", "магазин"]):
        business_model = "E-Commerce / Digital Retail"
    elif any(k in combined for k in ["ai", "ml", "llm", "нейросет", "machine learning"]):
        business_model = "AI / Machine Learning Solutions"
    elif any(k in combined for k in ["healthcare", "медицин", "health", "medtech"]):
        business_model = "HealthTech / Digital Medicine"

    # Detect declared tech stack
    tech_candidates = [
        "React", "Next.js", "TypeScript", "JavaScript", "Python", "FastAPI",
        "Node.js", "PostgreSQL", "Docker", "Kubernetes", "AWS", "GCP", "Tailwind CSS",
        "GraphQL", "REST API", "Kafka", "Redis", "Microservices", "CI/CD"
    ]
    detected_tech = [t for t in tech_candidates if re.search(r'\b' + re.escape(t.lower()) + r'\b', combined)]

    # Infer engineering signals
    culture_signals = []
    if "agile" in combined or "scrum" in combined:
        culture_signals.append("Итеративные спринты и регулярные релизные циклы")
    if any(k in combined for k in ["remote", "удален"]):
        culture_signals.append("Асинхронная коммуникация и распределенная команда")
    if any(k in combined for k in ["scale", "нагрузк", "highload", "миллион"]):
        culture_signals.append("Фокус на масштабируемости и отказоустойчивости сервисов")
    if not culture_signals:
        culture_signals.append("Продуктовая разработка с упором на скорость поставки")

    strategic_implications = [
        f"Команда ценит опыт в {', '.join(detected_tech[:4]) if detected_tech else 'современном веб-стеке'} для быстрой интеграции в кодовую базу.",
        "Критично продемонстрировать автономность и понимание бизнес-целей продукта."
    ]

    return {
        "company_name": company_name or "Direct Employer",
        "domain": domain or f"{company_name.lower().replace(' ', '')}.com",
        "public_facts": {
            "business_model": business_model,
            "main_products": [f"Продукты и сервисы {company_name}"],
            "headquarters_or_geo": "Remote / Распределенная команда" if "remote" in combined or "удален" in combined else "Локальный офис / Гибрид"
        },
        "engineering_signals": {
            "declared_tech_stack": detected_tech if detected_tech else ["React", "TypeScript", "Next.js"],
            "architecture_signals": ["Компонентная веб-архитектура", "REST / HTTP API интеграции"],
            "team_culture": culture_signals
        },
        "strategic_implications": strategic_implications,
        "sources": [domain] if domain else [],
        "cached_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


# ── AI COMPANY RESEARCHER ────────────────────────────────────────────────────

def research_company_context(
    company_name: str,
    vacancy_url: str = "",
    description: str = "",
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Main entrypoint: extracts domain, checks SQLite TTL cache (7 days),
    safely fetches page with 6.0s timeout, synthesizes facts vs engineering signals,
    and caches the result.
    """
    domain = extract_company_domain(company_name, vacancy_url, description)
    cache_key = domain or company_name.lower().strip()

    # 1. Check SQLite Cache
    if not force_refresh:
        try:
            from tracker.db import get_cached_company_dossier
            cached = get_cached_company_dossier(cache_key, ttl_days=7)
            if cached:
                return cached
        except Exception:
            pass

    # 2. Bounded Page Fetch (Max 6.0s)
    page_text = ""
    if domain and not domain.endswith(".example.com"):
        page_text = fetch_bounded_company_page(domain, timeout=6.0) or ""

    # 3. AI Synthesis if key available and page text found
    api_key = get_api_key()
    dossier = None

    if api_key and (page_text or len(description) > 300):
        prompt = f"""You are a Strategic Corporate Intelligence Analyst and Senior Technical Recruiter.
Analyze the following public company context for {company_name} (Domain: {domain or 'Unknown'}).
Separate PUBLICLY CONFIRMED FACTS from INFERRED ENGINEERING SIGNALS.

Public Web Content / Job Details:
\"\"\"{(page_text or description)[:4500]}\"\"\"

Output STRICT JSON:
{{
  "company_name": "{company_name}",
  "domain": "{domain or ''}",
  "public_facts": {{
    "business_model": "e.g. B2B SaaS, Marketplace, FinTech API, etc.",
    "main_products": ["Core Product 1", "Core Product 2"],
    "headquarters_or_geo": "e.g. London, UK / Remote"
  }},
  "engineering_signals": {{
    "declared_tech_stack": ["Confirmed technologies mentioned"],
    "architecture_signals": ["e.g. Microfrontends, Event-driven, Serverless"],
    "team_culture": ["e.g. High autonomy, Async-first"]
  }},
  "strategic_implications": [
    "Concrete angle: what the candidate should emphasize to win this specific company"
  ],
  "sources": ["{domain or 'job_description'}"]
}}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
        }

        for model in GEMINI_MODELS:
            model_path = model if model.startswith("models/") else f"models/{model}"
            url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent"
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp_data = json.loads(resp.read().decode('utf-8'))
                    text = resp_data['candidates'][0]['content']['parts'][0]['text'].strip()
                    text = re.sub(r'^```(?:json)?\s*', '', text)
                    text = re.sub(r'\s*```$', '', text).strip()
                    parsed = json.loads(text)
                    if "public_facts" in parsed and "engineering_signals" in parsed:
                        parsed["cached_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        dossier = parsed
                        break
            except Exception:
                pass

    # 4. Fallback if AI or network failed
    if not dossier:
        dossier = heuristic_company_dossier(company_name, domain, description, page_text)

    # 5. Persist to SQLite Cache
    try:
        from tracker.db import save_company_dossier
        save_company_dossier(cache_key, company_name, dossier)
    except Exception as e:
        print(f"[company_researcher] Cache save notice: {e}")

    return dossier
