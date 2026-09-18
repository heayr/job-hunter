// ==========================================
// Job Hunter CRM — Modals & System Views
// ==========================================

function toggleModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    
    // Auto-bind backdrop click to close if not already bound
    if (!el.dataset.backdropBound) {
        el.dataset.backdropBound = 'true';
        el.addEventListener('click', (e) => {
            if (e.target === el) {
                toggleModal(id);
            }
        });
    }

    el.classList.toggle('active');
}

// Global ESC key handler to close active modals
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const activeModals = document.querySelectorAll('.modal.active');
        activeModals.forEach(m => m.classList.remove('active'));
    }
});

let currentLlmProvider = 'gemini';

function setLlmProvider(provider) {
    currentLlmProvider = provider;
    const btnGemini = document.getElementById('provider-btn-gemini');
    const btnLm = document.getElementById('provider-btn-lm_studio');
    const blockGemini = document.getElementById('llm-block-gemini');
    const blockLm = document.getElementById('llm-block-lm_studio');

    if (provider === 'lm_studio') {
        btnLm.className = 'p-2 rounded-lg border border-purple-500 bg-purple-950/40 text-left transition-colors';
        btnGemini.className = 'p-2 rounded-lg border border-slate-700 bg-slate-900/60 text-left hover:border-slate-600 transition-colors';
        blockLm.classList.remove('hidden');
        blockGemini.classList.add('hidden');
    } else {
        btnGemini.className = 'p-2 rounded-lg border border-sky-500 bg-sky-950/40 text-left transition-colors';
        btnLm.className = 'p-2 rounded-lg border border-slate-700 bg-slate-900/60 text-left hover:border-slate-600 transition-colors';
        blockGemini.classList.remove('hidden');
        blockLm.classList.add('hidden');
    }
}

async function loadConfig() {
    try {
        const data = await api.getConfig();
        const keyInput = document.getElementById('gemini-key');
        if (keyInput) {
            if (data.has_gemini_key) {
                keyInput.placeholder = '●●●●●●●● (Ключ сохранен на сервере)';
                keyInput.value = data.gemini_api_key || '';
            } else {
                keyInput.placeholder = 'AIzaSy...';
                keyInput.value = '';
            }
        }

        const lmUrlInput = document.getElementById('lm-studio-url');
        if (lmUrlInput) lmUrlInput.value = data.lm_studio_url || 'http://127.0.0.1:1234/v1';

        setLlmProvider(data.llm_provider || 'gemini');
        
        const senCheck = document.getElementById('setting-seniority-alignment');
        if (senCheck) senCheck.checked = data.seniority_alignment !== false;

        const hlCheck = document.getElementById('setting-highload-guardrail');
        if (hlCheck) hlCheck.checked = data.highload_guardrail !== false;

        // Policy settings
        const salRub = document.getElementById('setting-min-salary-rub');
        if (salRub) salRub.value = data.policy_min_salary_rub !== undefined ? data.policy_min_salary_rub : 80000;

        const salUsd = document.getElementById('setting-min-salary-usd');
        if (salUsd) salUsd.value = data.policy_min_salary_usd !== undefined ? data.policy_min_salary_usd : 2000;

        const dailyLim = document.getElementById('setting-daily-limit');
        if (dailyLim) dailyLim.value = data.policy_daily_limit !== undefined ? data.policy_daily_limit : 25;

        const remOnly = document.getElementById('setting-remote-only');
        if (remOnly) remOnly.checked = data.policy_remote_only === true;

        activeProfileId = data.active_profile_id || null;
        renderActiveProfileDropdown();
    } catch (e) {
        console.error("Error loading config", e);
    }
}

async function saveConfig() {
    const key = document.getElementById('gemini-key')?.value.trim() || '';
    const lmUrl = document.getElementById('lm-studio-url')?.value.trim() || 'http://127.0.0.1:1234/v1';
    const seniorityAlignment = document.getElementById('setting-seniority-alignment')?.checked ?? true;
    const highloadGuardrail = document.getElementById('setting-highload-guardrail')?.checked ?? true;

    const salRub = parseInt(document.getElementById('setting-min-salary-rub')?.value || '80000', 10);
    const salUsd = parseInt(document.getElementById('setting-min-salary-usd')?.value || '2000', 10);
    const dailyLim = parseInt(document.getElementById('setting-daily-limit')?.value || '25', 10);
    const remOnly = document.getElementById('setting-remote-only')?.checked ?? false;

    const payload = {
        llm_provider: currentLlmProvider,
        lm_studio_url: lmUrl,
        active_profile_id: activeProfileId,
        seniority_alignment: seniorityAlignment,
        highload_guardrail: highloadGuardrail,
        policy_min_salary_rub: salRub,
        policy_min_salary_usd: salUsd,
        policy_daily_limit: dailyLim,
        policy_remote_only: remOnly
    };
    if (key && !key.includes('●')) {
        payload.gemini_api_key = key;
    }

    await api.saveConfig(payload);
    toggleModal('settings-modal');
    showToast('⚙️ Настройки и движок ИИ сохранены');
}

