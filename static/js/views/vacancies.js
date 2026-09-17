// ==========================================
// Job Hunter CRM — Vacancies & Details View
// ==========================================

async function loadPitches() {
    try {
        vacancies = await api.getPitches();
        updateCounts();
        renderList();
        renderDetails();
    } catch (e) {
        console.error("Failed to load vacancies", e);
    }
}

function setMarket(market) {
    currentMarket = market;
    document.querySelectorAll('.market-btn').forEach(b => {
        b.classList.remove('active');
        b.classList.add('text-slate-400');
    });
    const btn = document.getElementById(`market-btn-${market}`);
    if (btn) {
        btn.classList.add('active');
        btn.classList.remove('text-slate-400');
    }

    // If current vacancy is filtered out, re-select
    const targetStatus = (currentTab === 'inbox') ? ['inbox', 'new'] : [currentTab];
    let filtered = vacancies.filter(v => targetStatus.includes(v.status));
    if (currentMarket === 'ru') {
        filtered = filtered.filter(v => (v.language || 'ru') === 'ru');
    } else if (currentMarket === 'en') {
        filtered = filtered.filter(v => v.language === 'en');
    }

    if (currentVac && !filtered.some(v => v.id === currentVac.id)) {
        currentVac = filtered.length > 0 ? filtered[0] : null;
    }

    renderList();
    renderDetails();
}

function setTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.remove('active', 'text-slate-400');
        if (b.id === `tab-${tab}`) {
            b.classList.add('active');
        } else if (b.id !== 'tab-profiles') {
            b.classList.add('text-slate-400');
        }
    });

    if (tab === 'profiles') {
        document.getElementById('main-view').classList.add('hidden');
        document.getElementById('profiles-view').classList.remove('hidden');
        loadProfilesList();
    } else {
        document.getElementById('main-view').classList.remove('hidden');
        document.getElementById('profiles-view').classList.add('hidden');
        currentVac = null;
        updateCounts();
        renderList();
        renderDetails();
    }
}

function updateCounts() {
    const statusFilter = (v, s) => (s === 'inbox') ? (v.status === 'inbox' || v.status === 'new') : (v.status === s);

    const countInbox = vacancies.filter(v => statusFilter(v, 'inbox')).length;
    const countSent = vacancies.filter(v => statusFilter(v, 'sent')).length;
    const countReplied = vacancies.filter(v => statusFilter(v, 'replied')).length;
    const countArchive = vacancies.filter(v => statusFilter(v, 'archive')).length;
    const countBlacklist = vacancies.filter(v => statusFilter(v, 'blacklist')).length;

    const elInbox = document.getElementById('count-inbox');
    if (elInbox) elInbox.innerText = countInbox;
    const elSent = document.getElementById('count-sent');
    if (elSent) elSent.innerText = countSent;
    const elReplied = document.getElementById('count-replied');
    if (elReplied) elReplied.innerText = countReplied;
    const elArchive = document.getElementById('count-archive');
    if (elArchive) elArchive.innerText = countArchive;
    const elBlacklist = document.getElementById('count-blacklist');
    if (elBlacklist) elBlacklist.innerText = countBlacklist;

    // Market counts for currently active tab
    const tabVacs = vacancies.filter(v => statusFilter(v, currentTab));
    const marketAll = tabVacs.length;
    const marketRu = tabVacs.filter(v => (v.language || 'ru') === 'ru').length;
    const marketEn = tabVacs.filter(v => v.language === 'en').length;

    const cAll = document.getElementById('market-count-all');
    if (cAll) cAll.innerText = marketAll;
    const cRu = document.getElementById('market-count-ru');
    if (cRu) cRu.innerText = marketRu;
    const cEn = document.getElementById('market-count-en');
    if (cEn) cEn.innerText = marketEn;

    // Analytics Totals
    const totalRu = vacancies.filter(v => (v.language || 'ru') === 'ru').length;
    const totalEn = vacancies.filter(v => v.language === 'en').length;

    const statTotal = document.getElementById('stat-total');
    if (statTotal) statTotal.innerText = vacancies.length;
    const statRu = document.getElementById('stat-ru');
    if (statRu) statRu.innerText = totalRu;
    const statEn = document.getElementById('stat-en');
    if (statEn) statEn.innerText = totalEn;
    const statSent = document.getElementById('stat-sent');
    if (statSent) statSent.innerText = countSent;
    const statReplied = document.getElementById('stat-replied');
    if (statReplied) statReplied.innerText = countReplied;

    const winRate = countSent > 0 ? Math.round((countReplied / countSent) * 100) : 0;
    const statWinrate = document.getElementById('stat-winrate');
    if (statWinrate) statWinrate.innerText = winRate + '%';
}

function toggleGradeFilter(grade) {
    const idx = filterGrades.indexOf(grade);
    if (idx >= 0) {
        filterGrades.splice(idx, 1);
    } else {
        filterGrades.push(grade);
    }
    updateFilterChipsUI();
    renderList();
    renderDetails();
}

function resetGradeFilters() {
    filterGrades = [];
    updateFilterChipsUI();
    renderList();
    renderDetails();
}

