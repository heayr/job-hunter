// ===================================================
// Job Hunter Chrome Extension — Core Utilities
// Shared by autofill.js, automation.js, and platform adapters
// ===================================================

const JH = window.JH || {};
window.JH = JH;

// ── Randomized Delays ─────────────────────────────

JH.randomDelay = function(minMs, maxMs) {
  const delay = Math.floor(Math.random() * (maxMs - minMs) + minMs);
  return new Promise(r => setTimeout(r, delay));
};

// ── Field Value Setter (React/Vue compatible) ─────

JH.setFieldValue = function(el, val) {
  if (!el || val === undefined || val === null || val === '') return false;
  el.focus();
  const isTa = el.tagName === 'TEXTAREA';
  const proto = isTa ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
  if (setter) {
    setter.call(el, val);
  } else {
    el.value = val;
  }
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.dispatchEvent(new Event('blur', { bubbles: true }));

  el.style.transition = 'all 0.3s ease';
  el.style.borderColor = '#10b981';
  el.style.boxShadow = '0 0 0 2px rgba(16, 185, 129, 0.25)';
  return true;
};

// ── Human-like Typing ─────────────────────────────

JH.humanType = async function(el, text, opts = {}) {
  const { minDelay = 25, maxDelay = 90 } = opts;
  if (!el || !text) return false;
  el.focus();
  el.dispatchEvent(new Event('focus', { bubbles: true }));

  const isTa = el.tagName === 'TEXTAREA';
  const proto = isTa ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;

  for (const char of text) {
    const current = el.value || '';
    if (setter) {
      setter.call(el, current + char);
    } else {
      el.value = current + char;
    }
    el.dispatchEvent(new KeyboardEvent('keydown', { key: char, code: 'Key' + char.toUpperCase(), bubbles: true }));
    el.dispatchEvent(new KeyboardEvent('keypress', { key: char, code: 'Key' + char.toUpperCase(), bubbles: true }));
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new KeyboardEvent('keyup', { key: char, code: 'Key' + char.toUpperCase(), bubbles: true }));
    await JH.randomDelay(minDelay, maxDelay);
  }

  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.dispatchEvent(new Event('blur', { bubbles: true }));

  el.style.transition = 'all 0.3s ease';
  el.style.borderColor = '#10b981';
  el.style.boxShadow = '0 0 0 2px rgba(16, 185, 129, 0.25)';
  return true;
};

// ── Simulate Click with trajectory ────────────────

JH.simulateClick = async function(el) {
  if (!el) return false;

  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  await JH.randomDelay(150, 400);

  const rect = el.getBoundingClientRect();
  const x = rect.left + rect.width * (0.3 + Math.random() * 0.4);
  const y = rect.top + rect.height * (0.3 + Math.random() * 0.4);

  el.dispatchEvent(new MouseEvent('mouseover', { clientX: x, clientY: y, bubbles: true }));
  await JH.randomDelay(50, 150);
  el.dispatchEvent(new MouseEvent('mousedown', { clientX: x, clientY: y, bubbles: true }));
  await JH.randomDelay(30, 100);
  el.dispatchEvent(new MouseEvent('mouseup', { clientX: x, clientY: y, bubbles: true }));
  el.dispatchEvent(new MouseEvent('click', { clientX: x, clientY: y, bubbles: true }));
  return true;
};

// ── Field Context Detection ───────────────────────

JH.getFieldContext = function(el) {
  let t = [el.name, el.id, el.placeholder, el.getAttribute('aria-label'), el.autocomplete].filter(Boolean).join(' ');
  if (el.id) {
    const lbl = document.querySelector(`label[for="${el.id}"]`);
    if (lbl) t += ' ' + lbl.innerText;
  }
  const pLbl = el.closest('label');
  if (pLbl) t += ' ' + pLbl.innerText;

  const prev = el.previousElementSibling;
  if (prev && (prev.tagName === 'LABEL' || (prev.className && typeof prev.className === 'string' && prev.className.includes('label')))) {
    t += ' ' + prev.innerText;
  }
  const parent = el.parentElement;
  if (parent && parent.previousElementSibling && parent.previousElementSibling.tagName === 'LABEL') {
    t += ' ' + parent.previousElementSibling.innerText;
  }
  return t.toLowerCase().replace(/[^a-z0-9а-яё]/gi, ' ');
};

