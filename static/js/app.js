// ==========================================
// Job Hunter CRM — Application Bootstrap
// ==========================================

window.onload = async () => {
    initBookmarklet();
    await loadProfilesList();
    await loadConfig();
    await loadPitches();
};