function toggleMatchFilter(tier) {
    const idx = filterMatches.indexOf(tier);
    if (idx >= 0) {
        filterMatches.splice(idx, 1);
    } else {
        filterMatches.push(tier);
    }
    updateFilterChipsUI();
    renderList();
    renderDetails();
}

function resetMatchFilters() {
    filterMatches = [];
    updateFilterChipsUI();
    renderList();
    renderDetails();
}

function updateFilterChipsUI() {
    const allGrades = ['Intern', 'Junior', 'Middle', 'Senior', 'Lead'];
    allGrades.forEach(g => {
        const btn = document.getElementById(`grade-chip-${g}`);
        if (!btn) return;
        if (filterGrades.includes(g)) {
            btn.className = 'grade-chip px-2 py-0.5 rounded text-[10px] font-semibold border border-indigo-500 bg-indigo-600/30 text-indigo-300 shadow-sm transition-all';
        } else {
            btn.className = 'grade-chip px-2 py-0.5 rounded text-[10px] font-medium border border-slate-800 bg-slate-900/90 text-slate-400 hover:border-slate-700 transition-all';
        }
    });

    const allMatches = ['80', '60', 'mixed'];
    allMatches.forEach(m => {
        const btn = document.getElementById(`match-chip-${m}`);
        if (!btn) return;
        if (filterMatches.includes(m)) {
            btn.className = 'match-chip px-2 py-0.5 rounded text-[10px] font-semibold border border-indigo-500 bg-indigo-600/30 text-indigo-300 shadow-sm transition-all';
        } else {
            btn.className = 'match-chip px-2 py-0.5 rounded text-[10px] font-medium border border-slate-800 bg-slate-900/90 text-slate-400 hover:border-slate-700 transition-all';
        }
    });
}

function onFilterChange() {
    filterSearch = (document.getElementById('filter-search')?.value || '').toLowerCase().trim();
    filterSource = document.getElementById('filter-source')?.value || 'all';
    filterSort = document.getElementById('filter-sort')?.value || 'newest';

    renderList();
}

function selectVac(id) {
    currentVac = vacancies.find(v => String(v.id) === String(id));
    renderList();
    renderDetails();
}

