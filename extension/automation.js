// ===================================================
// Job Hunter Chrome Extension — Automation Engine
// CAPTCHA detection, auto-submit, multi-step, anti-detection
// ===================================================

const JH_automation = {

  // ── Full Auto-Submit Pipeline ─────────────────────
  async autoSubmitWithDetection(candidateData, coverLetterText) {
    const result = { success: false, action: 'none', captcha: null, filledCount: 0, filledFields: [], platform: '', error: null };

    // 1. CAPTCHA check BEFORE filling
    const captchaPre = JH.detectCaptcha();
    if (captchaPre.detected) {
      result.captcha = captchaPre;
      result.error = `CAPTCHA detected on page load: ${captchaPre.type}`;
      result.action = 'captcha_blocked';
      return result;
    }

    // 2. Domain rate limit check
    const hostname = window.location.hostname;
    if (!JH.checkDomainRate(hostname, 3)) {
      result.error = `Rate limit exceeded for ${hostname} (max 3/hour)`;
      result.action = 'rate_limited';
      return result;
    }

    // 3. Fill the form (reuse existing autofill)
    const fillResult = await autofillFormOnPage(candidateData, coverLetterText);
    result.filledCount = fillResult.filledCount;
    result.filledFields = fillResult.filledFields;
    result.platform = fillResult.platform;

    if (!fillResult.success || fillResult.filledCount === 0) {
      result.success = false;
      result.error = 'No fields found or filled on this page';
      result.action = 'form_not_found';
      return result;
    }

    // 4. Anti-detection delay after fill
    await JH.randomDelay(800, 2000);

    // 5. CAPTCHA check BEFORE submit
    const captchaPost = JH.detectCaptcha();
    if (captchaPost.detected) {
      result.captcha = captchaPost;
      result.error = `CAPTCHA appeared after fill: ${captchaPost.type}`;
      result.action = 'captcha_blocked';
      result.success = true; // Form was filled, just can't submit
      return result;
    }

    // 6. Multi-step check — if there's a "Next" button, click it instead of submit
    const nextBtn = JH.findNextButton();
    if (nextBtn) {
      const stepInfo = JH.detectStepProgress();
      await JH.simulateClick(nextBtn);
      result.action = 'step_advanced';
      result.stepProgress = stepInfo;
      result.success = true;

      // Wait for next step to render
      await JH.randomDelay(1500, 3000);

      // Check if form is still there (more steps)
      const nextNext = JH.findNextButton();
      const submit = JH.findSubmitButton();
      if (nextNext) {
        result.action = 'multi_step_pending';
        result.message = `Step ${(stepInfo?.current || 1) + 1} of ${stepInfo?.total || '?'} — more steps remaining`;
      } else if (submit.best) {
        result.action = 'ready_to_submit';
        result.message = 'Last step reached — submit button available';
      }
      return result;
    }

    // 7. Find and click submit
    const submitInfo = JH.findSubmitButton();
    if (!submitInfo.best) {
      result.error = 'Submit button not found on page';
      result.action = 'submit_not_found';
      result.success = true; // Form was filled, just can't find submit
      return result;
    }

    // 8. Human-like delay before submit
    await JH.randomDelay(500, 1500);

    // 9. Click submit with simulated mouse
    await JH.simulateClick(submitInfo.best);
    result.action = 'submitted';
    result.success = true;

    // 10. Wait for page response (navigation or AJAX)
    await JH.randomDelay(2000, 4000);

    return result;
  },

  // ── Multi-Step Traversal ─────────────────────────
  async traverseMultiStep(candidateData, coverLetterText, maxSteps = 7) {
    const stepsCompleted = [];

    for (let step = 0; step < maxSteps; step++) {
      // Fill current step
      const fillResult = await autofillFormOnPage(candidateData, coverLetterText);
      stepsCompleted.push({ step: step + 1, filled: fillResult.filledCount });

      await JH.randomDelay(500, 1200);

      // CAPTCHA check
      const captcha = JH.detectCaptcha();
      if (captcha.detected) {
        return { success: false, stepsCompleted, error: `CAPTCHA at step ${step + 1}: ${captcha.type}`, captcha };
      }

      // Look for Next button
      const nextBtn = JH.findNextButton();
      if (nextBtn) {
        await JH.simulateClick(nextBtn);
        await JH.randomDelay(1500, 3000);
        continue;
      }

      // Look for Submit button
      const submitInfo = JH.findSubmitButton();
      if (submitInfo.best) {
        await JH.randomDelay(500, 1500);
        await JH.simulateClick(submitInfo.best);
        await JH.randomDelay(2000, 4000);
        return { success: true, stepsCompleted, action: 'submitted' };
      }

      // No Next or Submit — maybe form is complete or stuck
      break;
    }

    return { success: false, stepsCompleted, error: 'Could not find Next or Submit after traversal' };
  }
};

// Expose globally
JH.automation = JH_automation;
