// ===================================================
// Job Hunter Chrome Extension — Platform Adapters
// Extracted from content_script.js for modularity
// ===================================================

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
    const mainApplyBtn = doc.querySelector('[data-qa="vacancy-response-link-top"],[data-qa="vacancy-response-link-bottom"]');
    if (mainApplyBtn && mainApplyBtn.offsetParent !== null && !doc.querySelector('textarea')) {
      mainApplyBtn.click();
      await new Promise(r => setTimeout(r, 600));
    }

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
    const form = doc.querySelector('form#application_form, form.application-form, #application');
    if (form) {
      form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    return true;
  }

  async customFill(candidate, coverLetter, doc, setVal, getCtx) {
    let filledCount = 0;
    const fields = [];

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

// ── Platform Registry ─────────────────────────────

const PLATFORM_ADAPTERS = [
  new HeadHunterAdapter(),
  new LinkedInAdapter(),
  new ModernATSAdapter(),
  new GenericWebAdapter()
];

function getActiveAdapter(url = window.location.href) {
  return PLATFORM_ADAPTERS.find(a => a.detect(url, document)) || PLATFORM_ADAPTERS[PLATFORM_ADAPTERS.length - 1];
}

function extractJobPostingData() {
  const adapter = getActiveAdapter();
  const data = adapter.extractJob(window.location.href, document);
  data.adapter_name = adapter.name;
  data.extracted_at = new Date().toISOString();
  return data;
}

// Expose on JH namespace
JH.adapters = { getActiveAdapter, extractJobPostingData, PLATFORM_ADAPTERS };