function renderList() {
    const listEl = document.getElementById('vacancy-list');
    if (!listEl) return;
    const targetStatus = (currentTab === 'inbox') ? ['inbox', 'new'] : [currentTab];
    let filtered = vacancies.filter(v => targetStatus.includes(v.status));

    // 1. Market filter (ru / en)
    if (currentMarket === 'ru') {
        filtered = filtered.filter(v => (v.language || 'ru') === 'ru');
    } else if (currentMarket === 'en') {
        filtered = filtered.filter(v => v.language === 'en');
    }

    // 2. Search query filter
    if (filterSearch) {
        filtered = filtered.filter(v => {
            const text = `${v.title || ''} ${v.company || ''} ${v.description || ''} ${v.skills || ''} ${v.location || ''} ${v.blacklist_reason || ''}`.toLowerCase();
            return text.includes(filterSearch);
        });
    }

    // 3. Multi-Grade filter
    if (filterGrades.length > 0) {
        filtered = filtered.filter(v => {
            const g = (v.grade || 'Middle').toLowerCase();
            return filterGrades.some(fg => fg.toLowerCase() === g);
        });
    }

    // 4. Multi-Match score filter
    if (filterMatches.length > 0) {
        filtered = filtered.filter(v => {
            const score = v.score || 0;
            return filterMatches.some(tier => {
                if (tier === '80') return score >= 80;
                if (tier === '60') return score >= 60 && score < 80;
                if (tier === 'mixed') return score < 60;
                return false;
            });
        });
    }

    // 5. Source filter
    if (filterSource !== 'all') {
        filtered = filtered.filter(v => (v.source || '').toLowerCase().includes(filterSource));
    }

    // 6. Sorting
    if (filterSort === 'score_desc') {
        filtered.sort((a, b) => (b.score || 0) - (a.score || 0));
    } else if (filterSort === 'newest') {
        filtered.sort((a, b) => {
            const timeA = new Date((a.published_at || a.created_at || '').replace(' ', 'T')).getTime() || 0;
            const timeB = new Date((b.published_at || b.created_at || '').replace(' ', 'T')).getTime() || 0;
            return timeB - timeA;
        });
    } else if (filterSort === 'salary') {
        filtered.sort((a, b) => parseSalaryValue(b.salary) - parseSalaryValue(a.salary));
    }

    if (filtered.length === 0) {
        listEl.innerHTML = `<div class="p-4 text-center text-slate-500 bg-slate-900/50 rounded-lg border border-slate-800 text-xs">Нет вакансий по выбранным фильтрам</div>`;
        return;
    }

    listEl.innerHTML = filtered.map(v => {
        const isEn = v.language === 'en';
        const langBadge = isEn
            ? `<span class="text-[10px] font-semibold px-2 py-0.5 rounded bg-sky-950/80 text-sky-400 border border-sky-800/70 flex items-center gap-1">🌍 EN</span>`
            : `<span class="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800/70 flex items-center gap-1">🇷🇺 RU</span>`;

        const grade = v.grade || 'Middle';
        let gradeClass = 'bg-sky-950/80 text-sky-400 border-sky-800/70';
        if (grade === 'Junior' || grade === 'Intern') {
            gradeClass = 'bg-emerald-950/80 text-emerald-400 border-emerald-800/70';
        } else if (grade === 'Senior') {
            gradeClass = 'bg-purple-950/80 text-purple-300 border-purple-800/70';
        } else if (grade === 'Lead') {
            gradeClass = 'bg-amber-950/80 text-amber-300 border-amber-800/70';
        }
        const gradeBadge = `<span class="text-[10px] font-semibold px-2 py-0.5 rounded border ${gradeClass}">${grade}</span>`;

        const timeStr = formatRelativeTime(v.published_at || v.created_at);
        const timeBadge = timeStr ? `<span class="text-[10px] text-slate-400 font-mono" title="${v.published_at || v.created_at || ''}">⏱ ${timeStr}</span>` : '';

        const hasDirectContact = Boolean(
            v.contact_handle && 
            v.contact_handle.trim() !== '' &&
            (
                (v.contact_type === 'telegram' && v.contact_handle.startsWith('@') && !v.contact_handle.includes('t.me/')) ||
                (v.contact_type === 'email' && v.contact_handle.includes('@') && v.contact_handle.includes('.'))
            )
        );
        const directBadge = hasDirectContact ? `<span class="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/70 flex items-center gap-1" title="Прямой контакт: ${v.contact_handle}">✈️ Прямой контакт</span>` : '';
        const isBlacklist = v.status === 'blacklist';
        const blacklistBadge = isBlacklist
            ? `<span class="text-[10px] font-semibold px-2 py-0.5 rounded bg-rose-950/90 text-rose-300 border border-rose-800/80 flex items-center gap-1" title="${v.blacklist_reason || 'В Черном списке'}">🛑 ${escapeHtml((v.blacklist_reason || 'Черный список').slice(0, 32))}${v.blacklist_reason && v.blacklist_reason.length > 32 ? '...' : ''}</span>`
            : '';

        let borderClass = 'bg-slate-900/50 border-slate-800 hover:border-slate-700';
        if (currentVac?.id === v.id) {
            borderClass = isBlacklist ? 'bg-slate-800/90 border-rose-500 shadow-sm' : 'bg-slate-800/90 border-sky-500 shadow-sm';
        } else if (isBlacklist) {
            borderClass = 'bg-rose-950/20 border-rose-900/50 hover:border-rose-800';
        }

        return `
        <div onclick="selectVac('${v.id}')" 
             class="cursor-pointer p-3 rounded-xl border transition-all ${borderClass}">
            <div class="flex items-center justify-between gap-1.5 mb-1.5 flex-wrap">
                <div class="flex items-center gap-1 flex-wrap">
                    <span class="text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/60">${v.source || 'WEB'}</span>
                    ${gradeBadge}
                    ${langBadge}
                    ${directBadge}
                    ${blacklistBadge}
                </div>
                <div class="flex items-center gap-1.5">
                    ${timeBadge}
                    ${v.score > 0 ? `<span class="text-[11px] font-bold px-2 py-0.5 rounded-full ${v.score >= 80 ? 'bg-emerald-900/50 text-emerald-400 border border-emerald-800/80' : v.score >= 50 ? 'bg-amber-900/50 text-amber-400 border border-amber-800/80' : 'bg-rose-900/50 text-rose-400 border border-rose-800/80'}">🔥 ${v.score}% Match</span>` : ''}
                </div>
            </div>
            <h3 class="font-semibold text-slate-200 text-sm truncate" title="${v.title}">${v.title}</h3>
            <div class="text-sky-400 text-xs mt-1 flex items-center justify-between">
                <span class="truncate pr-2 ${isBlacklist ? 'text-rose-300' : ''}">🏢 ${v.company}</span>
                ${v.salary && v.salary !== 'Не указана' ? `<span class="text-emerald-400 font-medium whitespace-nowrap">${v.salary}</span>` : ''}
            </div>
        </div>
    `}).join('');
}

