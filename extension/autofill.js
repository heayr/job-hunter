// ===================================================
// Job Hunter Chrome Extension — Autofill Engine
// UNCHANGED logic from original content_script.js
// Uses JH.core (setFieldValue, getFieldContext) and JH.adapters
// ===================================================

async function autofillFormOnPage(candidateData, coverLetterText) {
  const adapter = JH.adapters.getActiveAdapter();

  // 1. Let adapter expand toggles, modals or buttons
  await adapter.prepareForm(document);

  // 2. Run adapter-specific custom field fillers
  const customRes = await adapter.customFill(candidateData, coverLetterText, document, JH.setFieldValue, JH.getFieldContext);

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
    const ctx = JH.getFieldContext(el);
    const pad = ' ' + ctx + ' ';
    const has = (...words) => words.some(w => pad.includes(' ' + w + ' '));
    const tag = el.tagName;
    const type = (el.type || '').toLowerCase();

    if (type === 'email' || has('email', 'e mail', 'mail', 'почта')) {
      if (JH.setFieldValue(el, email)) { filledCount++; filledFields.push('Email'); }
    } else if (type === 'tel' || has('phone', 'mobile', 'cell', 'tel', 'телефон', 'тел')) {
      if (JH.setFieldValue(el, phone)) { filledCount++; filledFields.push('Телефон'); }
    } else if (pad.includes('linkedin') || pad.includes('linked in')) {
      if (JH.setFieldValue(el, linkedin)) { filledCount++; filledFields.push('LinkedIn'); }
    } else if (pad.includes('github') || pad.includes('git hub')) {
      if (JH.setFieldValue(el, github)) { filledCount++; filledFields.push('GitHub'); }
    } else if (has('telegram', 'телеграм', 'tg')) {
      const tgVal = ctx.includes('url') || ctx.includes('link') ? tg_url : telegram;
      if (JH.setFieldValue(el, tgVal)) { filledCount++; filledFields.push('Telegram'); }
    } else if (has('portfolio', 'website', 'web site', 'personal site', 'портфолио', 'веб сайт')) {
      if (JH.setFieldValue(el, portfolio)) { filledCount++; filledFields.push('Портфолио'); }
    } else if (has('first name', 'firstname', 'имя', 'given name') || (pad.includes(' first ') && !pad.includes(' last '))) {
      if (JH.setFieldValue(el, c_fn)) { filledCount++; filledFields.push('Имя'); }
    } else if (has('last name', 'lastname', 'фамилия', 'surname') || (pad.includes(' last ') && !pad.includes(' first '))) {
      if (JH.setFieldValue(el, c_ln)) { filledCount++; filledFields.push('Фамилия'); }
    } else if (has('full name', 'your name', 'applicant name', 'фио') || (pad.includes(' name ') && !pad.includes(' first ') && !pad.includes(' last ') && !pad.includes(' company ') && !pad.includes(' file '))) {
      if (JH.setFieldValue(el, c_name)) { filledCount++; filledFields.push('ФИО'); }
    } else if (has('city', 'город', 'location', 'residence', 'проживание') && !pad.includes('cover')) {
      if (JH.setFieldValue(el, c_loc)) { filledCount++; filledFields.push('Локация'); }
    } else if (tag === 'TEXTAREA' || has('cover letter', 'сопроводительн', 'letter', 'message', 'comments', 'additional info', 'pitch', 'note')) {
      if (coverLetterText && JH.setFieldValue(el, coverLetterText)) { filledCount++; filledFields.push('Сопроводительное'); }
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

// Expose globally for backward compatibility
window.autofillFormOnPage = autofillFormOnPage;
