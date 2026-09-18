// ==========================================
// Job Hunter CRM — Application Bootstrap
// ==========================================

async function checkCdpStatus() {
    try {
        const data = await api.getCdpStatus();
        const dot = document.getElementById('cdp-dot');
        const text = document.getElementById('cdp-text');
        if (data && data.cdp_available) {
            if (dot) dot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-pulse';
            if (text) text.innerText = 'Chrome 9222 Active';
        } else {
            if (dot) dot.className = 'w-2 h-2 rounded-full bg-slate-500';
            if (text) text.innerText = 'Chrome Offline';
        }
    } catch (e) {}
}

async function launchChromeAgent() {
    showToast('🚀 Запуск Google Chrome на порту 9222...');
    try {
        const data = await api.launchCdp();
        if (data && (data.cdp_available || data.success)) {
            showToast('✅ Chrome успешно запущен и готов к откликам!');
            checkCdpStatus();
        } else {
            showToast('⚠️ Chrome запускается... Окно скоро появится.');
            setTimeout(checkCdpStatus, 2000);
        }
    } catch (e) {
        showToast('❌ Ошибка запуска Chrome');
    }
}

window.onload = async () => {
    initBookmarklet();
    await loadProfilesList();
    await loadConfig();
    await loadPitches();
    await checkCdpStatus();
    setInterval(checkCdpStatus, 8000);
};

