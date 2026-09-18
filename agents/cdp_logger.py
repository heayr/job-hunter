import os
import time
import json
import logging
from typing import List, Dict, Any, Optional

try:
    from playwright.sync_api import Page, ConsoleMessage, Request
except ImportError:
    Page = None
    ConsoleMessage = None
    Request = None


class CDPLogger:
    """
    Real-time browser activity, console, network, and agent action logger.
    Captures live events from Playwright pages and agent actions.
    Persists logs to disk and maintains an in-memory buffer for UI display.
    """
    _instance: Optional['CDPLogger'] = None

    def __init__(self, log_dir: Optional[str] = None):
        if log_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_dir = os.path.join(base_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "agent_cdp.log")
        self._buffer: List[Dict[str, Any]] = []
        self._max_buffer = 500
        self._attached_pages = set()

        # Setup standard python file logger
        self.logger = logging.getLogger("CDPAgent")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file, encoding="utf-8")
            formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    @classmethod
    def get_instance(cls) -> 'CDPLogger':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def log(self, level: str, source: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Records a structured log entry."""
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "level": level.upper(),
            "source": source,
            "message": message,
            "data": data or {}
        }
        self._buffer.append(entry)
        if len(self._buffer) > self._max_buffer:
            self._buffer.pop(0)

        # File logging
        log_line = f"[{source}] {message}"
        if data:
            log_line += f" | {json.dumps(data, ensure_ascii=False)}"

        if level.upper() == "ERROR":
            self.logger.error(log_line)
        elif level.upper() == "WARN":
            self.logger.warning(log_line)
        else:
            self.logger.info(log_line)

    def attach_to_page(self, page: Page):
        """Attaches real-time browser event listeners to a Playwright page."""
        if not page or id(page) in self._attached_pages:
            return

        self._attached_pages.add(id(page))

        def on_console(msg: ConsoleMessage):
            msg_type = msg.type
            text = msg.text
            lvl = "INFO"
            if msg_type in ("error", "assert"):
                lvl = "ERROR"
            elif msg_type == "warning":
                lvl = "WARN"

            # Filter out noisy third-party tracking logs if needed
            if "yandex" in text or "metrika" in text or "google-analytics" in text:
                return

            self.log(lvl, "BROWSER_CONSOLE", f"[{msg_type}] {text}", {
                "location": msg.location,
                "url": page.url
            })

        def on_page_error(exc):
            self.log("ERROR", "PAGE_ERROR", f"Uncaught exception: {exc}", {
                "url": page.url
            })

        def on_request_failed(req: Request):
            # Log failed API/script requests (ignoring aborted trackers)
            fail = req.failure
            if fail and "net::ERR_ABORTED" not in fail:
                self.log("WARN", "NETWORK_FAILED", f"Failed: {req.method} {req.url}", {
                    "failure": fail,
                    "resource_type": req.resource_type
                })

        try:
            page.on("console", on_console)
            page.on("pageerror", on_page_error)
            page.on("requestfailed", on_request_failed)
            self.log("INFO", "AGENT", f"Attached event monitor to page: {page.url}")
        except Exception as e:
            self.log("WARN", "AGENT", f"Failed to attach page listeners: {e}")

    def get_recent_logs(self, limit: int = 50, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns recent logs from memory buffer."""
        logs = self._buffer
        if level:
            logs = [e for e in logs if e["level"] == level.upper()]
        return logs[-limit:]

    def clear(self):
        self._buffer.clear()
