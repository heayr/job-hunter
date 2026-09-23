import re

with open("generator/llm_generator.py", "r") as f:
    content = f.read()

# Replace _sanitize_text definition
new_sanitize = """def _sanitize_text(text: str, custom_stop_phrases: list = None) -> str:
    \"\"\"Anti-BS & Anti-Bullet sanitizer.\"\"\"
    # Remove bullets
    text = re.sub(r'(?m)^[\s]*[-*•]\s*', '', text)
    text = re.sub(r'(?m)^[\s]*\d+\.\s*', '', text)
    # Remove cliches
    cliches = [
        r"(?i)буду рад(а)? внести (свой )?вклад",
        r"(?i)динамично развивающ\w+ компани",
        r"(?i)ознакомился с (вашей )?вакансией",
        r"(?i)с большим интересом прочитал",
        r"(?i)могу принести пользу",
        r"(?i)нацелен(а)? на результат"
    ]
    if custom_stop_phrases:
        for p in custom_stop_phrases:
            if len(p) > 2:
                # Escape and make case insensitive regex
                cliches.append(r"(?i)" + re.escape(p))
                
    for c in cliches:
        text = re.sub(c, "", text)
    # Clean double spaces or broken lines caused by removals
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

def _sanitize_short_dm(dm: str, custom_stop_phrases: list = None) -> str:
    return _sanitize_text(dm, custom_stop_phrases)"""

content = re.sub(r'def _sanitize_text.*?return text\n\ndef _sanitize_short_dm\(dm: str\) -> str:\n    return _sanitize_text\(dm\)', new_sanitize, content, flags=re.DOTALL)

# Add stop_phrases logic to generate_ai_pitch
# Replace `cfg = get_llm_config()` with reading `stop_phrases` as well
content = content.replace(
    'cfg = get_llm_config()',
    'cfg = get_llm_config()\n    stop_phrases = cfg.get("stop_phrases", [])\n    stop_phrases_text = ", ".join(stop_phrases) if stop_phrases else ""'
)

# Update prompt injection
prompt_append = r"""
ПОЛНЫЙ ЗАПРЕТ НА "ИИ-СТИЛЬ":
- Никаких маркированных списков (bullet points)! Пиши сплошными абзацами.
- Никаких штампов ("динамично развивающаяся", "буду рад внести вклад", "ознакомился с вакансией").
- Тон: уверенный, сухой, профессионально-разговорный (инженер пишет инженеру).
"""
prompt_replace = r"""
ПОЛНЫЙ ЗАПРЕТ НА "ИИ-СТИЛЬ":
- Никаких маркированных списков (bullet points)! Пиши сплошными абзацами.
- Никаких штампов ("динамично развивающаяся", "буду рад внести вклад", "ознакомился с вакансией").
{f"- ДОПОЛНИТЕЛЬНЫЙ ЗАПРЕТ НА СЛОВА (не используй их): {stop_phrases_text}" if stop_phrases_text else ""}
- Тон: уверенный, сухой, профессионально-разговорный (инженер пишет инженеру).
"""
content = content.replace(prompt_append, prompt_replace)

# Update all calls to _sanitize_text and _sanitize_short_dm
content = content.replace(
    '_sanitize_short_dm((parsed.get("short_dm") or "").strip())',
    '_sanitize_short_dm((parsed.get("short_dm") or "").strip(), stop_phrases)'
)
content = content.replace(
    '_sanitize_short_dm(parsed.get("short_dm", "").strip())',
    '_sanitize_short_dm(parsed.get("short_dm", "").strip(), stop_phrases)'
)
content = content.replace(
    '_sanitize_text((parsed.get("cover_letter") or "").strip())',
    '_sanitize_text((parsed.get("cover_letter") or "").strip(), stop_phrases)'
)
content = content.replace(
    '_sanitize_text(parsed.get("cover_letter", "").strip())',
    '_sanitize_text(parsed.get("cover_letter", "").strip(), stop_phrases)'
)

with open("generator/llm_generator.py", "w") as f:
    f.write(content)