function renderDetails() {
    const detailsEl = document.getElementById('vacancy-details');
    if (!detailsEl) return;

    if (!currentVac) {
        detailsEl.innerHTML = `
            <div class="h-full flex flex-col items-center justify-center text-slate-500 p-8 text-center min-h-[400px]">
                <span class="text-4xl mb-3">👈</span>
                <p class="text-sm font-medium">Выберите вакансию из списка слева</p>
            </div>`;
        return;
    }

    const v = currentVac;
    const isEn = v.language === 'en';
    let contactInfo = '';
    let actionBtnHtml = '';

    if (v.contact_handle && (v.contact_type === 'telegram' || v.contact_handle.startsWith('@') || v.contact_handle.includes('t.me'))) {
        const tgHandle = v.contact_handle.replace('https://t.me/', '').replace('@', '');
        contactInfo = `<a href="tg://resolve?domain=${tgHandle}&text=${encodeURIComponent(v.short_dm || '')}" class="text-sky-400 hover:text-sky-300 flex items-center gap-1 font-medium bg-sky-900/30 px-3 py-1 rounded-lg text-xs border border-sky-800/50"><span>✈️</span> Telegram HR (Link)</a>`;
        actionBtnHtml = `<button onclick="applyTg('${v.id}')" class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium py-2 px-4 rounded-lg transition-colors flex items-center gap-1.5 shadow-md ring-1 ring-sky-400/30">🤖 Отправить через Userbot</button>`;
    } else {
        actionBtnHtml = `
            <div class="flex items-center gap-2 flex-wrap">
                <button onclick="triggerAgentAutoApply('${v.id}')" id="btn-agent-apply-${v.id}" class="bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold py-2 px-4 rounded-lg transition-all shadow-lg flex items-center gap-2 ring-2 ring-indigo-500/40">
                    <span>🤖</span> Авто-отклик агентом (1-Click)
                </button>
                <button onclick="openVacancyWithAutoApply('${v.id}')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium py-2 px-3 rounded-lg border border-slate-700 transition-all flex items-center gap-1.5 shadow-sm">
                    <span>↗</span> Открыть вручную
                </button>
            </div>
        `;
    }

    const cleanComp = cleanCompanyName(v.company, v.title, v.description);
    const cleanRole = (v.title || '').replace(/[\|\(\)\/].*$/, '').trim() || 'Frontend';

    // OSINT Dorks
    const directAtsQuery = `"${cleanComp}" (site:greenhouse.io OR site:lever.co OR site:ashbyhq.com OR site:workable.com OR inurl:careers OR inurl:jobs) "${cleanRole}"`;
    const directAtsUrl = `https://www.google.com/search?q=${encodeURIComponent(directAtsQuery)}`;

    const setkaQuery = `site:setka.ru "${cleanComp}" (HR OR рекрутер OR CTO OR тимлид OR frontend)`;
    const setkaUrl = `https://www.google.com/search?q=${encodeURIComponent(setkaQuery)}`;

    const hrQuery = isEn
        ? `site:linkedin.com/in "${cleanComp}" ("Technical Recruiter" OR "Talent Acquisition" OR "Recruiter" OR "Head of HR")`
        : `(site:linkedin.com/in OR site:t.me OR site:habr.com/ru/users OR site:setka.ru) "${cleanComp}" (рекрутер OR HR OR "talent acquisition" OR "найм")`;
    const hrSearchUrl = `https://www.google.com/search?q=${encodeURIComponent(hrQuery)}`;

    const ctoQuery = isEn
        ? `site:linkedin.com/in "${cleanComp}" ("CTO" OR "Engineering Manager" OR "Head of Engineering" OR "Tech Lead" OR "VP of Engineering")`
        : `(site:linkedin.com/in OR site:habr.com/ru/users OR site:setka.ru) "${cleanComp}" (CTO OR "Engineering Manager" OR "Tech Lead" OR "Тимлид Frontend" OR "Руководитель разработки")`;
    const ctoSearchUrl = `https://www.google.com/search?q=${encodeURIComponent(ctoQuery)}`;

    const emailQuery = `"${cleanComp}" ("careers@" OR "jobs@" OR "hr@" OR email) hiring`;
    const emailSearchUrl = `https://www.google.com/search?q=${encodeURIComponent(emailQuery)}`;

    const marketBadge = isEn
        ? `<span class="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-sky-950 text-sky-300 border border-sky-700 flex items-center gap-1">🌍 International · Remote (EN)</span>`
        : `<span class="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-700 flex items-center gap-1">🇷🇺 Локальная / РФ и СНГ (RU)</span>`;

    const grade = v.grade || 'Middle';
    let gradeBadgeClass = 'bg-sky-950/90 text-sky-300 border-sky-700';
    if (grade === 'Junior' || grade === 'Intern') {
        gradeBadgeClass = 'bg-emerald-950/90 text-emerald-300 border-emerald-700';
    } else if (grade === 'Senior') {
        gradeBadgeClass = 'bg-purple-950/90 text-purple-300 border-purple-700';
    } else if (grade === 'Lead') {
        gradeBadgeClass = 'bg-amber-950/90 text-amber-300 border-amber-700';
    }
    const gradeBadge = `<span class="text-xs font-semibold px-2.5 py-0.5 rounded-full border ${gradeBadgeClass}">Грейд: ${grade}</span>`;

    const activeP = profiles.find(p => p.id === activeProfileId);
    const personaHint = activeP
        ? `${activeP.role || activeP.name} (${(activeP.lang || 'ru').toUpperCase()})`
        : (isEn ? `🇬🇧 Международный профиль (English · Frontend / Full-stack Engineer)` : `🇷🇺 Локальный профиль (Русский · Frontend разработчик)`);

    const pubDateStr = v.published_at || v.created_at || '';
    const pubRelative = formatRelativeTime(pubDateStr);

    detailsEl.innerHTML = `
        ${v.status === 'blacklist' ? `
        <div class="bg-rose-950/70 border border-rose-700/80 rounded-xl p-4 mb-4 text-xs text-rose-200 flex items-start gap-3 shadow-md">
            <span class="text-2xl">🛑</span>
            <div class="flex-1">
                <div class="font-bold text-rose-300 text-sm mb-0.5">Внесено в Черный список (Доска позора)</div>
                <div class="text-white font-medium mb-1">Причина: <span class="text-rose-200">${escapeHtml(v.blacklist_reason || 'Токсичные условия / Нарушение ТК РФ')}</span></div>
                <div class="text-[11px] text-rose-400">Зафиксировано: ${v.blacklisted_at || v.created_at || '—'} · Запись синхронизирована с SHAME_LIST.md</div>
            </div>
            <button onclick="updateStatus('${v.id}', 'inbox')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-lg border border-slate-600 transition-colors whitespace-nowrap">
                ↩ Восстановить в Inbox
            </button>
        </div>` : ''}

        <div class="glass-panel rounded-xl p-5 border-l-4 ${isEn ? 'border-l-sky-500' : 'border-l-amber-500'} mb-4 shadow-sm">
            <div class="flex flex-col gap-3">
                <div class="flex items-center gap-2 flex-wrap">
                    <h2 class="text-xl font-bold text-white">${v.title}</h2>
                    ${marketBadge}
                    ${gradeBadge}
                    ${v.score > 0 ? `<span class="text-xs font-bold px-2 py-0.5 rounded-full ${v.score >= 80 ? 'bg-emerald-900/50 text-emerald-400 border border-emerald-800' : 'bg-amber-900/50 text-amber-400 border border-amber-800'}">🔥 ${v.score}% Match</span>` : ''}
                </div>
                <div class="flex gap-3 items-center text-xs text-slate-400 flex-wrap">
                    <span class="text-sky-400 font-medium">🏢 ${cleanComp !== v.company ? `${cleanComp} <span class="text-slate-500 text-[11px]">(${v.company})</span>` : v.company}</span>
                    <span>•</span>
                    <span>📍 ${v.location || (isEn ? 'Worldwide Remote' : 'Удаленно')}</span>
                    ${v.salary && v.salary !== 'Не указана' ? `<span>•</span><span class="text-emerald-400 font-medium">💰 ${v.salary}</span>` : ''}
                    ${pubDateStr ? `<span>•</span><span class="text-slate-300 font-mono" title="${pubDateStr}">⏱ ${pubRelative} (${pubDateStr.split('.')[0]})</span>` : ''}
                    <span>•</span>
                    <a href="${formatVacancyUrl(v.url)}" target="_blank" class="text-slate-400 hover:text-white underline">Оригинал вакансии ↗</a>
                </div>
                
                <div class="mt-1">
                    ${contactInfo}
                </div>
            </div>
        </div>

        <!-- Persona Active Indicator -->
        <div class="bg-slate-900/60 px-3.5 py-2 rounded-xl border border-slate-800 text-xs text-slate-400 flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
                <span>🎯 Активное резюме под вакансию:</span>
                <span class="font-medium text-purple-300">${personaHint}</span>
            </div>
            <button onclick="setTab('profiles')" class="text-purple-400 hover:underline text-[11px]">Редактировать ↗</button>
        </div>

        <div id="ai-progress-${v.id}" class="hidden mb-4 bg-slate-900/90 rounded-lg p-3 border border-slate-700 text-xs">
            <div class="text-slate-400 flex items-center gap-2">
                <span class="animate-spin">⏳</span>
                <span id="ai-text-${v.id}">Генерация текста и оценка матчинга...</span>
            </div>
        </div>

        <div class="flex flex-col gap-4 mb-4">
            <div>
                <div class="flex justify-between items-center mb-1.5">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-400">💬 Short DM (${isEn ? 'English' : 'Русский'})</h3>
                    <button onclick="copyFieldText('dm-box')" class="text-[11px] bg-slate-800 hover:bg-slate-700 px-2 py-0.5 rounded text-slate-300 border border-slate-700">Копировать</button>
                </div>
                <textarea id="dm-box" class="w-full bg-slate-900/80 border border-slate-700/80 rounded-lg p-3 text-xs text-slate-300 h-28 focus:outline-none focus:border-sky-500 font-sans leading-relaxed">${v.short_dm || ''}</textarea>
            </div>

            <div>
                <div class="flex justify-between items-center mb-1.5">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-400">📧 Cover Letter (${isEn ? 'English' : 'Русский'})</h3>
                    <button onclick="copyFieldText('cl-box')" class="text-[11px] bg-slate-800 hover:bg-slate-700 px-2 py-0.5 rounded text-slate-300 border border-slate-700">Копировать</button>
                </div>
                <textarea id="cl-box" class="w-full bg-slate-900/80 border border-slate-700/80 rounded-lg p-3 text-xs text-slate-300 h-44 focus:outline-none focus:border-sky-500 font-sans leading-relaxed">${v.cover_letter || ''}</textarea>
            </div>
        </div>

        <div class="pt-4 border-t border-slate-700/60 flex flex-col gap-3">
            <div class="flex flex-wrap gap-2 items-center justify-between">
                <div class="flex flex-wrap gap-2 items-center">
                    ${actionBtnHtml}
                    <button onclick="rewriteAI('${v.id}')" id="btn-rewrite-${v.id}" class="bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium py-1.5 px-3 rounded-lg border border-slate-700 transition-colors flex items-center gap-1.5 shadow-sm">
                        <span>✨</span> Переписать (AI)
                    </button>
                    <a href="/cv/${v.id}" target="_blank" class="bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium py-1.5 px-3 rounded-lg border border-slate-700 transition-colors flex items-center gap-1.5 shadow-sm">
                        <span>📄</span> PDF
                    </a>
                </div>
                
                <div class="flex gap-2 items-center mt-2 sm:mt-0">
                    ${(v.status === 'inbox' || v.status === 'new') ? `<button onclick="updateStatus('${v.id}', 'sent')" class="bg-emerald-600/80 hover:bg-emerald-600 text-white text-xs font-medium py-1.5 px-3 rounded-lg transition-colors flex items-center gap-1.5 shadow-sm">✅ Отправлено</button>` : ''}
                    ${v.status === 'sent' ? `<button onclick="updateStatus('${v.id}', 'replied')" class="bg-purple-600/80 hover:bg-purple-600 text-white text-xs font-medium py-1.5 px-3 rounded-lg transition-colors flex items-center gap-1.5 shadow-sm">💬 Ответили</button>` : ''}
                    
                    <div class="relative">
                        <button onclick="toggleActionMenu('${v.id}')" id="btn-menu-${v.id}" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium py-1.5 px-3 rounded-lg transition-colors flex items-center gap-1 border border-slate-700">
                            ⚙️ Ещё ▾
                        </button>
                        <div onclick="closeActionMenu('${v.id}')" id="menu-overlay-${v.id}" class="fixed inset-0 z-40 hidden"></div>
                        
                        <div id="menu-${v.id}" class="absolute right-0 bottom-full mb-1 hidden z-50">
                            <div class="bg-slate-800 border border-slate-700 rounded-lg shadow-xl overflow-hidden w-64 flex flex-col">
                                <a href="${directAtsUrl}" target="_blank" onclick="closeActionMenu('${v.id}')" class="text-left px-3 py-2 text-xs text-indigo-300 hover:bg-slate-700 transition-colors border-b border-slate-700 flex items-center gap-1.5"><span class="text-[10px]">🏢</span> Вакансия в ATS (Greenhouse)</a>
                                <a href="${hrSearchUrl}" target="_blank" onclick="closeActionMenu('${v.id}')" class="text-left px-3 py-2 text-xs text-sky-300 hover:bg-slate-700 transition-colors border-b border-slate-700 flex items-center gap-1.5"><span class="text-[10px]">🔍</span> Найти HR (LinkedIn/TG)</a>
                                <a href="${ctoSearchUrl}" target="_blank" onclick="closeActionMenu('${v.id}')" class="text-left px-3 py-2 text-xs text-amber-300 hover:bg-slate-700 transition-colors border-b border-slate-700 flex items-center gap-1.5"><span class="text-[10px]">⚡</span> Найти CTO / Тимлида</a>
                                <a href="${emailSearchUrl}" target="_blank" onclick="closeActionMenu('${v.id}')" class="text-left px-3 py-2 text-xs text-slate-300 hover:bg-slate-700 transition-colors border-b border-slate-700 flex items-center gap-1.5"><span class="text-[10px]">✉️</span> Корп. Email</a>
                                
                                <button onclick="closeActionMenu('${v.id}'); updateStatus('${v.id}', 'archive');" class="text-left px-3 py-2 text-xs text-slate-300 hover:bg-slate-700 transition-colors flex items-center gap-1.5"><span class="text-[10px]">📦</span> В архив</button>
                                <button onclick="closeActionMenu('${v.id}'); openBlacklistModal('${v.id}');" class="text-left px-3 py-2 text-xs text-rose-400 hover:bg-rose-950/50 transition-colors border-t border-slate-700 flex items-center gap-1.5"><span class="text-[10px]">💩</span> В Черный список (ТК РФ)</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="mt-4 bg-slate-900/40 p-4 rounded-xl border border-slate-800/80">
            <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">📋 Описание вакансии</h3>
            <div class="text-xs text-slate-400 whitespace-pre-wrap leading-relaxed">${v.description || 'Нет описания.'}</div>
        </div>
    `;
}

