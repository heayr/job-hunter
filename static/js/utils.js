// ==========================================
// Job Hunter CRM — Utility Functions
// ==========================================

function formatRelativeTime(isoStr) {
    if (!isoStr) return '';
    try {
        const d = new Date(isoStr.replace(' ', 'T'));
        if (isNaN(d.getTime())) return isoStr;
        const now = new Date();
        const diffMs = now - d;
        const diffMin = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMin / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMin < 1) return 'только что';
        if (diffMin < 60) return `${diffMin} мин назад`;
        if (diffHours < 24) return `${diffHours} ч назад`;
        if (diffDays === 1) return 'вчера';
        if (diffDays < 7) return `${diffDays} дн назад`;
        return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
    } catch(e) {
        return isoStr;
    }
}

function parseSalaryValue(salaryStr) {
    if (!salaryStr || salaryStr === 'Не указана') return 0;
    const nums = salaryStr.replace(/\s+/g, '').match(/\d+/g);
    if (!nums || nums.length === 0) return 0;
    return parseInt(nums[nums.length - 1], 10);
}

function cleanCompanyName(rawCompany, title, desc) {
    if (!rawCompany) return 'Компания';
    let c = rawCompany.trim();

    // 1. If it has a clean recognizable brand at the start
    const brandMatch = c.match(/^(FinTech Global|NextGen Cloud|Web3Core|CryptoPay|Buymie|Yandex|VK|Tinkoff|Ozon|Avito|Sber|Wildberries|Kaspi|Revolut|Telegram|Miro|Playrix|JetBrains|EPAM|Luxoft)\b/i);
    if (brandMatch) {
        return brandMatch[1];
    }

    // 2. Remove common vacancy title artifacts concatenated into company name
    c = c.replace(/\s*(?:ищет|в поисках|набирает|открывает позицию|вакансия).*$/i, '');
    c = c.replace(/\s*(?:Senior|Middle|Junior|Lead|Principal|Team Lead|Fullstack|Frontend|Backend|Developer|Engineer|Разработчик).*$/i, '');
    c = c.replace(/\s*(?:\(.*\)|\[.*\])$/, '');
    c = c.replace(/\s*ООО\s*/gi, '').replace(/\s*ЗАО\s*/gi, '').replace(/\s*LLC\s*/gi, '').replace(/\s*Inc\.?\s*/gi, '');
    c = c.replace(/^[«"']+|[»"']+$/g, '').trim();

    // 3. If cleaned name is too long or generic, try extracting from title
    if (c.length > 28 || c.toLowerCase() === 'direct employer' || c.toLowerCase() === 'компания') {
        const titleMatch = (title || '').match(/^(?:Компания\s+)?([A-ZА-Я][A-Za-zА-Яа-я0-9\s]{2,20})\s+(?:ищет|в поисках|открывает|набирает)/i);
        if (titleMatch && titleMatch[1]) {
            return titleMatch[1].trim();
        }
    }

    return c.trim() || 'Компания';
}

function formatVacancyUrl(url) {
    if (!url) return '#';
    let u = url.trim();
    if (u.startsWith('@')) return `https://t.me/${u.slice(1)}`;
    if (u.includes('@') && !u.startsWith('http') && !u.startsWith('mailto:')) return `mailto:${u}`;
    if (!u.startsWith('http') && !u.startsWith('tg://') && !u.startsWith('mailto:') && !u.startsWith('#')) return `https://${u}`;
    return u;
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showToast(msg, duration = 2500) {
    let t = document.getElementById('app-toast');
    if (!t) {
        t = document.createElement('div');
        t.id = 'app-toast';
        t.className = 'fixed bottom-5 right-5 bg-slate-800 border border-slate-700 text-white px-4 py-3 rounded-xl shadow-2xl z-50 transition-all transform translate-y-10 opacity-0 pointer-events-none text-sm flex items-center gap-2';
        document.body.appendChild(t);
    }
    t.innerHTML = msg;
    t.classList.remove('translate-y-10', 'opacity-0', 'pointer-events-none');
    setTimeout(() => {
        t.classList.add('translate-y-10', 'opacity-0', 'pointer-events-none');
    }, duration);
}

function copyText(text, btnId) {
    navigator.clipboard.writeText(text);
    const btn = document.getElementById(btnId);
    if (btn) {
        const original = btn.innerHTML;
        btn.innerHTML = '✅ Скопировано!';
        btn.classList.add('border-emerald-500', 'text-emerald-400');
        setTimeout(() => {
            btn.innerHTML = original;
            btn.classList.remove('border-emerald-500', 'text-emerald-400');
        }, 2000);
    }
}
