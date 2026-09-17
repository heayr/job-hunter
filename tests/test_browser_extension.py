import unittest
import os
import json
import urllib.request
import urllib.error

class TestBrowserExtension(unittest.TestCase):
    def setUp(self):
        self.ext_dir = os.path.join(os.path.dirname(__file__), "..", "extension")
        self.manifest_path = os.path.join(self.ext_dir, "manifest.json")

    def test_manifest_file_exists_and_is_valid_json(self):
        self.assertTrue(os.path.exists(self.manifest_path), "manifest.json must exist")
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("manifest_version"), 3, "Must be Manifest V3")
        self.assertEqual(data.get("name"), "Job Hunter — AI Career Agent")
        self.assertIn("version", data)

    def test_manifest_permissions_and_components(self):
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        permissions = data.get("permissions", [])
        self.assertIn("activeTab", permissions)
        self.assertIn("storage", permissions)
        self.assertIn("scripting", permissions)

        # Action with popup
        action = data.get("action", {})
        self.assertEqual(action.get("default_popup"), "sidepanel.html")

        # Background service worker
        bg = data.get("background", {})
        self.assertEqual(bg.get("service_worker"), "background.js")
        bg_path = os.path.join(self.ext_dir, bg.get("service_worker"))
        self.assertTrue(os.path.exists(bg_path), "background.js file must exist")

        # Popup / side panel HTML
        sp_path = os.path.join(self.ext_dir, action.get("default_popup"))
        self.assertTrue(os.path.exists(sp_path), "sidepanel.html file must exist")

        # Content script
        cs = data.get("content_scripts", [])
        self.assertGreaterEqual(len(cs), 1)
        self.assertIn("content_script.js", cs[0].get("js", []))
        cs_path = os.path.join(self.ext_dir, "content_script.js")
        self.assertTrue(os.path.exists(cs_path), "content_script.js file must exist")

    def test_extension_icons_exist(self):
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        icons = data.get("icons", {})
        for size, rel_path in icons.items():
            full_path = os.path.join(self.ext_dir, rel_path)
            self.assertTrue(os.path.exists(full_path), f"Icon {size} ({rel_path}) must exist")
            self.assertGreater(os.path.getsize(full_path), 0, f"Icon {size} must not be empty")

    def test_sidepanel_html_and_js_contract(self):
        sp_html_path = os.path.join(self.ext_dir, "sidepanel.html")
        with open(sp_html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("sidepanel.js", html)
        self.assertIn("analyze-btn", html)
        self.assertIn("autofill-btn", html)
        self.assertIn("crm-status-badge", html)
        self.assertIn("dm-card", html)
        self.assertIn("cl-card", html)

        sp_js_path = os.path.join(self.ext_dir, "sidepanel.js")
        with open(sp_js_path, "r", encoding="utf-8") as f:
            js = f.read()

        self.assertIn("/api/status", js)
        self.assertIn("/api/vacancies/ai-parse", js)
        self.assertIn("/api/profiles", js)
        self.assertIn("AUTOFILL_PAGE", js)
        self.assertIn("EXTRACT_PAGE_DATA", js)

    def test_content_script_selectors_and_handlers(self):
        cs_path = os.path.join(self.ext_dir, "content_script.js")
        with open(cs_path, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("hh.ru", code)
        self.assertIn("linkedin.com", code)
        self.assertIn("greenhouse.io", code)
        self.assertIn("HTMLInputElement.prototype", code)
        self.assertIn("HTMLTextAreaElement.prototype", code)
        self.assertIn("EXTRACT_PAGE_DATA", code)
        self.assertIn("AUTOFILL_PAGE", code)

    def test_crm_cors_options_preflight(self):
        port_file = os.path.join(os.path.dirname(__file__), "..", ".current_port")
        port = 8115
        if os.path.exists(port_file):
            try:
                with open(port_file) as pf:
                    port = int(pf.read().strip())
            except Exception:
                pass
        url = f"http://127.0.0.1:{port}/api/vacancies/ai-parse"

        req = urllib.request.Request(url, method="OPTIONS")
        req.add_header("Origin", "chrome-extension://dummy-extension-id")
        req.add_header("Access-Control-Request-Method", "POST")
        req.add_header("Access-Control-Request-Headers", "Content-Type")

        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                headers = dict(resp.getheaders())
                self.assertEqual(headers.get("Access-Control-Allow-Origin"), "*")
                self.assertIn("POST", headers.get("Access-Control-Allow-Methods", ""))
        except urllib.error.URLError:
            self.skipTest("CRM server not reachable on test port")

    def test_platform_adapters_architecture(self):
        cs_path = os.path.join(self.ext_dir, "content_script.js")
        with open(cs_path, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("BasePlatformAdapter", code)
        self.assertIn("HeadHunterAdapter", code)
        self.assertIn("LinkedInAdapter", code)
        self.assertIn("ModernATSAdapter", code)
        self.assertIn("GenericWebAdapter", code)
        self.assertIn("vacancy-response-popup-form-letter-input", code)
        self.assertIn("how many years", code)
        self.assertIn("legally authorized", code)
        self.assertIn("sponsorship", code)
        self.assertIn("PLATFORM_ADAPTERS", code)
        self.assertIn("getActiveAdapter", code)

    def test_execution_modes_and_guardrails(self):
        sp_html_path = os.path.join(self.ext_dir, "sidepanel.html")
        with open(sp_html_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("mode-assist-btn", html)
        self.assertIn("mode-semiauto-btn", html)
        self.assertIn("mode-auto-btn", html)

        sp_js_path = os.path.join(self.ext_dir, "sidepanel.js")
        with open(sp_js_path, "r", encoding="utf-8") as f:
            js = f.read()
        self.assertIn('executionMode = "SEMI_AUTO"', js)
        self.assertIn('executionMode === "ASSIST"', js)
        self.assertIn("автоматическая вставка отключена", js)

if __name__ == "__main__":
    unittest.main()