function copyFieldText(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.select();
    document.execCommand('copy');
    const originalBorder = el.style.borderColor;
    el.style.borderColor = '#10b981';
    setTimeout(() => { el.style.borderColor = originalBorder; }, 600);
}

function openVacancyWithAutoApply(vacId) {
    const v = vacancies.find(x => String(x.id) === String(vacId));
    if (!v) return;
    const text = v.cover_letter || v.short_dm || '';
    if (text) {
        try {
            navigator.clipboard.writeText(text);
        } catch(e) {}
        showToast('📋 Письмо скопировано в буфер! Открываем сайт вакансии...');
    }

    const rawUrl = formatVacancyUrl(v.url);
    if (rawUrl.startsWith('mailto:')) {
        const mailUrl = rawUrl + (rawUrl.includes('?') ? '&' : '?') + 'subject=' + encodeURIComponent('Отклик: ' + (v.title || '')) + '&body=' + encodeURIComponent(text);
        window.location.href = mailUrl;
        return;
    }

    // Safely encode text into hash payload for zero-network bookmarklet reading
    const safePayload = encodeURIComponent(text);
    const targetUrl = rawUrl.includes('#') ? rawUrl : (rawUrl + '#jh_cover=' + safePayload);
    window.open(targetUrl, '_blank');
}