// ── CAPTCHA Detection ─────────────────────────────

JH.detectCaptcha = function() {
  const turnstile = document.querySelector('iframe[src*="challenges.cloudflare.com"]') ||
                    document.querySelector('[data-sitekey]');
  const recaptcha = document.querySelector('iframe[src*="google.com/recaptcha"]') ||
                    document.querySelector('.g-recaptcha') ||
                    document.querySelector('#recaptcha');
  const hcaptcha = document.querySelector('iframe[src*="hcaptcha.com"]') ||
                   document.querySelector('.h-captcha');
  const datadome = document.querySelector('iframe[src*="datadome"]') ||
                   document.querySelector('[data-dd-captcha]');
  const challengeText = /verify you are human|prove you are not a robot|captcha|подтвердите/i
    .test(document.body ? document.body.innerText : '');

  return {
    detected: !!(turnstile || recaptcha || hcaptcha || datadome || challengeText),
    type: turnstile ? 'turnstile' : recaptcha ? 'recaptcha' : hcaptcha ? 'hcaptcha' :
          datadome ? 'datadome' : challengeText ? 'text_challenge' : null,
    element: turnstile || recaptcha || hcaptcha || datadome || null
  };
};

// ── Submit Button Detection ───────────────────────

JH.findSubmitButton = function() {
  const SUBMIT_TEXT = /^(?:submit|apply|send|отправить|подать|откликнуться|откликнуть|применить|далее|continue|next|save|сохранить)/i;

  const byType = Array.from(document.querySelectorAll(
    'button[type="submit"], input[type="submit"]'
  ));

  const byText = Array.from(document.querySelectorAll(
    'button, a[role="button"], [role="button"], input[type="button"]'
  )).filter(el => {
    const text = (el.innerText || el.value || '').trim();
    return SUBMIT_TEXT.test(text) && el.offsetParent !== null;
  });

  const form = document.querySelector('form');

  return {
    submitByType: byType,
    submitByText: byText,
    form,
    best: byType[0] || byText[0] || null
  };
};

// ── Multi-Step Detection ──────────────────────────

JH.detectStepProgress = function() {
  const text = (document.body ? document.body.innerText : '').slice(0, 3000);

  const stepMatch = text.match(/step\s+(\d+)\s+(?:of|из)\s+(\d+)/i) ||
                    text.match(/шаг\s+(\d+)\s+(?:из|of)\s+(\d+)/i);
  if (stepMatch) {
    return { current: parseInt(stepMatch[1]), total: parseInt(stepMatch[2]) };
  }

  const progressBar = document.querySelector('[role="progressbar"]');
  if (progressBar) {
    const val = parseInt(progressBar.getAttribute('aria-valuenow') || '0');
    const max = parseInt(progressBar.getAttribute('aria-valuemax') || '100');
    return { current: val, total: max, isPercent: true };
  }

  const dots = document.querySelectorAll('.step-indicator .active, .step.active, [data-step].active');
  if (dots.length > 0) {
    return { current: dots.length, total: document.querySelectorAll('.step-indicator .step, .step, [data-step]').length || dots.length + 2 };
  }

  return null;
};

JH.findNextButton = function() {
  const NEXT_TEXT = /^(?:next|далее|continue|продолжить|proceed|save & continue|далее\s*→)/i;
  return Array.from(document.querySelectorAll('button, a[role="button"], [role="button"], input[type="button"]'))
    .find(el => NEXT_TEXT.test((el.innerText || el.value || '').trim()));
};

