// ===================================================
// Job Hunter Chrome Extension — Platform Adapters Bridge
// ===================================================

/**
 * Base Platform Adapter Interface
 */
class BasePlatformAdapter {
  constructor(name) {
    this.name = name;
  }
  detect(url, document) {
    return false;
  }
  extractJob(url, document) {
    throw new Error("extractJob must be implemented");
  }
  async prepareForm(document) {
    return true;
  }
  async customFill(candidate, coverLetter, document, setVal, getCtx) {
    return { handled: false, filledCount: 0, fields: [] };
  }
}

/**
 * HeadHunter (HH.ru) Adapter
 */
class HeadHunterAdapter extends BasePlatformAdapter {
  constructor() {
    super("hh.ru");
  }

  detect(url) {
    return url.includes("hh.ru");
  }

  extractJob(url, doc) {
    const titleEl = doc.querySelector('[data-qa="vacancy-title"]') || doc.querySelector('h1');
    const compEl = doc.querySelector('[data-qa="vacancy-company-name"]') || doc.querySelector('.vacancy-company-name');
    const descEl = doc.querySelector('[data-qa="vacancy-description"]') || doc.querySelector('.g-user-content');
    const salaryEl = doc.querySelector('[data-qa="vacancy-salary"]') || doc.querySelector('.vacancy-salary-compensation-type');

    return {
      portal: "hh.ru",
      url,
      title: titleEl ? titleEl.innerText.trim() : doc.title.replace(/[\n\r]+/g, ' ').trim(),
      company: compEl ? compEl.innerText.trim() : "HH Employer",
      salary: salaryEl ? salaryEl.innerText.trim() : "",
      description: descEl ? descEl.innerText.trim() : (doc.body ? doc.body.innerText.slice(0, 4000) : "")
    };
  }

  async prepareForm(doc) {
    // 1. If response modal is not open, click the main response button if visible
    const mainApplyBtn = doc.querySelector('[data-qa="vacancy-response-link-top"],[data-qa="vacancy-response-link-bottom"]');
    if (mainApplyBtn && mainApplyBtn.offsetParent !== null && !doc.querySelector('textarea')) {
      mainApplyBtn.click();
      await new Promise(r => setTimeout(r, 600));
    }

    // 2. Open cover letter toggle in popup or on page
    const hhToggle = doc.querySelector('[data-qa="vacancy-response-letter-toggle"],[data-qa="vacancy-response-popup-letter-toggle"]');
    if (hhToggle && hhToggle.offsetParent !== null) {
      hhToggle.click();
      await new Promise(r => setTimeout(r, 400));
    }
    return true;
  }

  async customFill(candidate, coverLetter, doc, setVal, getCtx) {
    let filledCount = 0;
    const fields = [];

    // Target the specific HH.ru cover letter textarea
    const letterTa = doc.querySelector('[data-qa="vacancy-response-popup-form-letter-input"]') ||
                     doc.querySelector('textarea[name="message"]') ||
                     doc.querySelector('textarea');

    if (letterTa && coverLetter) {
      if (setVal(letterTa, coverLetter)) {
        filledCount++;
        fields.push("Сопроводительное (HH.ru)");
      }
    }

    return { handled: filledCount > 0, filledCount, fields };
  }
}

/**
 * LinkedIn Adapter (Jobs & Easy Apply)
 */
class LinkedInAdapter extends BasePlatformAdapter {
  constructor() {
    super("linkedin.com");
  }

  detect(url) {
    return url.includes("linkedin.com");
  }

  extractJob(url, doc) {
    const titleEl = doc.querySelector('.job-details-jobs-unified-top-card__job-title') ||
                    doc.querySelector('.jobs-unified-top-card__job-title') ||
                    doc.querySelector('h1');
    const compEl = doc.querySelector('.job-details-jobs-unified-top-card__company-name') ||
                   doc.querySelector('.jobs-unified-top-card__company-name');
    const descEl = doc.querySelector('#job-details') ||
                   doc.querySelector('.jobs-description__content') ||
                   doc.querySelector('.jobs-box__html-content');

    return {
      portal: "linkedin.com",
      url,
      title: titleEl ? titleEl.innerText.trim() : doc.title.trim(),
      company: compEl ? compEl.innerText.trim() : "LinkedIn Employer",
      description: descEl ? descEl.innerText.trim() : ""
    };
  }

