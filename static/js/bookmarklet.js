// ==========================================
// Job Hunter CRM — Auto-Apply Bookmarklet
// ==========================================

function copyBookmarkletCode() {
    const input = document.getElementById('bookmarklet-code-input');
    if (input) {
        input.select();
        navigator.clipboard.writeText(input.value);
        showToast('📋 Код букмарклета скопирован в буфер обмена!');
    }
}

function initBookmarklet() {
    const p = (profiles && profiles.find(pr => pr.id === activeProfileId)) || (profiles && profiles[0]) || {};
    const contacts = p.contacts_structured || {};

    const rawName = p.name || 'Егор Мышинский';
    const nameParts = rawName.split(/\s+/);
    const fn_ru = p.first_name || nameParts[0] || 'Егор';
    const ln_ru = p.last_name || (nameParts.length > 1 ? nameParts.slice(1).join(' ') : 'Мышинский');

    const fn_en = fn_ru.toLowerCase().includes('егор') ? 'Egor' : fn_ru;
    const ln_en = ln_ru.toLowerCase().includes('мышин') ? 'Myshinsky' : ln_ru;
    const name_en = `${fn_en} ${ln_en}`;
    const name_ru = `${fn_ru} ${ln_ru}`;

    const email = contacts.email || 'egormyshinsky@gmail.com';
    const phone = contacts.phone || '+79998291788';
    const linkedin = contacts.linkedin || 'https://linkedin.com/in/potatochipasu';
    const github = contacts.github || 'https://github.com/heayr';
    const portfolio = contacts.portfolio || 'https://nologs.website';
    const telegram = contacts.telegram || '@PotatoChipasu';
    const telegram_url = contacts.telegram_url || (telegram.startsWith('@') ? `https://t.me/${telegram.slice(1)}` : telegram);
    const loc_en = p.location || 'Yerevan, Armenia / Remote';
    const loc_ru = 'Ереван, Армения / Удаленно';

    const cand = {
        fn_en, ln_en, name_en,
        fn_ru, ln_ru, name_ru,
        email, phone, linkedin, github, portfolio,
        telegram, telegram_url,
        loc_en, loc_ru
    };

    const candJson = JSON.stringify(cand);

    const code = `javascript:(async function(){try{const C=${candJson};const isRu=/[а-яёА-ЯЁ]/.test(document.title+' '+(document.body?document.body.innerText.slice(0,400):''))||(document.documentElement.lang||'').startsWith('ru');const c_fn=isRu?C.fn_ru:C.fn_en;const c_ln=isRu?C.ln_ru:C.ln_en;const c_name=isRu?C.name_ru:C.name_en;const c_loc=isRu?C.loc_ru:C.loc_en;let coverText='';if(window.location.hash&&window.location.hash.includes('jh_cover=')){try{coverText=decodeURIComponent(window.location.hash.split('jh_cover=')[1]);}catch(e){}}if(!coverText&&navigator.clipboard&&navigator.clipboard.readText){try{const clip=await navigator.clipboard.readText();if(clip&&clip.length>40&&!clip.startsWith('http'))coverText=clip;}catch(e){}}const hhToggle=document.querySelector('[data-qa="vacancy-response-letter-toggle"],[data-qa="vacancy-response-popup-letter-toggle"]');if(hhToggle&&hhToggle.offsetParent!==null){hhToggle.click();await new Promise(r=>setTimeout(r,300));}const genToggles=Array.from(document.querySelectorAll('button, a, span[role="button"]'));const fToggle=genToggles.find(el=>el.offsetParent!==null&&/сопроводительн|cover/i.test(el.innerText||''));if(fToggle&&!document.querySelector('textarea')){fToggle.click();await new Promise(r=>setTimeout(r,300));}function setVal(el,val){if(!el||val===undefined||val===null||val==='')return false;el.focus();const isTa=el.tagName==='TEXTAREA';const proto=isTa?window.HTMLTextAreaElement.prototype:window.HTMLInputElement.prototype;const setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;if(setter){setter.call(el,val);}else{el.value=val;}el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));el.dispatchEvent(new Event('blur',{bubbles:true}));el.style.transition='all 0.3s ease';el.style.borderColor='#10b981';el.style.boxShadow='0 0 0 2px rgba(16, 185, 129, 0.25)';return true;}function getCtx(el){let t=[el.name,el.id,el.placeholder,el.getAttribute('aria-label'),el.autocomplete].filter(Boolean).join(' ');if(el.id){const lbl=document.querySelector(\`label[for="\${el.id}"]\`);if(lbl)t+=' '+lbl.innerText;}const pLbl=el.closest('label');if(pLbl)t+=' '+pLbl.innerText;const prev=el.previousElementSibling;if(prev&&(prev.tagName==='LABEL'||(prev.className&&typeof prev.className==='string'&&prev.className.includes('label'))))t+=' '+prev.innerText;const parent=el.parentElement;if(parent&&parent.previousElementSibling&&parent.previousElementSibling.tagName==='LABEL')t+=' '+parent.previousElementSibling.innerText;return t.toLowerCase().replace(/[^a-z0-9а-яё]/gi,' ');}const inputs=Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"]):not([type="file"]), textarea, [contenteditable="true"]'));let filledCount=0;const filledFields=[];for(const el of inputs){if(el.offsetParent===null&&el.type!=='text')continue;const ctx=getCtx(el);const pad=' '+ctx+' ';const has=(...words)=>words.some(w=>pad.includes(' '+w+' '));const tag=el.tagName;const type=(el.type||'').toLowerCase();if(type==='email'||has('email','e mail','mail','почта')){if(setVal(el,C.email)){filledCount++;filledFields.push('Email');}}else if(type==='tel'||has('phone','mobile','cell','tel','телефон','тел')){if(setVal(el,C.phone)){filledCount++;filledFields.push('Телефон');}}else if(pad.includes('linkedin')||pad.includes('linked in')){if(setVal(el,C.linkedin)){filledCount++;filledFields.push('LinkedIn');}}else if(pad.includes('github')||pad.includes('git hub')){if(setVal(el,C.github)){filledCount++;filledFields.push('GitHub');}}else if(has('telegram','телеграм','tg')){const tgVal=ctx.includes('url')||ctx.includes('link')?C.telegram_url:C.telegram;if(setVal(el,tgVal)){filledCount++;filledFields.push('Telegram');}}else if(has('portfolio','website','web site','personal site','портфолио','веб сайт')){if(setVal(el,C.portfolio)){filledCount++;filledFields.push('Портфолио');}}else if(has('first name','firstname','имя','given name')||(pad.includes(' first ')&&!pad.includes(' last '))){if(setVal(el,c_fn)){filledCount++;filledFields.push('Имя');}}else if(has('last name','lastname','фамилия','surname')||(pad.includes(' last ')&&!pad.includes(' first '))){if(setVal(el,c_ln)){filledCount++;filledFields.push('Фамилия');}}else if(has('full name','your name','applicant name','фио')||(pad.includes(' name ')&&!pad.includes(' first ')&&!pad.includes(' last ')&&!pad.includes(' company ')&&!pad.includes(' file '))){if(setVal(el,c_name)){filledCount++;filledFields.push('ФИО');}}else if(has('city','город','location','residence','проживание')&&!pad.includes('cover')){if(setVal(el,c_loc)){filledCount++;filledFields.push('Локация');}}else if(tag==='TEXTAREA'||has('cover letter','сопроводительн','letter','message','comments','additional info','pitch','note')){if(coverText&&setVal(el,coverText)){filledCount++;filledFields.push('Сопроводительное');}}}const fileInp=document.querySelector('input[type="file"]');let fileNoticed=false;if(fileInp){fileNoticed=true;const container=fileInp.closest('div')||fileInp;container.style.transition='all 0.4s ease';container.style.outline='3px dashed #38bdf8';container.style.backgroundColor='rgba(56, 189, 248, 0.08)';}const toast=document.createElement('div');toast.style.cssText='position:fixed;bottom:24px;right:24px;background:#0f172a;color:#fff;padding:16px 22px;border-radius:14px;z-index:99999999;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;font-size:13px;line-height:1.5;box-shadow:0 20px 40px rgba(0,0,0,0.5);border:1px solid #10b981;max-width:380px;';if(filledCount>0){toast.innerHTML=\`<div style="display:flex;align-items:flex-start;gap:10px;"><span style="font-size:20px;">⚡️</span><div><div style="font-weight:700;color:#34d399;margin-bottom:2px;">Job Hunter: Успешно заполнено!</div><div style="color:#cbd5e1;font-size:12px;">Полей: <b>\${filledCount}</b> (\${filledFields.slice(0, 5).join(', ')}\${filledFields.length > 5 ? '...' : ''})</div>\${fileNoticed ? '<div style="color:#38bdf8;font-size:11px;margin-top:4px;font-weight:600;">📎 Выделено поле прикрепления резюме (CV)</div>' : ''}</div></div>\`;}else{toast.style.borderColor='#f59e0b';toast.innerHTML='<div style="display:flex;align-items:flex-start;gap:10px;"><span style="font-size:20px;">⚠️</span><div><div style="font-weight:700;color:#fbbf24;">Job Hunter: Форма не найдена</div><div style="color:#cbd5e1;font-size:12px;">Если форма внутри всплывающего окна, сначала нажмите «Откликнуться» / «Apply», а затем повторно нажмите закладку.</div></div></div>';}document.body.appendChild(toast);setTimeout(()=>toast.remove(),5500);}catch(err){alert('❌ Job Hunter Error: '+err.message);}})();`;

    const btn = document.getElementById('bookmarklet-btn');
    if (btn) btn.href = code;
    const modalBtn = document.getElementById('bookmarklet-modal-btn');
    if (modalBtn) modalBtn.href = code;
    const codeArea = document.getElementById('bookmarklet-code-input');
    if (codeArea) codeArea.value = code;
}
