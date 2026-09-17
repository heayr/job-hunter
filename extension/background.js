// ===================================================
// Job Hunter Chrome Extension — Autonomous Agent Background Worker
// ===================================================

const CRM_URL = "http://127.0.0.1:8115";
let isPolling = false;

// 1. Open popup / side panel behavior
if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((error) => console.error("[JobHunter BG] Error setting panel behavior:", error));
}

// ── Anti-detection utilities ───────────────────────

function bgRandomDelay(minMs, maxMs) {
  const delay = Math.floor(Math.random() * (maxMs - minMs) + minMs);
  return new Promise(r => setTimeout(r, delay));
}

// ── Task Queue Polling ─────────────────────────────

async function checkPendingTasks() {
  if (isPolling) return;
  isPolling = true;

  try {
    const res = await fetch(`${CRM_URL}/api/agent/pending-tasks`);
    if (!res.ok) {
      isPolling = false;
      return;
    }
    const data = await res.json();
    const tasks = data.tasks || [];

    for (const task of tasks) {
      await executeAutonomousTask(task);

      // Inter-task cooldown (5-15 seconds random) to avoid bot detection
      if (tasks.indexOf(task) < tasks.length - 1) {
        const cooldown = 5000 + Math.floor(Math.random() * 10000);
        console.log(`[JobHunter BG] Cooldown ${Math.round(cooldown/1000)}s before next task...`);
        await new Promise(r => setTimeout(r, cooldown));
      }
    }
  } catch (err) {
    // CRM offline or network issue
  } finally {
    isPolling = false;
  }
}

// ── Task Execution ─────────────────────────────────