let terminalVisible = true;
function toggleTerminalLogs() {
    terminalVisible = !terminalVisible;
    const container = document.getElementById('terminal-container');
    const text = document.getElementById('toggle-logs-text');
    const arrow = document.getElementById('toggle-logs-arrow');
    if (container) {
        if (terminalVisible) {
            container.classList.remove('hidden');
            if (text) text.innerText = 'Лог терминала в реальном времени';
            if (arrow) arrow.innerText = '▲';
            const logs = document.getElementById('harvest-logs');
            if (logs) logs.scrollTop = logs.scrollHeight;
        } else {
            container.classList.add('hidden');
            if (text) text.innerText = 'Развернуть лог терминала';
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
    const metricScrapers = document.getElementById('harvest-metric-scrapers');
    const metricSaved = document.getElementById('harvest-metric-saved');
    const metricFiltered = document.getElementById('harvest-metric-filtered');
    const metricDups = document.getElementById('harvest-metric-dups');

    // Reset modal UI
    if (logs) {
        logs.innerText = '🚀 Запуск сборщика вакансий...\n';
        logs.scrollTop = logs.scrollHeight;
    }
    if (btn) btn.classList.add('hidden');
    if (pBar) {
        pBar.style.width = '3%';
        pBar.className = 'bg-gradient-to-r from-indigo-500 via-sky-500 to-emerald-500 h-2 rounded-full transition-all duration-300 animate-pulse';
    }
    if (pText) pText.innerText = '0%';
    if (pStep) pStep.innerText = 'Подключение к источникам...';
    if (metricScrapers) metricScrapers.innerText = '0 / 11';
    if (metricSaved) metricSaved.innerText = '0';
    if (metricFiltered) metricFiltered.innerText = '0';
    if (metricDups) metricDups.innerText = '0';

    toggleModal('harvest-modal');

    try {
        await api.startHarvest();
        
        // Start live polling (every 800ms for responsive streaming)
        const progressInterval = setInterval(async () => {
            try {
                const statusData = await api.getHarvestStatus();
                if (logs) {
                    logs.innerText = statusData.logs || 'Ожидание логов...';
                    logs.scrollTop = logs.scrollHeight;
                }
                
                const metrics = statusData.metrics || {};
                const step = metrics.step || 0;
                const total = metrics.total || 11;
                const saved = metrics.saved || 0;
                const filtered = metrics.filtered || 0;
                const dups = metrics.dups || 0;
                const scName = metrics.name || '';

                if (metricScrapers) metricScrapers.innerText = `${step} / ${total}`;
                if (metricSaved) metricSaved.innerText = saved;
                if (metricFiltered) metricFiltered.innerText = filtered;
                if (metricDups) metricDups.innerText = dups;

                // Accurate math-based percentage
                let currentProg = 3;
                if (total > 0 && step > 0) {
                    currentProg = Math.min(96, Math.round((step / total) * 90));
                }

                if (scName) {
                    if (scName === 'saving') {
                        if (pStep) pStep.innerHTML = `<span class="text-indigo-300">💾 Сохранение и оценка скоринга... (${saved} сохр.)</span>`;
                        currentProg = Math.max(currentProg, 92);
                    } else if (scName === 'completed') {
                        currentProg = 100;
                    } else {
                        if (pStep) pStep.innerHTML = `Сканирование: <span class="text-sky-300 font-bold">${scName}</span> [${step}/${total}]`;
                    }
                }

                if (pBar) pBar.style.width = currentProg + '%';
                if (pText) pText.innerText = currentProg + '%';
                
                if (!statusData.is_running && statusData.logs) {
                    clearInterval(progressInterval);
                    if (pBar) {
                        pBar.style.width = '100%';
                        pBar.classList.remove('animate-pulse');
                    }
                    if (pText) pText.innerText = '100%';
                    if (pStep) pStep.innerHTML = `<span class="text-emerald-400 font-bold">✨ Сбор завершен! Сохранено: ${saved} новых вакансий</span>`;
                    
                    if (btn) {
                        btn.classList.remove('hidden');
                        btn.classList.add('animate-bounce');
                        setTimeout(() => btn.classList.remove('animate-bounce'), 3500);
                    }

                    // Automatically refresh Inbox in background so user immediately sees fresh vacancies
                    try {
                        if (typeof loadPitches === 'function') {
                            await loadPitches();
                        }
                    } catch (loadErr) {
                        console.error("Auto reload pitches error:", loadErr);
                    }
                }
            } catch (pollErr) {
                console.error("Poll error:", pollErr);
            }
        }, 800);

    } catch (e) {
        if (pStep) pStep.innerHTML = '<span class="text-rose-400 font-bold">❌ Ошибка запуска</span>';
        if (logs) {
            logs.innerText += '\n❌ Ошибка соединения с сервером: ' + e;
            logs.scrollTop = logs.scrollHeight;
        }
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
