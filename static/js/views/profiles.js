// ==========================================
// Job Hunter CRM — Profiles & Candidate View
// ==========================================

function renderActiveProfileDropdown() {
    const select = document.getElementById('active-profile-select');
    const modalLabel = document.getElementById('harvest-active-profile-label');
    if (!select) return;

    if (!profiles || profiles.length === 0) {
        select.innerHTML = '<option value="">(Нет профилей)</option>';
        if (modalLabel) modalLabel.innerText = 'По умолчанию';
        return;
    }

    if (!activeProfileId || !profiles.some(p => p.id === activeProfileId)) {
        activeProfileId = profiles[0].id;
    }

    select.innerHTML = profiles.map(p => `
        <option value="${p.id}" ${p.id === activeProfileId ? 'selected' : ''}>
            ${p.role || p.name || p.id} (${(p.lang || 'ru').toUpperCase()})
        </option>
    `).join('');

    const cur = profiles.find(p => p.id === activeProfileId) || profiles[0];
    if (modalLabel && cur) {
        modalLabel.innerText = `${cur.role || cur.name} (${(cur.lang || 'ru').toUpperCase()})`;
    }
}

async function changeActiveProfile(profileId) {
    activeProfileId = profileId;
    renderActiveProfileDropdown();
    initBookmarklet();
    try {
        await api.saveConfig({ active_profile_id: profileId });
        showToast('🎯 Активное резюме переключено!');
        renderDetails();
    } catch (e) {
        console.error("Error saving active profile", e);
    }
}

async function loadProfilesList() {
    try {
        profiles = await api.getProfiles();
        renderProfilesList();
        renderProfileEditor();
        renderActiveProfileDropdown();
        initBookmarklet();
    } catch (e) {
        console.error("Error loading profiles", e);
    }
}

function renderProfilesList() {
    const list = document.getElementById('profiles-list');
    if (!list) return;

    list.innerHTML = profiles.map((p, idx) => `
        <div onclick="selectProfile(${idx})" class="p-3.5 rounded-xl cursor-pointer border transition-all ${currentProfile === idx
            ? 'bg-slate-800/90 border-purple-500/80 shadow-md ring-1 ring-purple-500/30'
            : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
        }">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center overflow-hidden flex-shrink-0">
                    ${p.photo_url ? `<img src="${p.photo_url}" class="w-full h-full object-cover">` : `<span class="text-xs font-bold text-slate-400">${(p.name || 'P')[0]}</span>`}
                </div>
                <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-1.5">
                        <span class="text-xs font-bold text-white truncate">${p.role || 'Без роли'}</span>
                        <span class="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">${p.lang || 'ru'}</span>
                    </div>
                    <div class="text-[11px] text-slate-400 truncate mt-0.5">${p.name || 'Имя не указано'}</div>
                </div>
            </div>
        </div>
    `).join('');
}

function selectProfile(i) {
    currentProfile = i;
    renderProfilesList();
    renderProfileEditor();
}

async function addProfile() {
    const newId = 'profile_' + Date.now();
    const newP = {
        id: newId,
        lang: 'ru',
        role: 'Frontend / Fullstack-разработчик',
        name: 'Имя Фамилия',
        photo_url: '',
        contacts: 'Telegram: @username | Email: candidate@example.com | Телефон: +79990000000 | GitHub: https://github.com/username | LinkedIn: https://linkedin.com/in/username',
        contacts_structured: {
            telegram: '@username',
            email: 'candidate@example.com',
            phone: '+79990000000',
            github: 'https://github.com/username',
            linkedin: 'https://linkedin.com/in/username',
            portfolio: 'https://example.com'
        },
        location: { city: 'Москва', country: 'Россия', remote: true, hybrid: true, office: true },
        summary: 'Разрабатываю продукты и довожу их до production — от архитектурных решений до деплоя с реальными пользователями.',
        keywords: 'Next.js 16, React 19, TypeScript, JavaScript, Tailwind CSS v4, FastAPI, Node.js, Docker, Traefik, Git, CI/CD',
        experience: '',
        experience_structured: [],
        education: [
            { grade: 'Высшее образование', field: 'Информационные технологии', institution: 'Университет', years: '2016–2020' }
        ],
        languages: [
            { language: 'Русский', level: 'родной' },
            { language: 'Английский', level: 'B2' }
        ]
    };
    profiles.push(newP);
    await api.saveProfiles(profiles);
    showToast('✅ Создан и сохранен новый профиль!');
    selectProfile(profiles.length - 1);
}