async function triggerAgentAutoApply(vacId) {
    const v = vacancies.find(x => String(x.id) === String(vacId));
    if (!v) return;

    const btn = document.getElementById(`btn-agent-apply-${vacId}`);
    const origHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="inline-block animate-spin">⏳</span> Агент открывает вакансию...';
        btn.className = btn.className.replace('from-indigo-600', 'from-amber-600').replace('to-indigo-600', 'to-amber-600');
    }

    showToast('🚀 Задача передана агенту! Открываю вкладку в браузере...');

    try {
        const res = await fetch('/api/agent/queue-task', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                vacancy_id: v.id,
                url: formatVacancyUrl(v.url),
                company: v.company || 'Unknown',
                role_title: v.title || 'Engineer',
                portal: v.source || 'web',
                cover_letter: v.cover_letter || v.short_dm || ''
            })
        });
        const data = await res.json();
        if (data.success) {
            if (btn) {
                btn.innerHTML = '<span class="inline-block animate-pulse">📝</span> Заполняю форму...';
            }

            // Poll for task completion with resilient error handling
            let pollCount = 0;
            const maxPolls = 20; // 60 seconds max
            const pollInterval = setInterval(async () => {
                pollCount++;
                try {
                    const statusRes = await fetch(`/api/vacancies/${vacId}/runtime_state`);
                    const stateData = await statusRes.json();
                    if (stateData.fsm_state === 'SUBMITTED') {
                        clearInterval(pollInterval);
                        if (btn) {
                            btn.innerHTML = '<span>✅</span> Отклик заполнен!';
                            btn.className = btn.className.replace('from-amber-600', 'from-emerald-600').replace('to-amber-600', 'to-emerald-600');
                            setTimeout(() => {
                                btn.disabled = false;
                                btn.innerHTML = origHtml;
                                btn.className = btn.className.replace('from-emerald-600', 'from-indigo-600').replace('to-emerald-600', 'to-indigo-600');
                            }, 4000);
                        }
                        showToast('🎉 Агент заполнил форму! Проверьте вкладку в браузере.');
                        await updateStatus(vacId, 'sent');
                    } else if (stateData.fsm_state === 'FAILED') {
                        clearInterval(pollInterval);
                        if (btn) {
                            btn.innerHTML = '<span>❌</span> Ошибка';
                            btn.className = btn.className.replace('from-amber-600', 'from-rose-600').replace('to-amber-600', 'to-rose-600');
                            setTimeout(() => {
                                btn.disabled = false;
                                btn.innerHTML = origHtml;
                                btn.className = btn.className.replace('from-rose-600', 'from-indigo-600').replace('to-rose-600', 'to-indigo-600');
                            }, 4000);
                        }
                        showToast('❌ Агент не смог заполнить форму. Откройте вакансию вручную.');
                    } else if (pollCount >= maxPolls) {
                        clearInterval(pollInterval);
                        if (btn) {
                            btn.innerHTML = '<span>⏱</span> Таймаут — проверьте вкладку';
                            btn.className = btn.className.replace('from-amber-600', 'from-slate-600').replace('to-amber-600', 'to-slate-600');
                            setTimeout(() => {
                                btn.disabled = false;
                                btn.innerHTML = origHtml;
                                btn.className = btn.className.replace('from-slate-600', 'from-indigo-600').replace('to-slate-600', 'to-indigo-600');
                            }, 4000);
                        }
                    } else {
                        // Update button with progress
                        if (btn && pollCount % 2 === 0) {
                            const dots = '.'.repeat((pollCount % 4) + 1);
                            btn.innerHTML = `<span class="inline-block animate-pulse">📝</span> Заполняю${dots}`;
                        }
                    }
                } catch (e) {
                    // Transient network error — don't break polling, just retry
                    console.debug('[Agent] Poll retry:', e.message);
                }
            }, 3000);
        } else {
            alert('Ошибка постановки задачи агенту: ' + (data.error || 'Неизвестная ошибка'));
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = origHtml;
            }
        }
    } catch (err) {
        alert('Ошибка связи с сервером CRM: ' + err.message);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
    }
}

