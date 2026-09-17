// ===================================================
// Job Hunter Chrome Extension — Side Panel Controller
// ===================================================

const CRM_BASE_URL = "http://127.0.0.1:8115";

let currentPageData = null;
let currentCandidateData = null;
let currentGeneratedPitch = null;

let executionMode = "SEMI_AUTO"; // 'ASSIST' | 'SEMI_AUTO' | 'AUTO'

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", async () => {
  checkCrmConnection();
  loadCandidateProfile();
  refreshActiveTabData();

  // Mode Selection Listeners (Phase 16)
  const modeAssist = document.getElementById("mode-assist-btn");
  const modeSemi = document.getElementById("mode-semiauto-btn");
  const modeAuto = document.getElementById("mode-auto-btn");
  const badge = document.getElementById("active-mode-badge");
  const desc = document.getElementById("mode-desc");

  function setMode(mode) {
    executionMode = mode;
    if (badge) badge.textContent = mode;
    [modeAssist, modeSemi, modeAuto].forEach(b => {
      if (b) {
        b.style.borderColor = "#1e293b";
        b.style.background = "transparent";
        b.style.color = "var(--text-muted)";
      }
    });
    if (mode === "ASSIST") {
      if (modeAssist) {
        modeAssist.style.borderColor = "#6366f1";
        modeAssist.style.background = "rgba(99,102,241,0.2)";
        modeAssist.style.color = "#fff";
      }
      if (desc) desc.innerHTML = "<b>ASSIST:</b> Только подготовка питчей и копирование. Форма на странице не трогается.";
    } else if (mode === "SEMI_AUTO") {
      if (modeSemi) {
        modeSemi.style.borderColor = "#6366f1";
        modeSemi.style.background = "rgba(99,102,241,0.2)";
        modeSemi.style.color = "#fff";
      }
      if (desc) desc.innerHTML = "<b>SEMI-AUTO:</b> Заполнение полей формы в 1 клик с ручной финальной проверкой перед отправкой.";
    } else if (mode === "AUTO") {
      if (modeAuto) {
        modeAuto.style.borderColor = "#10b981";
        modeAuto.style.background = "rgba(16,185,129,0.2)";
        modeAuto.style.color = "#34d399";
      }
      if (desc) desc.innerHTML = "<b>AUTO:</b> Полное заполнение формы и подсветка кнопки отправки (с защитой от случайного нажатия).";
    }
  }

  modeAssist?.addEventListener("click", () => setMode("ASSIST"));
  modeSemi?.addEventListener("click", () => setMode("SEMI_AUTO"));
  modeAuto?.addEventListener("click", () => setMode("AUTO"));

  // Event Listeners
  document.getElementById("refresh-page-btn")?.addEventListener("click", refreshActiveTabData);
  document.getElementById("analyze-btn")?.addEventListener("click", runAiAnalysis);
  document.getElementById("autofill-btn")?.addEventListener("click", triggerPageAutofill);

  document.getElementById("copy-dm-btn")?.addEventListener("click", () => {
    const text = document.getElementById("dm-content")?.innerText || "";
    navigator.clipboard.writeText(text);
    showCopyFeedback("copy-dm-btn");
  });

  document.getElementById("copy-cl-btn")?.addEventListener("click", () => {
    const text = document.getElementById("cl-content")?.innerText || "";
    navigator.clipboard.writeText(text);
    showCopyFeedback("copy-cl-btn");
  });
});

// React to tab switches
chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "TAB_CHANGED") {
    refreshActiveTabData();
  }
});

/**
 * Checks if local CRM server is responding
 */
async function checkCrmConnection() {
  const badge = document.getElementById("crm-status-badge");
  try {
    const res = await fetch(`${CRM_BASE_URL}/api/status`, { method: "GET" });
    if (res.ok) {
      badge.className = "server-status";
      badge.textContent = "● CRM Online";
    } else {
      throw new Error("Bad status");
    }
  } catch (err) {
    badge.className = "server-status offline";
    badge.textContent = "○ CRM Offline (Запустите start.sh)";
  }
}

/**
 * Loads active candidate canonical profile from local CRM
 */
async function loadCandidateProfile() {
  try {
    const res = await fetch(`${CRM_BASE_URL}/api/profiles`);
    if (res.ok) {
      const profiles = await res.json();
      currentCandidateData = (profiles && profiles[0]) || null;
    }
  } catch (err) {
    console.debug("[SidePanel] Error loading candidate profile:", err);
  }
}

/**
 * Communicates with active tab content script to extract job information
 */
async function refreshActiveTabData() {
  const titleEl = document.getElementById("detected-title");
  const compEl = document.getElementById("detected-company");

  titleEl.textContent = "Определение страницы...";
  compEl.textContent = "—";

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) {
      titleEl.textContent = "Вкладка недоступна";
      return;
    }

    // Ping content script
    chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_PAGE_DATA" }, (response) => {
      if (chrome.runtime.lastError || !response) {
        titleEl.textContent = tab.title || "Веб-страница";
        compEl.textContent = tab.url ? new URL(tab.url).hostname : "";
        currentPageData = { url: tab.url, title: tab.title, company: compEl.textContent, description: "" };
        return;
      }

      currentPageData = response;
      titleEl.textContent = response.title || tab.title;
      compEl.textContent = response.company || (tab.url ? new URL(tab.url).hostname : "");
    });
  } catch (err) {
    titleEl.textContent = "Ошибка определения";
  }
}

