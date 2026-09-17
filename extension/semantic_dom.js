// ===================================================
// Job Hunter Chrome Extension — Semantic DOM Serializer
// Inspects active page forms, assigns stable element IDs,
// and extracts compact, token-efficient observations for AI agent.
// ===================================================

(function() {
  const JH = window.JH || {};
  window.JH = JH;

  let elementIdCounter = 1;
  const elementMap = new Map(); // id -> Element

  /**
   * Resets element counter and mappings for a new inspection pass.
   */
  function resetElementMap() {
    elementIdCounter = 1;
    elementMap.clear();
  }

  /**
   * Assigns or retrieves a stable agent ID for an element.
   */
  function getOrAssignAgentId(el) {
    let id = el.getAttribute("data-jh-agent-id");
    if (!id || !elementMap.has(id)) {
      id = `elem_${elementIdCounter++}`;
      el.setAttribute("data-jh-agent-id", id);
    }
    elementMap.set(id, el);
    return id;
  }

  /**
   * Finds the most descriptive text label for an interactive element.
   */
  function resolveElementLabel(el) {
    // 1. Check aria-labelledby
    const ariaLabelledBy = el.getAttribute("aria-labelledby");
    if (ariaLabelledBy) {
      const lblEl = document.getElementById(ariaLabelledBy);
      if (lblEl && lblEl.innerText.trim()) return cleanText(lblEl.innerText);
    }

    // 2. Check aria-label
    const ariaLabel = el.getAttribute("aria-label");
    if (ariaLabel && ariaLabel.trim()) return cleanText(ariaLabel);

    // 3. Check for linked label[for="id"]
    if (el.id) {
      const labelFor = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (labelFor && labelFor.innerText.trim()) return cleanText(labelFor.innerText);
    }

    // 4. Check parent label
    const parentLabel = el.closest("label");
    if (parentLabel && parentLabel.innerText.trim()) {
      const clone = parentLabel.cloneNode(true);
      clone.querySelectorAll("input, select, textarea, button").forEach(n => n.remove());
      const txt = clone.innerText.trim();
      if (txt) return cleanText(txt);
    }

    // 5. Check placeholder
    const placeholder = el.getAttribute("placeholder");
    if (placeholder && placeholder.trim()) return cleanText(placeholder);

    // 6. Check previous sibling or parent previous sibling (common in ATS)
    let prev = el.previousElementSibling;
    while (prev) {
      if (prev.tagName === "LABEL" || prev.classList.contains("label") || prev.getAttribute("role") === "heading") {
        if (prev.innerText.trim()) return cleanText(prev.innerText);
      }
      prev = prev.previousElementSibling;
    }

    // 7. Check container heading / legend
    const fieldset = el.closest("fieldset");
    if (fieldset) {
      const legend = fieldset.querySelector("legend");
      if (legend && legend.innerText.trim()) return cleanText(legend.innerText);
    }

    const container = el.closest(".form-group, .form-field, .field, [class*='field'], [class*='input-wrapper']");
    if (container) {
      const lbl = container.querySelector("label, .label, [class*='label'], strong, b");
      if (lbl && lbl !== el && lbl.innerText.trim()) return cleanText(lbl.innerText);
    }

    return el.name || el.id || "";
  }

  function cleanText(txt) {
    return txt.replace(/[\n\r\t]+/g, " ").replace(/\s{2,}/g, " ").trim();
  }

  /**
   * Checks if an element is marked as required.
   */
  function isElementRequired(el, labelText) {
    if (el.hasAttribute("required") || el.getAttribute("aria-required") === "true") {
      return true;
    }
    if (labelText && (labelText.includes("*") || labelText.includes("обязательно") || labelText.toLowerCase().includes("required"))) {
      return true;
    }
    const parent = el.parentElement;
    if (parent && parent.querySelector(".required, [class*='required'], .asterisk, [class*='star']")) {
      return true;
    }
    return false;
  }

  /**
   * Detects visible validation error message attached to an element.
   */
  function detectElementError(el) {
    if (el.getAttribute("aria-invalid") === "true") {
      const describedBy = el.getAttribute("aria-describedby");
      if (describedBy) {
        const errEl = document.getElementById(describedBy);
        if (errEl && errEl.innerText.trim()) return cleanText(errEl.innerText);
      }
    }

    const container = el.closest(".form-group, .form-field, .field, [class*='field']") || el.parentElement;
    if (container) {
      const errEl = container.querySelector(".error, .invalid-feedback, [class*='error'], [class*='invalid'], [role='alert']");
      if (errEl && errEl.offsetParent !== null && errEl.innerText.trim()) {
        return cleanText(errEl.innerText);
      }
    }
    return null;
  }

  /**
   * Checks element visibility.
   */
  function isVisible(el) {
    if (!el) return false;
    if (el.offsetParent === null && el.style.position !== "fixed") return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  /**
   * Inspects entire page and returns a semantic observation for the agent.
   */
  JH.inspectPageSemantics = function(opts = {}) {
    resetElementMap();

    const currentUrl = window.location.href;
    const hostname = window.location.hostname;

    // ── Platform-Specific Pre-Actions & Auth Detection ──
    let authRequired = false;
    let authReason = null;

    // 1. HeadHunter (hh.ru)
    if (hostname.includes('hh.ru')) {
      if (currentUrl.includes('/account/login') || document.querySelector('[data-qa="account-login-input"], [data-qa="login-submit-form"]')) {
        authRequired = true;
        authReason = "Требуется вход в аккаунт на HH.ru";
      }

      // If response modal is open on hh.ru, auto-click letter toggle to reveal cover letter textarea!
      const letterToggle = document.querySelector('[data-qa="vacancy-response-letter-toggle"], [data-qa="vacancy-response-popup-letter-toggle"]');
      if (letterToggle && isVisible(letterToggle)) {
        try {
          letterToggle.click();
        } catch(e) {}
      }
    }

    // 2. Habr Career (career.habr.com)
    if (hostname.includes('habr.com')) {
      if (currentUrl.includes('account.habr.com/login') || document.querySelector('.user-info__login, form[action*="/login"]')) {
        if (!document.querySelector('textarea, form.new_vacancy_response')) {
          authRequired = true;
          authReason = "Требуется авторизация на Хабр Карьере";
        }
      }
    }

    // 3. SuperJob (superjob.ru)
    if (hostname.includes('superjob.ru')) {
      if (currentUrl.includes('/auth') || document.querySelector('form[action*="/auth/login"]')) {
        authRequired = true;
        authReason = "Требуется авторизация на SuperJob";
      }
    }

    const selector = 'input:not([type="hidden"]), textarea, select, button, a[role="button"], [role="button"], a[data-qa*="response"], a[data-qa*="apply"], a[href*="response"], a[href*="apply"], a[href*="#apply"], a.btn, a[class*="apply"], a[class*="response"]';
    const allElements = Array.from(document.querySelectorAll(selector));

    // Also include any <a> elements whose visible text matches apply keywords
    document.querySelectorAll('a').forEach(aEl => {
      if (!allElements.includes(aEl) && isVisible(aEl)) {
        const txt = (aEl.innerText || '').trim().toLowerCase();
        if (/^(?:откликнуться|подать резюме|подать заявку|apply|apply now|quick apply)/.test(txt)) {
          allElements.push(aEl);
        }
      }
    });

    const elementsData = [];
    const errorsList = [];

    // Collect global validation errors on the page
    document.querySelectorAll('[role="alert"], .alert-danger, .form-error, [class*="form-error"]').forEach(errEl => {
      if (isVisible(errEl) && errEl.innerText.trim()) {
        errorsList.push(cleanText(errEl.innerText));
      }
    });

    for (const el of allElements) {
      if (!isVisible(el)) continue;

      const tag = el.tagName.toLowerCase();
      const type = (el.type || "").toLowerCase();
      const id = getOrAssignAgentId(el);
      const label = resolveElementLabel(el);
      const required = isElementRequired(el, label);
      const error = detectElementError(el);
      if (error) errorsList.push(error);

      const item = {
        element_id: id,
        tag: tag,
        type: type,
        label: label,
        required: required,
        validation_error: error
      };

      if (tag === "input") {
        if (type === "checkbox" || type === "radio") {
          item.checked = el.checked;
          item.value = el.value;
        } else if (type === "file") {
          item.accept = el.accept || "";
          item.files_count = el.files ? el.files.length : 0;
          item.attached_files = el.files ? Array.from(el.files).map(f => f.name) : [];
        } else {
          item.current_value = el.value || "";
          item.placeholder = el.placeholder || "";
        }
      } else if (tag === "textarea") {
        item.current_value = el.value || "";
        item.placeholder = el.placeholder || "";
      } else if (tag === "select") {
        item.options = Array.from(el.options).map(o => ({
          text: cleanText(o.text),
          value: o.value,
          selected: o.selected
        }));
        item.current_value = el.value || "";
        item.selected_text = el.selectedIndex >= 0 && el.options[el.selectedIndex] ? cleanText(el.options[el.selectedIndex].text) : "";
      } else if (tag === "button" || tag === "a" || el.getAttribute("role") === "button") {
        item.button_text = cleanText(el.innerText || el.value || el.getAttribute("title") || "");
        item.is_submit = type === "submit" || /submit|apply|send|отправить|подать|откликнуться|далее|continue|next/i.test(item.button_text);
      }

      elementsData.push(item);
    }

    const captcha = JH.detectCaptcha ? JH.detectCaptcha() : { detected: false };

    return {
      url: window.location.href,
      page_title: document.title,
      auth_required: authRequired,
      auth_reason: authReason,
      total_interactive_elements: elementsData.length,
      interactive_elements: elementsData,
      validation_errors: Array.from(new Set(errorsList)),
      has_captcha: captcha.detected,
      captcha_type: captcha.type || null
    };
  };

  /**
   * Retrieves live DOM element by assigned agent ID.
   */
  JH.getElementByAgentId = function(agentId) {
    if (elementMap.has(agentId)) {
      return elementMap.get(agentId);
    }
    const found = document.querySelector(`[data-jh-agent-id="${CSS.escape(agentId)}"]`);
    if (found) {
      elementMap.set(agentId, found);
      return found;
    }
    return null;
  };

})();
