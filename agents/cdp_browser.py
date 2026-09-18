import os
import sys
import time
import json
import base64
import tempfile
import urllib.request
import urllib.error
import subprocess
from typing import Dict, Any, List, Optional

try:
    from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page
except ImportError:
    sync_playwright = None
    Playwright = None
    Browser = None
    BrowserContext = None
    Page = None


CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"

# JavaScript payload for semantic inspection & assigning stable data-jh-agent-id
SEMANTIC_INSPECTION_JS = """() => {
    let elementIdCounter = 1;
    const elements = [];

    function cleanText(txt) {
        return (txt || '').replace(/[\\n\\r\\t]+/g, ' ').replace(/\\s{2,}/g, ' ').trim();
    }

    function resolveLabel(el) {
        // 1. aria-labelledby
        const labelledBy = el.getAttribute('aria-labelledby');
        if (labelledBy) {
            const l = document.getElementById(labelledBy);
            if (l && l.innerText.trim()) return cleanText(l.innerText);
        }
        // 2. aria-label
        const ariaLabel = el.getAttribute('aria-label');
        if (ariaLabel && ariaLabel.trim()) return cleanText(ariaLabel);

        // 3. label[for]
        if (el.id) {
            const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
            if (l && l.innerText.trim()) return cleanText(l.innerText);
        }
        // 4. parent label
        const parentLabel = el.closest('label');
        if (parentLabel && parentLabel.innerText.trim()) {
            const clone = parentLabel.cloneNode(true);
            clone.querySelectorAll('input, select, textarea, button').forEach(n => n.remove());
            const t = cleanText(clone.innerText);
            if (t) return t;
        }
        // 5. placeholder
        const placeholder = el.getAttribute('placeholder');
        if (placeholder && placeholder.trim()) return cleanText(placeholder);

        // 6. Closest container label
        const container = el.closest('.form-group, .form-field, .field, [class*="field"]');
        if (container) {
            const lbl = container.querySelector('label, .label, [class*="label"], strong, b');
            if (lbl && lbl !== el && lbl.innerText.trim()) return cleanText(lbl.innerText);
        }
        return el.name || el.id || '';
    }

    function isVisible(el) {
        if (!el) return false;
        if (el.offsetParent === null && el.style.position !== 'fixed') return false;
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    function isRequired(el, label) {
        if (el.hasAttribute('required') || el.getAttribute('aria-required') === 'true') return true;
        if (label && (label.includes('*') || label.includes('обязательно') || label.toLowerCase().includes('required'))) return true;
        const parent = el.parentElement;
        if (parent && parent.querySelector('.required, [class*="required"], .asterisk, [class*="star"]')) return true;
        return false;
    }

    // Auto-reveal cover letter textarea on HH.ru if present
    const hhLetterToggle = document.querySelector('[data-qa="vacancy-response-letter-toggle"], [data-qa="vacancy-response-popup-letter-toggle"]');
    if (hhLetterToggle && isVisible(hhLetterToggle)) {
        try { hhLetterToggle.click(); } catch (e) {}
    }

    const interactiveSelectors = 'input:not([type="hidden"]), textarea, select, button, a[role="button"], [role="button"]';
    const rawElements = Array.from(document.querySelectorAll(interactiveSelectors));

    for (const el of rawElements) {
        if (!isVisible(el) && el.type !== 'file') continue;

        let agentId = el.getAttribute('data-jh-agent-id');
        if (!agentId) {
            agentId = `elem_${elementIdCounter++}`;
            el.setAttribute('data-jh-agent-id', agentId);
        }

        const tag = el.tagName.toLowerCase();
        const type = (el.getAttribute('type') || (tag === 'textarea' ? 'textarea' : tag)).toLowerCase();
        const label = resolveLabel(el);
        const required = isRequired(el, label);
        const placeholder = el.getAttribute('placeholder') || '';
        const name = el.getAttribute('name') || '';

        let value = '';
        if (tag === 'input' || tag === 'textarea') {
            value = el.value || '';
        } else if (tag === 'select') {
            value = el.options[el.selectedIndex]?.text || el.value || '';
        } else {
            value = cleanText(el.innerText);
        }

        let options = [];
        if (tag === 'select') {
            options = Array.from(el.options).map(o => cleanText(o.text)).filter(Boolean);
        }

        elements.push({
            element_id: agentId,
            tag: tag,
            type: type,
            label: label,
            placeholder: placeholder,
            required: required,
            name: name,
            value: value,
            options: options.slice(0, 20)
        });
    }

    return {
        url: window.location.href,
        title: document.title,
        elements_count: elements.length,
        elements: elements
    };
}"""


