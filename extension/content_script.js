// ===================================================
// Job Hunter Chrome Extension — Message Orchestrator
// Thin router — delegates to core, adapters, autofill, automation
// ===================================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // ── Existing High-Level Commands ──
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

  // ── Atomic Agent Browser Actions (Phase 1: Browser Hands) ──

  } else if (message.type === "INSPECT_PAGE" || message.type === "INSPECT_FORM") {
    try {
      const observation = JH.inspectPageSemantics(message.options || {});
      sendResponse({ success: true, observation });
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }

  } else if (message.type === "FILL_FIELD") {
    (async () => {
      try {
        const el = JH.getElementByAgentId(message.element_id);
        if (!el) {
          sendResponse({ success: false, error: `Element '${message.element_id}' not found on page` });
          return;
        }

        const useHumanType = message.typing_speed === 'human' || message.human_like;
        let fillOk = false;
        if (useHumanType) {
          fillOk = await JH.humanType(el, message.value);
        } else {
          fillOk = JH.setFieldValue(el, message.value);
        }

        // Check if field triggered error immediately
        const error = el.getAttribute('aria-invalid') === 'true' ||
                      (el.parentElement && el.parentElement.querySelector('.error, .invalid-feedback') !== null);

        sendResponse({
          success: fillOk,
          element_id: message.element_id,
          applied_value: el.value || '',
          validation_error: error
        });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;

  } else if (message.type === "SELECT_OPTION") {
    try {
      const el = JH.getElementByAgentId(message.element_id);
      if (!el) {
        sendResponse({ success: false, error: `Element '${message.element_id}' not found on page` });
        return;
      }
      const res = JH.selectOption(el, message.option);
      sendResponse(res);
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }

  } else if (message.type === "CLICK_ELEMENT") {
    (async () => {
      try {
        const el = JH.getElementByAgentId(message.element_id);
        if (!el) {
          sendResponse({ success: false, error: `Element '${message.element_id}' not found on page` });
          return;
        }

        const prevUrl = window.location.href;
        await JH.simulateClick(el);

        // Small grace period to allow DOM mutations / URL changes
        await JH.randomDelay(200, 450);

        const newUrl = window.location.href;
        sendResponse({
          success: true,
          element_id: message.element_id,
          url_changed: newUrl !== prevUrl,
          current_url: newUrl
        });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;

  } else if (message.type === "UPLOAD_FILE") {
    try {
      const el = JH.getElementByAgentId(message.element_id);
      if (!el) {
        sendResponse({ success: false, error: `Element '${message.element_id}' not found on page` });
        return;
      }
      const res = JH.injectFile(el, message.file_base64, message.file_name, message.mime_type);
      sendResponse(res);
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }

  } else if (message.type === "SCROLL_PAGE") {
    try {
      const res = JH.scrollPage(message.direction || 'down', message.pixels || 400);
      sendResponse(res);
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }
  }
});

