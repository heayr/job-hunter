const DEFAULT_SYSTEM_PROMPT = `ТЫ — опытный IT-специалист и карьерный стратег. Твоя задача — писать короткие, пробивные и 100% конвертящие сопроводительные письма под конкретную вакансию.

КОНТЕКСТ РЫНКА (ПРАВИЛА ИГРЫ):
1. Все приукрашивают. Кандидат должен выглядеть максимально уверенным практиком с твердым релевантным бэкграундом (минимум 2+ года, уверенно адаптируй опыт под требования).
2. Эйчар тратит 5 секунд. Письмо должно цеплять с первого абзаца техническим сленгом ("изнанка", "под капотом", "логи", "контракты" — в зависимости от стека).

ПОЛНЫЙ ЗАПРЕТ НА "ИИ-СТИЛЬ":
- Никаких маркированных списков (bullet points)! Пиши сплошными абзацами.
- Никаких штампов ("динамично развивающаяся", "буду рад внести вклад", "ознакомился с вакансией").
- Тон: уверенный, сухой, профессионально-разговорный (инженер пишет инженеру).

{stop_phrases_block}

СТРУКТУРА:
1. Приветствие + Указание вакансии (например: Привет. Пишу по поводу вакансии {title} в {company}).
2. Крючок (1 абзац): Заявление релевантного опыта. Главный угол атаки: не просто "исполнитель по ТЗ", а человек, понимающий архитектуру и бизнес-задачу.
3. Мясо стека: Собрать главные требования из описания и вписать их в живую речь. Использовать сленг.
4. Короткий CTA + Контакты: {tg} | {email} | {github}

VACANCY: {title} at {company}
{desc}

PROFILE: {name}, {role}
{summary}
Keywords: {keywords}

{gold_examples_text}
{rejected_text}
`;

async function loadPromptEditor() {
    try {
        const config = await window.api.getConfig();
        const textarea = document.getElementById('prompt-editor-textarea');
        const tempSlider = document.getElementById('prompt-temperature');
        const tempVal = document.getElementById('prompt-temperature-val');
        
        if (config.system_prompt_template) {
            textarea.value = config.system_prompt_template;
        } else {
            textarea.value = DEFAULT_SYSTEM_PROMPT;
        }

        if (config.temperature !== undefined) {
            tempSlider.value = config.temperature;
            tempVal.innerText = parseFloat(config.temperature).toFixed(1);
        }
    } catch (err) {
        console.error('Failed to load prompt template', err);
    }
}

async function savePrompt() {
    const textarea = document.getElementById('prompt-editor-textarea');
    const tempSlider = document.getElementById('prompt-temperature');
    const val = textarea.value.trim();
    const temp = parseFloat(tempSlider.value);
    
    if (!val) {
        alert('Промпт не может быть пустым');
        return;
    }
    try {
        await window.api.saveConfig({ 
            system_prompt_template: val,
            temperature: temp
        });
        showToast('Промпт сохранен', 'success');
    } catch (err) {
        console.error('Failed to save prompt', err);
        showToast('Ошибка сохранения', 'error');
    }
}

async function resetPromptToDefault() {
    if (!confirm('Вернуть промпт по умолчанию? Все ваши изменения будут потеряны.')) return;
    const textarea = document.getElementById('prompt-editor-textarea');
    textarea.value = DEFAULT_SYSTEM_PROMPT;
    await savePrompt();
}
