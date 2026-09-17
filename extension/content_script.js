// ===================================================
// Job Hunter Chrome Extension — Message Orchestrator
// Thin router — delegates to core, adapters, autofill, automation
// ===================================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "EXTRACT_PAGE_DATA") {
    const data = JH.adapters.extractJobPostingData();
    sendResponse(data);

  } else if (message.type === "AUTOFILL_PAGE") {
    autofillFormOnPage(message.candidateData, message.coverLetter)
      .then(res => sendResponse(res))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;

  } else if (message.type === "AUTO_SUBMIT_PAGE") {
    JH.automation.autoSubmitWithDetection(message.candidateData, message.coverLetter)
      .then(res => sendResponse(res))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;

  } else if (message.type === "SHOW_RESULT_OVERLAY") {
    JH.showResultOverlay(message);
    sendResponse({ ok: true });
  }
});
