// ==========================================
// Job Hunter CRM — Modals & System Views
// ==========================================

function toggleModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('active');
}

async function loadConfig() {
    try {
        const data = await api.getConfig();
        const keyInput = document.getElementById('gemini-key');
        if (keyInput) keyInput.value = data.gemini_api_key || '';
        activeProfileId = data.active_profile_id || null;
        renderActiveProfileDropdown();
    } catch (e) {
        console.error("Error loading config", e);
    }
}

async function saveConfig() {
    const key = document.getElementById('gemini-key')?.value.trim() || '';
    await api.saveConfig({ gemini_api_key: key, active_profile_id: activeProfileId });
    toggleModal('settings-modal');
    showToast('⚙️ Настройки сохранены');
}

let terminalVisible = false;
function toggleTerminalLogs() {
    terminalVisible = !terminalVisible;
    const container = document.getElementById('terminal-container');
    const text = document.getElementById('toggle-logs-text');
    const arrow = document.getElementById('toggle-logs-arrow');
    if (container) {
        if (terminalVisible) {
            container.classList.remove('hidden');
            if (text) text.innerText = 'Скрыть лог терминала';
            if (arrow) arrow.innerText = '▲';
            const logs = document.getElementById('harvest-logs');
            if (logs) logs.scrollTop = logs.scrollHeight;
        } else {
            container.classList.add('hidden');
            if (text) text.innerText = 'Показать подробный лог терминала';
            if (arrow) arrow.innerText = '▼';
        }
    }
}

async function startHarvest() {
    const logs = document.getElementById('harvest-logs');
    const btn = document.getElementById('harvest-close-btn');
    const pBar = document.getElementById('harvest-progress-bar');
    const pText = document.getElementById('harvest-percent');
    const pStep = document.getElementById('harvest-current-step');

    // Reset modal UI
    if (logs) logs.innerText = '🚀 Запуск сборщика вакансий...\n';
    if (btn) btn.classList.add('hidden');
    if (pBar) {
        pBar.style.width = '15%';
        pBar.className = 'bg-gradient-to-r from-indigo-500 via-sky-500 to-emerald-500 h-2 rounded-full transition-all duration-700 animate-pulse';
    }
    if (pText) pText.innerText = '15%';
    if (pStep) pStep.innerText = 'Подключение к источникам (HH, SuperJob, Rabota, TG, RemoteOK)...';

    toggleModal('harvest-modal');

    // Progress animation while background harvest runs
    let currentProg = 15;
    const progressInterval = setInterval(() => {
        if (currentProg < 88) {
            currentProg += Math.floor(Math.random() * 10) + 4;
            if (currentProg > 88) currentProg = 88;
            if (pBar) pBar.style.width = currentProg + '%';
            if (pText) pText.innerText = currentProg + '%';
            if (currentProg > 35 && currentProg <= 65) {
                if (pStep) pStep.innerText = 'Анти-BS фильтрация, отсеивание рекламы и кандидатов...';
            } else if (currentProg > 65) {
                if (pStep) pStep.innerText = 'Расчет грейдов (Junior-Lead) и сопоставление со стеком...';
            }
        }
    }, 1200);

    try {
        const res = await api.startHarvest();
        const data = await res.json();
        clearInterval(progressInterval);

        if (pBar) {
            pBar.style.width = '100%';
            pBar.classList.remove('animate-pulse');
        }
        if (pText) pText.innerText = '100%';
        if (pStep) pStep.innerHTML = '<span class="text-emerald-400 font-bold">✨ Сбор завершен успешно!</span>';

        if (logs) {
            logs.innerText += (data.logs || data.error || 'Готово.') + '\n\n🏁 Процесс завершен.';
            logs.scrollTop = logs.scrollHeight;
        }
    } catch (e) {
        clearInterval(progressInterval);
        if (pStep) pStep.innerHTML = '<span class="text-rose-400 font-bold">❌ Ошибка сбора</span>';
        if (logs) {
            logs.innerText += '\n❌ Ошибка соединения с сервером: ' + e;
            logs.scrollTop = logs.scrollHeight;
        }
    }

    if (btn) {
        btn.classList.remove('hidden');
        btn.classList.add('animate-bounce');
        setTimeout(() => btn.classList.remove('animate-bounce'), 3500);
    }
}

function closeHarvest() {
    toggleModal('harvest-modal');
    loadPitches();
}

// --- UNIVERSAL AI VACANCY PARSER ---
let aiParseMode = 'url';

function setAiParseMode(mode) {
    aiParseMode = mode;
    const tabUrl = document.getElementById('ai-tab-url');
    const tabText = document.getElementById('ai-tab-text');
    const boxUrl = document.getElementById('ai-input-url-container');
    const boxText = document.getElementById('ai-input-text-container');
    const err = document.getElementById('ai-parse-error');
    if (err) err.classList.add('hidden');

    if (mode === 'url') {
        if (tabUrl) tabUrl.className = 'flex-1 py-1.5 text-xs font-semibold rounded-lg bg-purple-600 text-white transition-all flex items-center justify-center gap-1.5';
        if (tabText) tabText.className = 'flex-1 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 rounded-lg transition-all flex items-center justify-center gap-1.5';
        if (boxUrl) boxUrl.classList.remove('hidden');
        if (boxText) boxText.classList.add('hidden');
    } else {
        if (tabText) tabText.className = 'flex-1 py-1.5 text-xs font-semibold rounded-lg bg-purple-600 text-white transition-all flex items-center justify-center gap-1.5';
        if (tabUrl) tabUrl.className = 'flex-1 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 rounded-lg transition-all flex items-center justify-center gap-1.5';
        if (boxText) boxText.classList.remove('hidden');
        if (boxUrl) boxUrl.classList.add('hidden');
    }
}

async function executeAiParse() {
    const urlInput = document.getElementById('ai-input-url');
    const textInput = document.getElementById('ai-input-text');
    const loader = document.getElementById('ai-parse-loader');
    const errBox = document.getElementById('ai-parse-error');
    const errMsg = document.getElementById('ai-parse-error-msg');
    const submitBtn = document.getElementById('ai-parse-submit-btn');

    if (errBox) errBox.classList.add('hidden');

    const rawVal = aiParseMode === 'url' ? (urlInput?.value || '').trim() : (textInput?.value || '').trim();
    if (!rawVal) {
        if (errMsg) errMsg.innerText = aiParseMode === 'url' ? 'Пожалуйста, введите корректный URL вакансии' : 'Пожалуйста, вставьте текст вакансии';
        if (errBox) errBox.classList.remove('hidden');
        return;
    }

    if (loader) loader.classList.remove('hidden');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
    }

    try {
        const data = await api.parseVacancyAi({
            input: rawVal,
            is_url: aiParseMode === 'url',
            profile_id: activeProfileId
        });

        if (!data.success) {
            throw new Error(data.error || 'Не удалось распознать вакансию через ИИ');
        }

        // Success: clear inputs, close modal, reload pitches
        if (urlInput) urlInput.value = '';
        if (textInput) textInput.value = '';
        toggleModal('ai-parser-modal');

        // Switch to inbox and refresh list
        setTab('inbox');
        await loadPitches();
        showToast('✨ Вакансия успешно распознана и добавлена!');

    } catch (err) {
        if (errMsg) errMsg.innerText = err.message || 'Ошибка обработки вакансии';
        if (errBox) errBox.classList.remove('hidden');
    } finally {
        if (loader) loader.classList.add('hidden');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }
}