class CDPBrowserDriver:
    """
    Direct Chrome DevTools Protocol (CDP) driver powered by Playwright.
    Controls the user's authentic desktop Chrome browser (with actual logins & cookies).
    Bypasses anti-bot barriers and supports native file uploads (PDF resumes).
    """
    _instance: Optional['CDPBrowserDriver'] = None

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._active_page: Optional[Page] = None

    @classmethod
    def get_instance(cls) -> 'CDPBrowserDriver':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_cdp_available(self) -> bool:
        """Checks if Chrome is listening on port 9222."""
        try:
            req = urllib.request.Request(f"{CDP_URL}/json/version", headers={"User-Agent": "JobHunter"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def launch_chrome_if_needed(self) -> bool:
        """Launches Chrome with --remote-debugging-port=9222 if not already running."""
        if self.is_cdp_available():
            return True

        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "launch_chrome.sh")
        if os.path.exists(script_path):
            try:
                subprocess.Popen(["/bin/bash", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for _ in range(15):
                    time.sleep(0.3)
                    if self.is_cdp_available():
                        return True
            except Exception as e:
                print(f"[CDP] Failed to run launch_chrome.sh: {e}")

        # Fallback to direct process launch on macOS
        chrome_mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if sys.platform == "darwin" and os.path.exists(chrome_mac):
            profile_dir = os.path.expanduser("~/.jobhunter-chrome")
            os.makedirs(profile_dir, exist_ok=True)
            try:
                subprocess.Popen([
                    chrome_mac,
                    f"--remote-debugging-port={CDP_PORT}",
                    f"--user-data-dir={profile_dir}",
                    "--no-first-run",
                    "--no-default-browser-check"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for _ in range(20):
                    time.sleep(0.3)
                    if self.is_cdp_available():
                        return True
            except Exception as e:
                print(f"[CDP] Failed to launch Google Chrome: {e}")

        return False

    def connect(self) -> bool:
        """Connects Playwright over CDP to the running Chrome instance."""
        if sync_playwright is None:
            raise RuntimeError("Playwright package is not installed in the environment.")

        if not self.is_cdp_available():
            launched = self.launch_chrome_if_needed()
            if not launched:
                return False

        try:
            if self._playwright is None:
                self._playwright = sync_playwright().start()

            if self._browser is None or not self._browser.is_connected():
                self._browser = self._playwright.chromium.connect_over_cdp(CDP_URL)
                contexts = self._browser.contexts
                self._context = contexts[0] if contexts else self._browser.new_context()

            return True
        except Exception as e:
            print(f"[CDP] Connection error: {e}")
            return False

    def get_active_page(self) -> Page:
        """Returns active or latest open page."""
        if not self.connect():
            raise RuntimeError("Could not connect to Chrome over CDP on port 9222.")

        pages = self._context.pages if self._context else []
        if pages:
            self._active_page = pages[-1]
        else:
            self._active_page = self._context.new_page()
        return self._active_page

    def open_page(self, url: str) -> Dict[str, Any]:
        """Navigates to the given URL in the user's Chrome."""
        page = self.get_active_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            return {
                "success": True,
                "url": page.url,
                "title": page.title()
            }
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    def inspect_page(self) -> Dict[str, Any]:
        """Inspects interactive form elements on active page."""
        page = self.get_active_page()
        try:
            res = page.evaluate(SEMANTIC_INSPECTION_JS)
            return {
                "success": True,
                "url": res.get("url"),
                "title": res.get("title"),
                "elements": res.get("elements", []),
                "elements_count": res.get("elements_count", 0)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fill_field(self, element_id: str, value: str, human_like: bool = True) -> Dict[str, Any]:
        """Fills an input or textarea element by data-jh-agent-id."""
        page = self.get_active_page()
        selector = f'[data-jh-agent-id="{element_id}"]'
        try:
            loc = page.locator(selector).first
            loc.wait_for(state="visible", timeout=8000)
            loc.click()
            loc.fill(value)
            return {"success": True, "element_id": element_id, "filled_value": value}
        except Exception as e:
            return {"success": False, "error": str(e), "element_id": element_id}

    def click_element(self, element_id: str) -> Dict[str, Any]:
        """Clicks an element by data-jh-agent-id."""
        page = self.get_active_page()
        selector = f'[data-jh-agent-id="{element_id}"]'
        try:
            loc = page.locator(selector).first
            loc.wait_for(state="visible", timeout=8000)
            loc.click()
            # Brief pause for DOM reactions
            page.wait_for_timeout(400)
            return {"success": True, "element_id": element_id}
        except Exception as e:
            return {"success": False, "error": str(e), "element_id": element_id}

    def select_option(self, element_id: str, option: str) -> Dict[str, Any]:
        """Selects option in select dropdown."""
        page = self.get_active_page()
        selector = f'[data-jh-agent-id="{element_id}"]'
        try:
            loc = page.locator(selector).first
            loc.select_option(label=option)
            return {"success": True, "element_id": element_id, "selected": option}
        except Exception as e:
            return {"success": False, "error": str(e), "element_id": element_id}

    def upload_file(self, element_id: str, file_path_or_base64: str, file_name: str = "resume.pdf") -> Dict[str, Any]:
        """
        Natively uploads a file into an input[type=file].
        Accepts either an absolute file path or base64 encoded file data.
        """
        page = self.get_active_page()
        selector = f'[data-jh-agent-id="{element_id}"]'
        temp_file_to_clean = None

        try:
            if os.path.exists(file_path_or_base64):
                target_path = file_path_or_base64
            else:
                # Decode base64 into a temporary file
                file_bytes = base64.b64decode(file_path_or_base64)
                suffix = os.path.splitext(file_name)[1] or ".pdf"
                temp_fd, target_path = tempfile.mkstemp(suffix=suffix, prefix="jh_resume_")
                with os.fdopen(temp_fd, "wb") as f:
                    f.write(file_bytes)
                temp_file_to_clean = target_path

            loc = page.locator(selector).first
            loc.set_input_files(target_path)
            return {
                "success": True,
                "element_id": element_id,
                "file_name": file_name,
                "file_path": target_path
            }
        except Exception as e:
            return {"success": False, "error": str(e), "element_id": element_id}
        finally:
            if temp_file_to_clean and os.path.exists(temp_file_to_clean):
                try:
                    os.remove(temp_file_to_clean)
                except Exception:
                    pass

    def take_screenshot(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Takes a screenshot of the active page."""
        page = self.get_active_page()
        try:
            if output_path:
                page.screenshot(path=output_path, full_page=False)
                return {"success": True, "path": output_path}
            else:
                screenshot_bytes = page.screenshot(full_page=False)
                b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                return {"success": True, "base64": b64}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close(self):
        """Disconnects from Chrome without closing user's browser."""
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