// ── Domain Rate Tracking ──────────────────────────

JH._domainCounts = {};

JH.checkDomainRate = function(hostname, maxPerHour = 3) {
  const now = Date.now();
  const key = hostname;
  if (!JH._domainCounts[key]) {
    JH._domainCounts[key] = [];
  }
  JH._domainCounts[key] = JH._domainCounts[key].filter(t => now - t < 3600000);
  if (JH._domainCounts[key].length >= maxPerHour) {
    return false;
  }
  JH._domainCounts[key].push(now);
  return true;
};

// ── Overlay Display ───────────────────────────────

JH.showResultOverlay = function(result) {
  const existing = document.getElementById("jh-result-overlay");
  if (existing) existing.remove();

  const isOk = result.success;
  const fieldList = (result.filledFields || []).map(f => `<li>${f}</li>`).join("");

  const overlay = document.createElement("div");
  overlay.id = "jh-result-overlay";
  overlay.innerHTML = `
    <div style="
      position: fixed; top: 20px; right: 20px; z-index: 2147483647;
      background: ${isOk ? 'linear-gradient(135deg, #064e3b, #022c22)' : 'linear-gradient(135deg, #7f1d1d, #450a0a)'};
      color: #f0fdf4; border-radius: 16px; padding: 20px 24px;
      box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5), 0 0 0 1px ${isOk ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'};
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px; line-height: 1.5; max-width: 420px; min-width: 320px;
      animation: jhSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      backdrop-filter: blur(20px);
    ">
      <style>
        @keyframes jhSlideIn { from { opacity:0; transform: translateY(-20px) scale(0.95); } to { opacity:1; transform: translateY(0) scale(1); } }
        .jh-close { position:absolute; top:8px; right:12px; cursor:pointer; color:#94a3b8; font-size:18px; line-height:1; }
        .jh-close:hover { color:#fff; }
        .jh-fields { margin:8px 0 0; padding-left:18px; font-size:12px; color:#a7f3d0; }
        .jh-fields li { margin: 2px 0; }
        .jh-badge { display:inline-flex; align-items:center; gap:4px; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:600; }
      </style>
      <span class="jh-close" onclick="document.getElementById('jh-result-overlay').remove()">&times;</span>
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
        <span style="font-size:24px;">${isOk ? '✅' : '⚠️'}</span>
        <div>
          <div style="font-weight:700; font-size:15px;">${isOk ? 'Отклик заполнен!' : 'Форма не найдена'}</div>
          <div style="font-size:12px; color:#86efac; opacity:0.8;">${result.company || ''} — ${result.role || ''}</div>
        </div>
      </div>
      ${isOk ? `
        <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:4px;">
          <span class="jh-badge" style="background:rgba(16,185,129,0.2); color:#6ee7b7; border:1px solid rgba(16,185,129,0.3);">🎯 ${result.platform || 'web'}</span>
          <span class="jh-badge" style="background:rgba(56,189,248,0.2); color:#7dd3fc; border:1px solid rgba(56,189,248,0.3);">📝 ${result.filledCount} полей</span>
        </div>
        <ul class="jh-fields">${fieldList}</ul>
        <div style="margin-top:10px; font-size:11px; color:#86efac; opacity:0.7;">
          ⏳ Проверьте поля и нажмите "Submit" когда будете готовы
        </div>
      ` : `
        <div style="font-size:12px; color:#fca5a5; margin-top:4px;">
          Откройте форму отклика вручную, затем нажмите <b>"Заполнить"</b> в Side Panel расширения.
        </div>
      `}
    </div>
  `;

  document.body.appendChild(overlay);

  setTimeout(() => {
    if (overlay.parentNode) {
      overlay.style.transition = "opacity 0.5s";
      overlay.style.opacity = "0";
      setTimeout(() => overlay.remove(), 500);
    }
  }, 12000);
};