/**
 * Invokes CRM AI Career Agent pipeline for current active vacancy
 */
async function runAiAnalysis() {
  if (!currentPageData) return;

  const btn = document.getElementById("analyze-btn");
  const msg = document.getElementById("analyze-msg");
  const scoreBadge = document.getElementById("match-score-badge");
  const scoreVal = document.getElementById("match-score-val");

  btn.disabled = true;
  btn.innerHTML = `<span class="loading-spinner"></span> Рассуждение агента...`;
  msg.style.display = "none";

  try {
    const payload = {
      input: currentPageData.url || `${currentPageData.title}\n${currentPageData.company}\n${currentPageData.description}`,
      is_url: Boolean(currentPageData.url && currentPageData.url.startsWith("http")),
      text: currentPageData.description
    };

    const res = await fetch(`${CRM_BASE_URL}/api/vacancies/ai-parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || "Ошибка при анализе вакансии");
    }

    currentGeneratedPitch = data;

    // Display match score
    const score = data.score || 70;
    scoreVal.textContent = `${score}%`;
    scoreBadge.style.display = "inline-flex";
    scoreBadge.className = `score-badge ${score >= 80 ? 'score-high' : score >= 60 ? 'score-mid' : 'score-low'}`;

    // Display Pitches
    if (data.short_dm) {
      document.getElementById("dm-card").style.display = "block";
      document.getElementById("dm-content").textContent = data.short_dm;
    }
    if (data.cover_letter) {
      document.getElementById("cl-card").style.display = "block";
      document.getElementById("cl-content").textContent = data.cover_letter;
    }

    msg.className = "alert alert-success";
    msg.textContent = `✅ Успешно проанализировано! Создана вакансия в CRM.`;
    msg.style.display = "block";
  } catch (err) {
    msg.className = "alert alert-warn";
    msg.textContent = `⚠️ ${err.message}`;
    msg.style.display = "block";
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>🪄</span> Анализировать и подготовить питч`;
  }
}

/**
 * Triggers DOM auto-fill via content script
 */
async function triggerPageAutofill() {
  const resultDiv = document.getElementById("autofill-result");
  const btn = document.getElementById("autofill-btn");

  if (!currentCandidateData) {
    await loadCandidateProfile();
  }

  const coverText = (currentGeneratedPitch && currentGeneratedPitch.cover_letter) ||
    (document.getElementById("cl-content")?.innerText) || "";

  if (executionMode === "ASSIST") {
    resultDiv.style.display = "block";
    resultDiv.className = "alert alert-warn";
    resultDiv.innerHTML = "🛡️ Режим <b>ASSIST</b>: автоматическая вставка отключена. Скопируйте питч вручную или переключитесь в <b>SEMI-AUTO</b>.";
    return;
  }

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) return;

    chrome.tabs.sendMessage(tab.id, {
      type: "AUTOFILL_PAGE",
      candidateData: currentCandidateData || {},
      coverLetter: coverText
    }, (response) => {
      resultDiv.style.display = "block";
      if (chrome.runtime.lastError || !response || !response.success) {
        resultDiv.className = "alert alert-warn";
        resultDiv.textContent = "⚠️ Поля формы не найдены или скрипт не внедрен в страницу.";
        return;
      }

      if (response.filledCount > 0) {
        resultDiv.className = "alert alert-success";
        resultDiv.innerHTML = `⚡️ Заполнено полей: <b>${response.filledCount}</b> (${response.filledFields.join(", ")})`;

        // Record application audit history (Phase 17)
        if (currentGeneratedPitch && currentGeneratedPitch.vacancy_id) {
          fetch(`${CRM_BASE_URL}/api/applications/record`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              vacancy_id: currentGeneratedPitch.vacancy_id,
              company: (currentPageData && currentPageData.company) || "Unknown",
              role_title: (currentPageData && currentPageData.title) || "Engineer",
              portal: response.platform || "web",
              mode: executionMode,
              fsm_state: "SUBMITTED",
              metadata: {
                match_score: currentGeneratedPitch.score || 0,
                filled_count: response.filledCount,
                filled_fields: response.filledFields
              }
            })
          }).catch(err => console.debug("[SidePanel] Record event error:", err));
        }
      } else {
        resultDiv.className = "alert alert-warn";
        resultDiv.textContent = "⚠️ Форма не найдена на текущем экране. Если форма в модальном окне, откройте её и нажмите снова.";
      }
    });
  } catch (err) {
    resultDiv.style.display = "block";
    resultDiv.className = "alert alert-warn";
    resultDiv.textContent = `⚠️ Ошибка: ${err.message}`;
  }
}

function showCopyFeedback(buttonId) {
  const btn = document.getElementById(buttonId);
  if (!btn) return;
  const prev = btn.textContent;
  btn.textContent = " Скопировано!";
  setTimeout(() => { btn.textContent = prev; }, 1500);
}