  async prepareForm(doc) {
    // Look for Easy Apply button
    const easyApplyBtn = doc.querySelector('.jobs-apply-button--top-card button') ||
                         Array.from(doc.querySelectorAll('button')).find(b => /easy apply|откликнуться/i.test(b.innerText || ''));
    if (easyApplyBtn && easyApplyBtn.offsetParent !== null && !doc.querySelector('.jobs-easy-apply-modal')) {
      easyApplyBtn.click();
      await new Promise(r => setTimeout(r, 600));
    }
    return true;
  }

  async customFill(candidate, coverLetter, doc, setVal, getCtx) {
    let filledCount = 0;
    const fields = [];

    // Experience / Years numeric inputs
    const numInputs = Array.from(doc.querySelectorAll('input[type="number"], input[type="text"]'));
    for (const inp of numInputs) {
      const ctx = getCtx(inp);
      if (ctx.includes('how many years') || ctx.includes('years of experience') || ctx.includes('сколько лет')) {
        if (!inp.value || inp.value === '0') {
          if (setVal(inp, '5')) {
            filledCount++;
            fields.push("Опыт (5 лет)");
          }
        }
      }
    }

    // Yes/No Sponsorship radio questions
    const radios = Array.from(doc.querySelectorAll('input[type="radio"]'));
    for (const radio of radios) {
      const ctx = getCtx(radio);
      if (ctx.includes('legally authorized') || ctx.includes('authorized to work')) {
        if (ctx.includes('yes') || radio.value.toLowerCase() === 'yes') {
          radio.checked = true;
          radio.dispatchEvent(new Event('change', { bubbles: true }));
          filledCount++;
          fields.push("Work Authorization (Yes)");
        }
      }
      if (ctx.includes('sponsorship') || ctx.includes('require sponsorship')) {
        if (ctx.includes('no') || radio.value.toLowerCase() === 'no') {
          radio.checked = true;
          radio.dispatchEvent(new Event('change', { bubbles: true }));
          filledCount++;
          fields.push("Sponsorship (No)");
        }
      }
    }

    return { handled: false, filledCount, fields };
  }
}

/**
 * Greenhouse.io & Ashby & Lever & Workable ATS Adapter
 */
class ModernATSAdapter extends BasePlatformAdapter {
  constructor() {
    super("modern-ats");
  }

  detect(url) {
    return url.includes("greenhouse.io") ||
           url.includes("lever.co") ||
           url.includes("ashbyhq.com") ||
           url.includes("workable.com") ||
           url.includes("personio.");
  }

  extractJob(url, doc) {
    const titleEl = doc.querySelector('.app-title') ||
                    doc.querySelector('.posting-headline h2') ||
                    doc.querySelector('h1');
    const compEl = doc.querySelector('.company-name') ||
                   doc.querySelector('.posting-headline h4') ||
                   doc.querySelector('.org-name');
    const descEl = doc.querySelector('#content') ||
                   doc.querySelector('.section-wrapper') ||
                   doc.querySelector('.job-description') ||
                   doc.querySelector('article');

    return {
      portal: "ats",
      url,
      title: titleEl ? titleEl.innerText.trim() : doc.title.split(/[-|—]/)[0].trim(),
      company: compEl ? compEl.innerText.trim() : (new URL(url).hostname.split('.')[0]),
      description: descEl ? descEl.innerText.trim() : ""
    };
  }

