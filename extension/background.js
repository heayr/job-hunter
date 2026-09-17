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

// 2. Poll CRM for autonomous apply tasks every 4 seconds
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
    }
  } catch (err) {
    // CRM offline or network issue
  } finally {
    isPolling = false;
  }
}

// 3. Execute Autonomous Apply Task in browser
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

  // Create a new background tab
  let tab = null;
  try {
    tab = await chrome.tabs.create({ url: task.url, active: false });
  } catch (err) {
    console.error("[JobHunter Agent] Failed to create tab:", err);
    await reportTaskStatus(task.id, task.vacancy_id, "FAILED", `Failed to open tab: ${err.message}`);
    return;
  }

  // Wait for tab to finish loading
  await waitForTabComplete(tab.id, 25000);

  // Give dynamic JavaScript frameworks (React / Vue) a moment to render DOM
  await new Promise(r => setTimeout(r, 2000));

  // Send message to content script to perform auto-fill
  try {
    const fillResult = await new Promise((resolve, reject) => {
      chrome.tabs.sendMessage(tab.id, {
        type: "AUTOFILL_PAGE",
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

    if (fillResult.success && fillResult.filledCount > 0) {
      console.log("[JobHunter Agent] Task SUCCESS:", fillResult);
      await reportTaskStatus(
        task.id,
        task.vacancy_id,
        "COMPLETED",
        `Заполнено ${fillResult.filledCount} полей (${fillResult.filledFields.join(", ")})`
      );

      // Record in application history
      await fetch(`${CRM_URL}/api/applications/record`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vacancy_id: task.vacancy_id,
          company: task.company,
          role_title: task.role_title,
          portal: task.portal || "web",
          mode: "AUTO",
          fsm_state: "SUBMITTED",
          metadata: {
            task_id: task.id,
            filled_count: fillResult.filledCount,
            fields: fillResult.filledFields
          }
        })
      });
    } else {
      await reportTaskStatus(task.id, task.vacancy_id, "FAILED", "Форма не найдена на странице вакансии");
    }
  } catch (err) {
    console.error("[JobHunter Agent] Execution error:", err);
    await reportTaskStatus(task.id, task.vacancy_id, "FAILED", err.message);
  } finally {
    // Graceful close of tab after submission
    setTimeout(() => {
      if (tab && tab.id) {
        chrome.tabs.remove(tab.id).catch(() => {});
      }
    }, 3000);
  }
}

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

// Start polling interval
setInterval(checkPendingTasks, 3500);

// Listen for tab activation to notify side panel of URL change
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