async function rewriteAI(vac_id) {
    const btn = document.getElementById(`btn-rewrite-${vac_id}`);
    const prog = document.getElementById(`ai-progress-${vac_id}`);
    const ptext = document.getElementById(`ai-text-${vac_id}`);

    if (btn) {
        btn.disabled = true;
        btn.classList.add('opacity-50');
    }
    if (prog) prog.classList.remove('hidden');
    if (ptext) ptext.innerText = 'Запрос в Gemini... (подбираем персону и генерируем pitch)';

    try {
        const data = await api.rewriteAI(vac_id);
        if (data.success) {
            if (ptext) ptext.innerHTML = '<span class="text-emerald-400 font-medium">✅ Готово! Текст обновлен.</span>';
            setTimeout(() => { if (prog) prog.classList.add('hidden'); }, 2000);

            const v = vacancies.find(v => String(v.id) === String(vac_id));
            if (v) {
                v.short_dm = data.short_dm;
                v.cover_letter = data.cover_letter;
                if (data.score) v.score = data.score;
            }
            renderDetails();
            renderList();
        } else {
            if (ptext) ptext.innerHTML = `<span class="text-rose-400 font-medium">❌ ${data.error || 'Ошибка генерации'}</span>`;
        }
    } catch (e) {
        if (ptext) ptext.innerHTML = `<span class="text-rose-400 font-medium">❌ Ошибка сети. Проверьте VPN и консоль сервера.</span>`;
    }

    if (btn) {
        btn.disabled = false;
        btn.classList.remove('opacity-50');
    }
}