async function executeAutonomousTask(task) {
  console.log("[JobHunter Agent] Executing task for vacancy:", task.vacancy_id, task.url);

  // Fetch candidate profile from CRM
  let candidateData = {};
  try {
    const profRes = await fetch(`${CRM_URL}/api/profiles`);
    const profiles = await profRes.json();
    candidateData = (profiles && profiles[0]) || {};
  } catch (e) {
    console.warn("[JobHunter Agent] Could not fetch profile:", e);
  }

  // Determine execution mode: AUTO = auto-submit, SEMI_AUTO = fill only
  const mode = task.mode || "SEMI_AUTO";

  // Notify user: task is starting
  chrome.notifications?.create(`jh-task-${task.id}`, {
    type: "basic",
    iconUrl: "icon.png",
    title: "Job Hunter — Отклик",
    message: `${mode === 'AUTO' ? '🤖 Авто-отклик' : '📝 Заполнение'}: ${task.company} — ${task.role_title}...`,
    priority: 2
  });

  // Create a new tab (visible to user)
  let tab = null;
  try {
    tab = await chrome.tabs.create({ url: task.url, active: true });
  } catch (err) {
    console.error("[JobHunter Agent] Failed to create tab:", err);
    await reportTaskStatus(task.id, task.vacancy_id, "FAILED", `Failed to open tab: ${err.message}`);
    return;
  }

  // Wait for tab to finish loading
  await waitForTabComplete(tab.id, 25000);

  // Anti-detection: randomized delay for framework rendering (1.5-4s)
  const renderDelay = 1500 + Math.floor(Math.random() * 2500);
  await new Promise(r => setTimeout(r, renderDelay));

  // Choose message type based on mode
  const messageType = mode === "AUTO" ? "AUTO_SUBMIT_PAGE" : "AUTOFILL_PAGE";

  try {
    const result = await new Promise((resolve, reject) => {
      chrome.tabs.sendMessage(tab.id, {
        type: messageType,
        candidateData: candidateData,
        coverLetter: task.cover_letter || ""
      }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(response || { success: false, filledCount: 0 });
        }
      });
    });

    if (result.success && result.filledCount > 0) {
      console.log("[JobHunter Agent] Task SUCCESS:", result);
      const actionLabel = result.action === 'submitted' ? '✅ Авто-отправлено' :
                          result.action === 'step_advanced' ? '⏭ Шаг пройден' :
                          result.action === 'ready_to_submit' ? '📝 Готово к отправке' :
                          '📝 Заполнено';
      const summary = `${actionLabel}: ${result.filledCount} полей (${result.filledFields.join(", ")})`;

      // Determine final FSM state
      const fsmState = result.action === 'submitted' ? 'SUBMITTED' :
                       result.action === 'captcha_blocked' ? 'WAITING_APPROVAL' :
                       'WAITING_APPROVAL';

      await reportTaskStatus(task.id, task.vacancy_id, "COMPLETED", summary);

      // Record in application history
      await fetch(`${CRM_URL}/api/applications/record`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vacancy_id: task.vacancy_id,
          company: task.company,
          role_title: task.role_title,
          portal: task.portal || "web",
          mode: mode,
          fsm_state: fsmState,
          metadata: {
            task_id: task.id,
            filled_count: result.filledCount,
            fields: result.filledFields,
            action: result.action,
            captcha: result.captcha ? result.captcha.type : null
          }
        })
      });

      // Show result overlay on the page
      chrome.tabs.sendMessage(tab.id, {
        type: "SHOW_RESULT_OVERLAY",
        success: true,
        filledCount: result.filledCount,
        filledFields: result.filledFields,
        platform: result.platform,
        company: task.company,
        role: task.role_title
      }).catch(() => {});

      // Notification
      const notifTitle = result.action === 'submitted'
        ? `✅ Авто-отправлено — ${task.company}`
        : result.action === 'captcha_blocked'
        ? `⚠️ CAPTCHA — ${task.company}`
        : `✅ Отклик заполнен — ${task.company}`;
      const notifMsg = result.action === 'captcha_blocked'
        ? `CAPTCHA обнаружен (${result.captcha?.type}). Форма заполнена, нужна ручная отправка.`
        : result.action === 'submitted'
        ? `Отклик успешно отправлен через ${result.platform || 'форму'}`
        : summary;

      chrome.notifications?.create(`jh-done-${task.id}`, {
        type: "basic",
        iconUrl: "icon.png",
        title: notifTitle,
        message: notifMsg,
        priority: 2
      });

    } else if (result.action === 'rate_limited') {
      await reportTaskStatus(task.id, task.vacancy_id, "FAILED", result.error);
      chrome.notifications?.create(`jh-rate-${task.id}`, {
        type: "basic",
        iconUrl: "icon.png",
        title: `⏱ Лимит — ${task.company}`,
        message: result.error,
        priority: 2
      });

    } else {
      await reportTaskStatus(task.id, task.vacancy_id, "FAILED", result.error || "Форма не найдена на странице вакансии");

      chrome.notifications?.create(`jh-fail-${task.id}`, {
        type: "basic",
        iconUrl: "icon.png",
        title: `❌ Форма не найдена — ${task.company}`,
        message: "Откройте форму отклика вручную и нажмите 'Заполнить' в Side Panel",
        priority: 2
      });
    }
  } catch (err) {
    console.error("[JobHunter Agent] Execution error:", err);
    await reportTaskStatus(task.id, task.vacancy_id, "FAILED", err.message);

    chrome.notifications?.create(`jh-err-${task.id}`, {
      type: "basic",
      iconUrl: "icon.png",
      title: `❌ Ошибка — ${task.company}`,
      message: err.message || "Не удалось заполнить форму. Проверьте консоль.",
      priority: 2
    });
  }
}

// ── Tab Lifecycle ──────────────────────────────────

function waitForTabComplete(tabId, timeoutMs = 20000) {
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      resolve(false);
    }, timeoutMs);

    function listener(id, changeInfo) {
      if (id === tabId && changeInfo.status === "complete") {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve(true);
      }
    }
    chrome.tabs.onUpdated.addListener(listener);
  });
}

// ── CRM Communication ─────────────────────────────

async function reportTaskStatus(taskId, vacancyId, status, message) {
  try {
    await fetch(`${CRM_URL}/api/agent/task-status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_id: taskId,
        vacancy_id: vacancyId,
        status: status,
        result_message: message
      })
    });
  } catch (e) {
    console.error("[JobHunter Agent] Failed to report task status:", e);
  }
}

// ── Tab Activation Listener ────────────────────────

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (tab && tab.url && !tab.url.startsWith("chrome://")) {
      chrome.runtime.sendMessage({
        type: "TAB_CHANGED",
        tabId: activeInfo.tabId,
        url: tab.url,
        title: tab.title
      }).catch(() => {});
    }
  } catch (err) {}
});

// ── Start Polling ──────────────────────────────────
setInterval(checkPendingTasks, 3500);