  async prepareForm(doc) {
    // Scroll smoothly to application form if available
    const form = doc.querySelector('form#application_form, form.application-form, #application');
    if (form) {
      form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    return true;
  }

  async customFill(candidate, coverLetter, doc, setVal, getCtx) {
    let filledCount = 0;
    const fields = [];

    // Demographic / Legal dropdowns
    const selects = Array.from(doc.querySelectorAll('select'));
    for (const sel of selects) {
      const ctx = getCtx(sel);
      if (ctx.includes('authorized') || ctx.includes('work authorization')) {
        const opt = Array.from(sel.options).find(o => /yes|да/i.test(o.text));
        if (opt) {
          sel.value = opt.value;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          filledCount++;
          fields.push("Authorization: Yes");
        }
      } else if (ctx.includes('sponsorship')) {
        const opt = Array.from(sel.options).find(o => /no|нет/i.test(o.text));
        if (opt) {
          sel.value = opt.value;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          filledCount++;
          fields.push("Sponsorship: No");
        }
      }
    }

    return { handled: false, filledCount, fields };
  }
}

/**
 * Generic Fallback Adapter
 */
class GenericWebAdapter extends BasePlatformAdapter {
  constructor() {
    super("generic");
  }
  detect() { return true; }
  extractJob(url, doc) {
    const h1 = doc.querySelector('h1');
    const title = h1 ? h1.innerText.trim() : doc.title.split(/[-|—]/)[0].trim();
    const hostParts = window.location.hostname.replace(/^www\./, '').split('.');
    const company = hostParts[0].charAt(0).toUpperCase() + hostParts[0].slice(1);
    const mainEl = doc.querySelector('main') || doc.querySelector('article') || doc.querySelector('#main') || doc.body;
    const description = mainEl ? mainEl.innerText.slice(0, 4000).trim() : "";

    return { portal: "generic", url, title, company, description };
  }
}

// ─────────────────────────────────────────────
// Platform Registry
// ─────────────────────────────────────────────

const PLATFORM_ADAPTERS = [
  new HeadHunterAdapter(),
  new LinkedInAdapter(),
  new ModernATSAdapter(),
  new GenericWebAdapter()
];

function getActiveAdapter(url = window.location.href) {
  return PLATFORM_ADAPTERS.find(a => a.detect(url, document)) || PLATFORM_ADAPTERS[PLATFORM_ADAPTERS.length - 1];
}

/**
 * Extracts job posting text and metadata from the current webpage DOM.
 */
function extractJobPostingData() {
  const adapter = getActiveAdapter();
  const data = adapter.extractJob(window.location.href, document);
  data.adapter_name = adapter.name;
  data.extracted_at = new Date().toISOString();
  return data;
}

/**
 * Robust input/textarea setter that triggers framework change events
 */
function setFieldValue(el, val) {
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

  // Visual feedback
  el.style.transition = 'all 0.3s ease';
  el.style.borderColor = '#10b981';
  el.style.boxShadow = '0 0 0 2px rgba(16, 185, 129, 0.25)';
  return true;
}

/**
 * Returns contextual text around an input (labels, name, id, placeholder, aria-label)
 */
function getFieldContext(el) {
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
}

/**
 * Autofills job application forms on the active page
 */
async function autofillFormOnPage(candidateData, coverLetterText) {
  const adapter = getActiveAdapter();

  // 1. Let adapter expand toggles, modals or buttons
  await adapter.prepareForm(document);

  // 2. Run adapter-specific custom field fillers (numeric experience, sponsorship questions)
  const customRes = await adapter.customFill(candidateData, coverLetterText, document, setFieldValue, getFieldContext);

  const isRu = /[а-яёА-ЯЁ]/.test(document.title + ' ' + (document.body ? document.body.innerText.slice(0, 400) : '')) || (document.documentElement.lang || '').startsWith('ru');
  const c_fn = isRu ? (candidateData.fn_ru || candidateData.first_name || 'Егор') : (candidateData.fn_en || candidateData.first_name || 'Egor');
  const c_ln = isRu ? (candidateData.ln_ru || candidateData.last_name || 'Мышинский') : (candidateData.ln_en || candidateData.last_name || 'Myshinsky');
  const c_name = `${c_fn} ${c_ln}`;
  const c_loc = isRu ? (candidateData.loc_ru || 'Ереван, Армения / Удаленно') : (candidateData.loc_en || 'Yerevan, Armenia / Remote');

  const contacts = candidateData.contacts_structured || candidateData;
  const email = contacts.email || candidateData.email || 'egormyshinsky@gmail.com';
  const phone = contacts.phone || candidateData.phone || '+79998291788';
  const linkedin = contacts.linkedin || candidateData.linkedin || 'https://linkedin.com/in/potatochipasu';
  const github = contacts.github || candidateData.github || 'https://github.com/heayr';
  const portfolio = contacts.portfolio || candidateData.portfolio || 'https://nologs.website';
  const telegram = contacts.telegram || candidateData.telegram || '@PotatoChipasu';
  const tg_url = contacts.telegram_url || (telegram.startsWith('@') ? `https://t.me/${telegram.slice(1)}` : telegram);

  const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"]):not([type="file"]), textarea, [contenteditable="true"]'));
  let filledCount = customRes.filledCount || 0;
  const filledFields = [...(customRes.fields || [])];

  for (const el of inputs) {
    if (el.offsetParent === null && el.type !== 'text') continue;
    const ctx = getFieldContext(el);
    const pad = ' ' + ctx + ' ';
    const has = (...words) => words.some(w => pad.includes(' ' + w + ' '));
    const tag = el.tagName;
    const type = (el.type || '').toLowerCase();

    if (type === 'email' || has('email', 'e mail', 'mail', 'почта')) {
      if (setFieldValue(el, email)) { filledCount++; filledFields.push('Email'); }
    } else if (type === 'tel' || has('phone', 'mobile', 'cell', 'tel', 'телефон', 'тел')) {
      if (setFieldValue(el, phone)) { filledCount++; filledFields.push('Телефон'); }
    } else if (pad.includes('linkedin') || pad.includes('linked in')) {
      if (setFieldValue(el, linkedin)) { filledCount++; filledFields.push('LinkedIn'); }
    } else if (pad.includes('github') || pad.includes('git hub')) {
      if (setFieldValue(el, github)) { filledCount++; filledFields.push('GitHub'); }
    } else if (has('telegram', 'телеграм', 'tg')) {
      const tgVal = ctx.includes('url') || ctx.includes('link') ? tg_url : telegram;
      if (setFieldValue(el, tgVal)) { filledCount++; filledFields.push('Telegram'); }
    } else if (has('portfolio', 'website', 'web site', 'personal site', 'портфолио', 'веб сайт')) {
      if (setFieldValue(el, portfolio)) { filledCount++; filledFields.push('Портфолио'); }
    } else if (has('first name', 'firstname', 'имя', 'given name') || (pad.includes(' first ') && !pad.includes(' last '))) {
      if (setFieldValue(el, c_fn)) { filledCount++; filledFields.push('Имя'); }
    } else if (has('last name', 'lastname', 'фамилия', 'surname') || (pad.includes(' last ') && !pad.includes(' first '))) {
      if (setFieldValue(el, c_ln)) { filledCount++; filledFields.push('Фамилия'); }
    } else if (has('full name', 'your name', 'applicant name', 'фио') || (pad.includes(' name ') && !pad.includes(' first ') && !pad.includes(' last ') && !pad.includes(' company ') && !pad.includes(' file '))) {
      if (setFieldValue(el, c_name)) { filledCount++; filledFields.push('ФИО'); }
    } else if (has('city', 'город', 'location', 'residence', 'проживание') && !pad.includes('cover')) {
      if (setFieldValue(el, c_loc)) { filledCount++; filledFields.push('Локация'); }
    } else if (tag === 'TEXTAREA' || has('cover letter', 'сопроводительн', 'letter', 'message', 'comments', 'additional info', 'pitch', 'note')) {
      if (coverLetterText && setFieldValue(el, coverLetterText)) { filledCount++; filledFields.push('Сопроводительное'); }
    }
  }

  // Highlight file input (CV)
  const fileInp = document.querySelector('input[type="file"]');
  let fileNoticed = false;
  if (fileInp) {
    fileNoticed = true;
    const container = fileInp.closest('div') || fileInp;
    container.style.transition = 'all 0.4s ease';
    container.style.outline = '3px dashed #38bdf8';
    container.style.backgroundColor = 'rgba(56, 189, 248, 0.08)';
  }

  return {
    success: true,
    platform: adapter.name,
    filledCount,
    filledFields,
    fileNoticed
  };
}

// Listen for messages from Side Panel / Popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "EXTRACT_PAGE_DATA") {
    const data = extractJobPostingData();
    sendResponse(data);
  } else if (message.type === "AUTOFILL_PAGE") {
    autofillFormOnPage(message.candidateData, message.coverLetter)
      .then(res => sendResponse(res))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true; // Async response
  }
});