async function applyTg(vacId) {
    const btn = event.currentTarget;
    const origHtml = btn.innerHTML;
    btn.innerHTML = '⏳ Отправка...';
    btn.disabled = true;
    showToast('Отправка через Telegram Userbot...');
    try {
        const res = await fetch(`/api/vacancies/${vacId}/apply_tg`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('✅ Сообщение успешно отправлено в Telegram!');
            await updateStatus(vacId, 'sent');
        } else {
            alert('Ошибка отправки: ' + (data.error || 'Неизвестная ошибка'));
            btn.innerHTML = origHtml;
            btn.disabled = false;
        }
    } catch (e) {
        alert('Ошибка сети: ' + e);
        btn.innerHTML = origHtml;
        btn.disabled = false;
    }
}

async function updateStatus(vac_id, status, reason = null) {
    try {
        await api.updateVacancyStatus(vac_id, status, reason);
        const v = vacancies.find(v => String(v.id) === String(vac_id));
        if (v) {
            v.status = status;
            if (reason) v.blacklist_reason = reason;
            if (status === 'blacklist') {
                v.blacklisted_at = new Date().toISOString().slice(0, 19).replace('T', ' ');
            }
        }
        updateCounts();

        // Select next vacancy in current active tab
        const targetStatus = (currentTab === 'inbox') ? ['inbox', 'new'] : [currentTab];
        const remaining = vacancies.filter(x => targetStatus.includes(x.status));
        currentVac = remaining.length > 0 ? remaining[0] : null;

        renderList();
        renderDetails();

        if (status === 'blacklist') {
            showToast('🛑 Вакансия занесена в Черный список и Доску позора');
        } else if (status === 'inbox') {
            showToast('↩ Вакансия восстановлена в Inbox');
        } else if (status === 'archive') {
            showToast('📦 Вакансия отправлена в архив');
        }
    } catch (e) {
        alert("Ошибка: " + e);
    }
}

function openBlacklistModal(vacId) {
    pendingBlacklistVacId = vacId;
    const v = vacancies.find(x => String(x.id) === String(vacId));
    const titleEl = document.getElementById('blacklist-modal-vac-info');
    if (titleEl && v) {
        titleEl.innerText = `${v.company} — ${v.title}`;
    }
    const input = document.getElementById('blacklist-reason-input');
    if (input) {
        input.value = 'Навязывание ИП / Самозанятости с 1-го дня (уклонение от ТК РФ, перекладывание рисков)';
    }
    toggleModal('blacklist-modal');
}

function setBlacklistTag(reasonText) {
    const input = document.getElementById('blacklist-reason-input');
    if (input) input.value = reasonText;
}

async function confirmBlacklist() {
    if (!pendingBlacklistVacId) return;
    const input = document.getElementById('blacklist-reason-input');
    const reason = (input && input.value.trim()) || 'Токсичные условия / Нарушение ТК РФ';
    const targetId = pendingBlacklistVacId;
    pendingBlacklistVacId = null;
    toggleModal('blacklist-modal');
    await updateStatus(targetId, 'blacklist', reason);
}

async function openShameListModal() {
    try {
        const res = await api.getShameList();
        const pre = document.getElementById('shame-list-content');
        if (pre) pre.innerText = res.markdown || 'Список пуст.';
        toggleModal('shame-list-modal');
    } catch (e) {
        alert("Ошибка загрузки Доски позора: " + e.message);
    }
}

function copyShameListMarkdown() {
    const pre = document.getElementById('shame-list-content');
    if (pre) {
        navigator.clipboard.writeText(pre.innerText);
        showToast('📋 Доска позора (Markdown) скопирована в буфер обмена!');
    }
}

function toggleActionMenu(vacId) {
    const menu = document.getElementById(`menu-${vacId}`);
    const overlay = document.getElementById(`menu-overlay-${vacId}`);
    const btn = document.getElementById(`btn-menu-${vacId}`);
    if (!menu) return;

    const isOpening = menu.classList.contains('hidden');
    if (isOpening) {
        if (btn) {
            const rect = btn.getBoundingClientRect();
            // If space above is less than 260px (menu height ~240px), open downwards instead of upwards
            if (rect.top < 260) {
                menu.classList.remove('bottom-full', 'mb-1');
                menu.classList.add('top-full', 'mt-1');
            } else {
                menu.classList.remove('top-full', 'mt-1');
                menu.classList.add('bottom-full', 'mb-1');
            }
        }
        menu.classList.remove('hidden');
        if (overlay) overlay.classList.remove('hidden');
    } else {
        menu.classList.add('hidden');
        if (overlay) overlay.classList.add('hidden');
    }
}

function closeActionMenu(vacId) {
    const menu = document.getElementById(`menu-${vacId}`);
    const overlay = document.getElementById(`menu-overlay-${vacId}`);
    if (menu) menu.classList.add('hidden');
    if (overlay) overlay.classList.add('hidden');
}