function renderProfileEditor() {
    const ed = document.getElementById('profile-editor');
    if (!ed) return;

    if (currentProfile === null || !profiles[currentProfile]) {
        ed.innerHTML = '<div class="text-center py-16 text-slate-500 text-xs">Выберите профиль слева</div>';
        return;
    }
    const p = profiles[currentProfile];
    const c = p.contacts_structured || {};
    const loc = p.location || {};
    const expList = p.experience_structured || [];
    const eduList = p.education || [];
    const langList = p.languages || [];

    ed.innerHTML = `
        <div class="flex flex-col gap-4 bg-slate-900/50 p-5 rounded-xl border border-slate-800 h-[calc(100vh-14rem)] overflow-y-auto pr-2">
            <!-- Top Upload Bar -->
            <div class="flex justify-between items-center bg-slate-900/90 p-3 rounded-lg border border-slate-700/80 shadow-sm">
                <div>
                    <div class="text-xs font-semibold text-white flex items-center gap-2">
                        <span>📄</span> Автопарсинг резюме под стандарты площадок
                    </div>
                    <div class="text-[11px] text-slate-400">Парсит PDF/DOCX: поля разбиваются на опыт, компании, контакты, стек и грейды образования</div>
                </div>
                <div class="flex items-center gap-2">
                    <label class="bg-indigo-600 hover:bg-indigo-500 cursor-pointer text-white text-xs font-medium px-3.5 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 shadow-sm">
                        <span>📤</span> Загрузить файл
                        <input type="file" class="hidden" accept=".pdf,.docx,.txt" onchange="uploadResume(this)">
                    </label>
                    <span id="resume-status" class="text-xs"></span>
                </div>
            </div>

            <!-- 1. Basic Info -->
            <div class="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
                <h3 class="text-xs font-bold text-sky-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                    <span>👤</span> Основная информация (HH.ru / LinkedIn)
                </h3>
                <div class="grid grid-cols-3 gap-3 mb-3">
                    <div>
                        <label class="text-[11px] font-medium text-slate-400 mb-1 block">ID профиля</label>
                        <input id="p-id" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-mono" value="${escapeHtml(p.id || '')}">
                    </div>
                    <div>
                        <label class="text-[11px] font-medium text-slate-400 mb-1 block">Язык откликов</label>
                        <select id="p-lang" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white">
                            <option value="ru" ${p.lang !== 'en' ? 'selected' : ''}>🇷🇺 Русский</option>
                            <option value="en" ${p.lang === 'en' ? 'selected' : ''}>🇺🇸 English</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-[11px] font-medium text-slate-400 mb-1 block">Желаемая должность / Headline</label>
                        <input id="p-role" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-medium" value="${escapeHtml(p.role || '')}">
                    </div>
                </div>

                <div class="grid grid-cols-3 gap-3">
                    <div>
                        <label class="text-[11px] font-medium text-slate-400 mb-1 block">Имя и Фамилия</label>
                        <input id="p-name" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white" value="${escapeHtml(p.name || '')}">
                    </div>
                    <div>
                        <label class="text-[11px] font-medium text-slate-400 mb-1 block">Город / Локация</label>
                        <input id="p-city" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white" value="${escapeHtml(loc.city || 'Москва')}">
                    </div>
                    <div>
                        <label class="text-[11px] font-medium text-slate-400 mb-1 block">Аватар</label>
                        <div class="flex gap-2">
                            <input id="p-photo" class="flex-1 bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white truncate" value="${escapeHtml(p.photo_url || '')}">
                            <label class="bg-slate-800 hover:bg-slate-700 border border-slate-700 cursor-pointer px-2.5 py-1.5 rounded-lg text-xs flex items-center" title="Загрузить фото и центрировать">
                                📷 <input type="file" class="hidden" accept="image/*" onchange="initCrop(this)">
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 2. Structured Contact Channels -->
            <div class="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
                <h3 class="text-xs font-bold text-sky-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                    <span>📞</span> Контакты для откликов
                </h3>
                <div class="grid grid-cols-3 gap-3 mb-2">
                    <div>
                        <label class="text-[11px] font-medium text-slate-400 mb-1 block">Telegram</label>
                        <input id="p-tg" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white" value="${escapeHtml(c.telegram || '')}" placeholder="@username">
                    </div>
                    <div>
                        <label class="text-[11px] font-medium text-slate-400 mb-1 block">Email</label>
                        <input id="p-email" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white" value="${escapeHtml(c.email || '')}" placeholder="email@gmail.com">
                    </div>
                    <div>
                        <label class="text-[11px] font-medium text-slate-400 mb-1 block">Телефон</label>
                        <input id="p-phone" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white" value="${escapeHtml(c.phone || '')}" placeholder="+7 (999) 000-00-00">
                    </div>
                </div>
                <div class="grid grid-cols-3 gap-3">
                    <div>
                        <label class="text-[11px] font-medium text-slate-400 mb-1 block">GitHub</label>
                        <input id="p-gh" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white" value="${escapeHtml(c.github || '')}" placeholder="https://github.com/...">
                    </div>
                    <div>
                        <label class="text-[11px] font-medium text-slate-400 mb-1 block">LinkedIn</label>
                        <input id="p-li" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white" value="${escapeHtml(c.linkedin || '')}" placeholder="https://linkedin.com/in/...">
                    </div>
                    <div>
                        <label class="text-[11px] font-medium text-slate-400 mb-1 block">Портфолио / Сайт</label>
                        <input id="p-portfolio" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white" value="${escapeHtml(c.portfolio || '')}" placeholder="https://...">
                    </div>
                </div>
            </div>

            <!-- 3. Skills & ATS Keywords -->
            <div class="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
                <h3 class="text-xs font-bold text-sky-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <span>⚡</span> Ключевые навыки (ATS & Matching)
                </h3>
                <p class="text-[11px] text-slate-500 mb-2">Список тегов через запятую — используется для расчета % совпадения с вакансией</p>
                <input id="p-keys" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-mono" value="${escapeHtml(p.keywords || '')}">
            </div>

            <!-- 4. Summary -->
            <div class="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
                <h3 class="text-xs font-bold text-sky-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <span>📝</span> О себе (Professional Summary)
                </h3>
                <textarea id="p-summary" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-300 h-24 focus:outline-none focus:border-sky-500 leading-relaxed font-sans">${escapeHtml(p.summary || '')}</textarea>
            </div>

            <!-- 5. Structured Work Experience -->
            <div class="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-xs font-bold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                        <span>💼</span> Места работы (Структурированный опыт)
                    </h3>
                    <button type="button" onclick="addExperienceRow()" class="text-[11px] bg-sky-950 hover:bg-sky-900 border border-sky-800 text-sky-300 px-2.5 py-1 rounded-lg transition-colors flex items-center gap-1">
                        <span>+</span> Добавить место работы
                    </button>
                </div>
                <div id="exp-rows-container" class="flex flex-col gap-3">
                    ${expList.map((job, idx) => `
                        <div class="exp-row bg-slate-900/90 p-3.5 rounded-lg border border-slate-700/80 flex flex-col gap-2.5">
                            <div class="grid grid-cols-12 gap-2.5">
                                <div class="col-span-5">
                                    <label class="text-[10px] text-slate-400 block mb-0.5">Должность / Позиция</label>
                                    <input class="exp-role w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white font-medium" value="${escapeHtml(job.role || '')}" placeholder="Senior Frontend Engineer">
                                </div>
                                <div class="col-span-4">
                                    <label class="text-[10px] text-slate-400 block mb-0.5">Компания / Проект</label>
                                    <input class="exp-company w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white" value="${escapeHtml(job.company || '')}" placeholder="Название компании">
                                </div>
                                <div class="col-span-2">
                                    <label class="text-[10px] text-slate-400 block mb-0.5">Период</label>
                                    <input class="exp-period w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-white font-mono text-center" value="${escapeHtml(job.period || '')}" placeholder="2023 — н.в.">
                                </div>
                                <div class="col-span-1 text-right pt-4">
                                    <button type="button" onclick="this.closest('.exp-row').remove()" class="text-rose-400 hover:text-rose-300 p-1.5 text-xs" title="Удалить">🗑️</button>
                                </div>
                            </div>
                            <div>
                                <label class="text-[10px] text-slate-400 block mb-0.5">Краткое описание / Стек технологий</label>
                                <input class="exp-desc w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-300" value="${escapeHtml(job.description || '')}" placeholder="Краткая суть проекта и стек">
                            </div>
                            <div>
                                <label class="text-[10px] text-slate-400 block mb-0.5">Ключевые достижения и результаты (по одному на строку)</label>
                                <textarea class="exp-bullets w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs text-slate-300 h-20 focus:outline-none focus:border-sky-500 leading-relaxed font-sans" placeholder="• Описание достижения...">${escapeHtml((job.bullets || []).join('\n'))}</textarea>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <div class="mt-3 pt-3 border-t border-slate-800">
                    <label class="text-[11px] font-medium text-slate-400 mb-1 block">Полный текст опыта (для генератора питчей и резюме)</label>
                    <textarea id="p-exp" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-300 h-36 focus:outline-none focus:border-sky-500 leading-relaxed font-sans">${escapeHtml(p.experience || '')}</textarea>
                </div>
            </div>

            <!-- 6. Education with Editable Grades -->
            <div class="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-xs font-bold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                        <span>🎓</span> Образование (Грейды, Специальности, ВУЗы)
                    </h3>
                    <button onclick="addEducationRow()" class="text-[11px] bg-sky-950 hover:bg-sky-900 border border-sky-800 text-sky-300 px-2.5 py-1 rounded-lg transition-colors flex items-center gap-1">
                        <span>+</span> Добавить образование
                    </button>
                </div>
                <div id="edu-rows-container" class="flex flex-col gap-2.5">
                    ${eduList.map((e, idx) => `
                        <div class="edu-row grid grid-cols-12 gap-2 bg-slate-900/90 p-2.5 rounded-lg border border-slate-700/80 items-center">
                            <div class="col-span-3">
                                <label class="text-[10px] text-slate-500 block mb-0.5">Грейд / Уровень</label>
                                <input class="edu-grade w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white" value="${escapeHtml(e.grade || '')}" placeholder="Магистратура, Бакалавр...">
                            </div>
                            <div class="col-span-4">
                                <label class="text-[10px] text-slate-500 block mb-0.5">Специальность / Программа</label>
                                <input class="edu-field w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white" value="${escapeHtml(e.field || '')}" placeholder="PR и маркетинг...">
                            </div>
                            <div class="col-span-3">
                                <label class="text-[10px] text-slate-500 block mb-0.5">ВУЗ / Организация</label>
                                <input class="edu-inst w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white" value="${escapeHtml(e.institution || '')}" placeholder="РУТ (МИИТ)...">
                            </div>
                            <div class="col-span-1">
                                <label class="text-[10px] text-slate-500 block mb-0.5">Годы</label>
                                <input class="edu-years w-full bg-slate-950 border border-slate-700 rounded px-1.5 py-1 text-xs text-white font-mono text-center" value="${escapeHtml(e.years || '')}" placeholder="2015-2017">
                            </div>
                            <div class="col-span-1 text-right pt-3">
                                <button onclick="this.closest('.edu-row').remove()" class="text-rose-400 hover:text-rose-300 p-1 text-xs" title="Удалить">🗑️</button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- 7. Languages -->
            <div class="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-xs font-bold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                        <span>🌐</span> Знание языков
                    </h3>
                    <button onclick="addLanguageRow()" class="text-[11px] bg-sky-950 hover:bg-sky-900 border border-sky-800 text-sky-300 px-2.5 py-1 rounded-lg transition-colors flex items-center gap-1">
                        <span>+</span> Добавить язык
                    </button>
                </div>
                <div id="lang-rows-container" class="flex flex-col gap-2">
                    ${langList.map((l, idx) => `
                        <div class="lang-row flex gap-2 items-center bg-slate-900/90 p-2 rounded-lg border border-slate-700/80">
                            <input class="lang-name flex-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white" value="${escapeHtml(l.language || '')}" placeholder="Язык (например: Английский)">
                            <input class="lang-level flex-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white" value="${escapeHtml(l.level || '')}" placeholder="Уровень (например: B2, родной)">
                            <button onclick="this.closest('.lang-row').remove()" class="text-rose-400 hover:text-rose-300 px-2 py-1 text-xs" title="Удалить">🗑️</button>
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- Save Actions -->
            <div class="flex gap-2 pt-3 border-t border-slate-800 sticky bottom-0 bg-slate-900/95 py-2.5">
                <button onclick="saveProfiles()" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-5 py-2.5 rounded-lg flex items-center gap-2 shadow-lg transition-colors">
                    <span>💾</span> Сохранить профиль
                </button>
                <button onclick="deleteProfile()" class="bg-rose-900/30 hover:bg-rose-900/60 text-rose-300 border border-rose-800/80 text-xs font-medium px-3.5 py-2.5 rounded-lg ml-auto transition-colors">
                    🗑️ Удалить профиль
                </button>
            </div>
        </div>
    `;
}

function addExperienceRow() {
    const container = document.getElementById('exp-rows-container');
    if (!container) return;
    const div = document.createElement('div');
    div.className = "exp-row bg-slate-900/90 p-3.5 rounded-lg border border-slate-700/80 flex flex-col gap-2.5";
    div.innerHTML = `
        <div class="grid grid-cols-12 gap-2.5">
            <div class="col-span-5">
                <label class="text-[10px] text-slate-400 block mb-0.5">Должность / Позиция</label>
                <input class="exp-role w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white font-medium" placeholder="Senior Frontend Engineer">
            </div>
            <div class="col-span-4">
                <label class="text-[10px] text-slate-400 block mb-0.5">Компания / Проект</label>
                <input class="exp-company w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white" placeholder="Название компании">
            </div>
            <div class="col-span-2">
                <label class="text-[10px] text-slate-400 block mb-0.5">Период</label>
                <input class="exp-period w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-white font-mono text-center" placeholder="2023 — н.в.">
            </div>
            <div class="col-span-1 text-right pt-4">
                <button type="button" onclick="this.closest('.exp-row').remove()" class="text-rose-400 hover:text-rose-300 p-1.5 text-xs" title="Удалить">🗑️</button>
            </div>
        </div>
        <div>
            <label class="text-[10px] text-slate-400 block mb-0.5">Краткое описание / Стек</label>
            <input class="exp-desc w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-300" placeholder="Краткая суть проекта и стек">
        </div>
        <div>
            <label class="text-[10px] text-slate-400 block mb-0.5">Ключевые достижения и результаты (по одному на строку)</label>
            <textarea class="exp-bullets w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs text-slate-300 h-20 focus:outline-none focus:border-sky-500 leading-relaxed font-sans" placeholder="• Описание достижения..."></textarea>
        </div>
    `;
    container.appendChild(div);
}

function addEducationRow() {
    const container = document.getElementById('edu-rows-container');
    if (!container) return;
    const div = document.createElement('div');
    div.className = "edu-row grid grid-cols-12 gap-2 bg-slate-900/90 p-2.5 rounded-lg border border-slate-700/80 items-center";
    div.innerHTML = `
        <div class="col-span-3">
            <label class="text-[10px] text-slate-500 block mb-0.5">Грейд / Уровень</label>
            <input class="edu-grade w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white" placeholder="Магистратура, Бакалавр...">
        </div>
        <div class="col-span-4">
            <label class="text-[10px] text-slate-500 block mb-0.5">Специальность / Программа</label>
            <input class="edu-field w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white" placeholder="Специальность...">
        </div>
        <div class="col-span-3">
            <label class="text-[10px] text-slate-500 block mb-0.5">ВУЗ / Организация</label>
            <input class="edu-inst w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white" placeholder="ВУЗ...">
        </div>
        <div class="col-span-1">
            <label class="text-[10px] text-slate-500 block mb-0.5">Годы</label>
            <input class="edu-years w-full bg-slate-950 border border-slate-700 rounded px-1.5 py-1 text-xs text-white font-mono text-center" placeholder="2015-2017">
        </div>
        <div class="col-span-1 text-right pt-3">
            <button onclick="this.closest('.edu-row').remove()" class="text-rose-400 hover:text-rose-300 p-1 text-xs" title="Удалить">🗑️</button>
        </div>
    `;
    container.appendChild(div);
}

function addLanguageRow() {
    const container = document.getElementById('lang-rows-container');
    if (!container) return;
    const div = document.createElement('div');
    div.className = "lang-row flex gap-2 items-center bg-slate-900/90 p-2 rounded-lg border border-slate-700/80";
    div.innerHTML = `
        <input class="lang-name flex-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white" placeholder="Язык">
        <input class="lang-level flex-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white" placeholder="Уровень">
        <button onclick="this.closest('.lang-row').remove()" class="text-rose-400 hover:text-rose-300 px-2 py-1 text-xs" title="Удалить">🗑️</button>
    `;
    container.appendChild(div);
}

async function saveProfiles() {
    if (currentProfile === null || !profiles[currentProfile]) return;
    const p = profiles[currentProfile];

    p.id = document.getElementById('p-id').value.trim() || ('profile_' + Date.now());
    p.lang = document.getElementById('p-lang').value;
    p.role = document.getElementById('p-role').value;
    p.name = document.getElementById('p-name').value;
    p.photo_url = document.getElementById('p-photo').value;
    p.summary = document.getElementById('p-summary').value;
    p.keywords = document.getElementById('p-keys').value;
    p.experience = document.getElementById('p-exp').value;

    p.location = p.location || {};
    p.location.city = document.getElementById('p-city').value;

    p.contacts_structured = p.contacts_structured || {};
    p.contacts_structured.telegram = document.getElementById('p-tg').value;
    p.contacts_structured.email = document.getElementById('p-email').value;
    p.contacts_structured.phone = document.getElementById('p-phone').value;
    p.contacts_structured.github = document.getElementById('p-gh').value;
    p.contacts_structured.linkedin = document.getElementById('p-li').value;
    p.contacts_structured.portfolio = document.getElementById('p-portfolio').value;

    p.contacts = [
        p.contacts_structured.telegram,
        p.contacts_structured.email,
        p.contacts_structured.phone,
        p.contacts_structured.github,
        p.contacts_structured.linkedin
    ].filter(Boolean).join(' | ');

    // Collect structured experience rows
    const expRows = document.querySelectorAll('#exp-rows-container .exp-row');
    p.experience_structured = [];
    expRows.forEach(row => {
        const role = row.querySelector('.exp-role')?.value.trim();
        const company = row.querySelector('.exp-company')?.value.trim();
        const period = row.querySelector('.exp-period')?.value.trim();
        const description = row.querySelector('.exp-desc')?.value.trim();
        const bulletsRaw = row.querySelector('.exp-bullets')?.value || '';
        const bullets = bulletsRaw.split('\n').map(b => b.trim().replace(/^[•\-\*]\s*/, '')).filter(Boolean);
        if (role || company || description || bullets.length > 0) {
            p.experience_structured.push({ role, company, period, description, bullets });
        }
    });

    // Collect education rows
    const eduRows = document.querySelectorAll('#edu-rows-container .edu-row');
    p.education = [];
    eduRows.forEach(row => {
        const grade = row.querySelector('.edu-grade')?.value.trim();
        const field = row.querySelector('.edu-field')?.value.trim();
        const institution = row.querySelector('.edu-inst')?.value.trim();
        const years = row.querySelector('.edu-years')?.value.trim();
        if (grade || field || institution) {
            p.education.push({ grade, field, institution, years });
        }
    });

    // Collect language rows
    const langRows = document.querySelectorAll('#lang-rows-container .lang-row');
    p.languages = [];
    langRows.forEach(row => {
        const language = row.querySelector('.lang-name')?.value.trim();
        const level = row.querySelector('.lang-level')?.value.trim();
        if (language) {
            p.languages.push({ language, level });
        }
    });

    try {
        const data = await api.saveProfiles(profiles);
        if (data.success) {
            showToast(`✅ Профиль «${p.name || p.role}» успешно сохранен!`);
            renderProfilesList();
            renderProfileEditor();
        } else {
            showToast(`❌ Ошибка сохранения: ${data.error}`, 3000);
        }
    } catch (e) {
        showToast(`❌ Ошибка сети при сохранении`, 3000);
    }
}

async function deleteProfile() {
    if (currentProfile === null || !profiles[currentProfile]) return;
    const p = profiles[currentProfile];
    if (!confirm(`Удалить профиль «${p.name || p.role}»?`)) return;

    profiles.splice(currentProfile, 1);
    currentProfile = profiles.length > 0 ? 0 : null;

    try {
        await api.saveProfiles(profiles);
        showToast('🗑️ Профиль удален');
        renderProfilesList();
        renderProfileEditor();
    } catch (e) {
        showToast('❌ Ошибка сети при удалении', 3000);
    }
}

async function uploadResume(input) {
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];
    const status = document.getElementById('resume-status');
    if (status) status.innerHTML = `<span class="text-sky-400 animate-pulse">Парсинг через Gemini...</span>`;

    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const data = await api.uploadResume(file.name, e.target.result);
            if (data.success && data.profile) {
                profiles[currentProfile] = Object.assign(profiles[currentProfile] || {}, data.profile);
                await api.saveProfiles(profiles);
                showToast('✅ Резюме распарсено и сохранено!');
                renderProfilesList();
                renderProfileEditor();
                if (status) status.innerHTML = `<span class="text-emerald-400 font-medium">✅ Распарсено и сохранено!</span>`;
            } else {
                if (status) status.innerHTML = `<span class="text-rose-400">❌ ${data.error || 'Ошибка'}</span>`;
            }
        } catch (err) {
            if (status) status.innerHTML = `<span class="text-rose-400">❌ Ошибка сети</span>`;
        }
    };
    reader.readAsDataURL(file);
}

// --- CROPPER ---
function initCrop(input) {
    if (input.files && input.files[0]) {
        const r = new FileReader();
        r.onload = (e) => {
            const img = document.getElementById('cropper-image');
            img.src = e.target.result;
            img.classList.remove('hidden');
            toggleModal('cropper-modal');
            if (cropper) cropper.destroy();
            cropper = new Cropper(img, { aspectRatio: 1, viewMode: 2 });
        };
        r.readAsDataURL(input.files[0]);
    }
}

function saveCrop() {
    if (!cropper) return;
    const canvas = cropper.getCroppedCanvas({ width: 400, height: 400 });
    document.getElementById('p-photo').value = canvas.toDataURL('image/jpeg', 0.85);
    toggleModal('cropper-modal');
    saveProfiles();
}
