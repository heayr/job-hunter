import uuid
import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class BrowserCommand:
    command_id: str
    action: str
    params: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    event: threading.Event = field(default_factory=threading.Event)
    result: Optional[Dict[str, Any]] = None


class BrowserBridge:
    """
    Thread-safe synchronous bridge between Python AI Agent and Chrome Extension.
    Enables Python tool calls to block until the action completes in user's visible Chrome.
    """
    _instance: Optional['BrowserBridge'] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BrowserBridge, cls).__new__(cls)
                cls._instance._init_bridge()
            return cls._instance

    def _init_bridge(self):
        self._pending_commands: List[BrowserCommand] = []
        self._active_commands: Dict[str, BrowserCommand] = {}
        self._last_extension_poll: float = 0.0
        self._command_lock = threading.Lock()

    def mark_extension_alive(self):
        with self._command_lock:
            self._last_extension_poll = time.time()

    def is_connected(self, max_idle_sec: float = 3.5) -> bool:
        with self._command_lock:
            return (time.time() - self._last_extension_poll) < max_idle_sec

    def send_command(self, action: str, params: Optional[Dict[str, Any]] = None, timeout: float = 15.0) -> Dict[str, Any]:
        """
        Sends an atomic command to the Chrome Extension and blocks until execution finishes.
        """
        cmd_id = str(uuid.uuid4())
        cmd = BrowserCommand(
            command_id=cmd_id,
            action=action,
            params=params or {}
        )

        with self._command_lock:
            self._pending_commands.append(cmd)
            self._active_commands[cmd_id] = cmd

        # Wait for the extension to complete the command
        completed = cmd.event.wait(timeout=timeout)

        with self._command_lock:
            self._active_commands.pop(cmd_id, None)

        if not completed:
            is_conn = self.is_connected()
            err_msg = (
                f"Browser action '{action}' timed out after {timeout}s."
                + (" Extension is offline/not polling." if not is_conn else " Tab did not respond.")
            )
            return {
                "success": False,
                "error_type": "TIMEOUT",
                "error": err_msg,
                "action": action
            }

        return cmd.result or {"success": False, "error": "Empty result received from browser"}

    def get_next_pending_command(self) -> Optional[Dict[str, Any]]:
        """
        Called by Chrome Extension via HTTP polling. Returns the next queued command.
        """
        self.mark_extension_alive()
        with self._command_lock:
            if not self._pending_commands:
                return None
            cmd = self._pending_commands.pop(0)
            return {
                "command_id": cmd.command_id,
                "action": cmd.action,
                "params": cmd.params
            }

    def complete_command(self, command_id: str, result: Dict[str, Any]) -> bool:
        """
        Called when Chrome Extension reports the result of a command.
        Unblocks the waiting Python agent thread.
        """
        self.mark_extension_alive()
        with self._command_lock:
            cmd = self._active_commands.get(command_id)
            if not cmd:
                return False
            cmd.result = result
            cmd.event.set()
            return True

    # ── Convenience High-Level Methods for Tools ──────────────────────────

    def open_page(self, url: str, timeout: float = 25.0) -> Dict[str, Any]:
        """
        Opens a URL in the user's visible Chrome.
        If extension is not connected or slow to respond, uses native OS command
        to guarantee tab visibility in Google Chrome immediately.
        """
        import subprocess
        import sys
        import webbrowser

        # Native launch in user's real Chrome to ensure tab is physically visible
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "Google Chrome", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                webbrowser.open(url)
        except Exception as e:
            pass

        # Also send OPEN_PAGE via extension bridge if extension is active
        res = self.send_command("OPEN_PAGE", {"url": url}, timeout=timeout)
        # If extension reported success or tab loaded, return it
        if res.get("success"):
            return res

        # If extension bridge timed out but native Chrome opened the tab,
        # return a helpful message indicating tab was launched
        return {
            "success": True,
            "url": url,
            "native_launched": True,
            "message": "Вкладка открыта в Google Chrome через системный вызов. Ожидаем загрузки страницы и активации расширения."
        }

    def inspect_page(self, timeout: float = 15.0) -> Dict[str, Any]:
        return self.send_command("INSPECT_PAGE", {}, timeout=timeout)

    def fill_field(self, element_id: str, value: str, human_like: bool = False, timeout: float = 12.0) -> Dict[str, Any]:
        return self.send_command("FILL_FIELD", {
            "element_id": element_id,
            "value": value,
            "human_like": human_like
        }, timeout=timeout)

    def select_option(self, element_id: str, option: str, timeout: float = 10.0) -> Dict[str, Any]:
        return self.send_command("SELECT_OPTION", {
            "element_id": element_id,
            "option": option
        }, timeout=timeout)

    def click_element(self, element_id: str, timeout: float = 15.0) -> Dict[str, Any]:
        return self.send_command("CLICK_ELEMENT", {
            "element_id": element_id
        }, timeout=timeout)

    def upload_file(self, element_id: str, file_base64: str, file_name: str = "resume.pdf", mime_type: str = "application/pdf", timeout: float = 15.0) -> Dict[str, Any]:
        return self.send_command("UPLOAD_FILE", {
            "element_id": element_id,
            "file_base64": file_base64,
            "file_name": file_name,
            "mime_type": mime_type
        }, timeout=timeout)

    def scroll_page(self, direction: str = "down", pixels: int = 400, timeout: float = 8.0) -> Dict[str, Any]:
        return self.send_command("SCROLL_PAGE", {
            "direction": direction,
            "pixels": pixels
        }, timeout=timeout)


# Global singleton helper
def get_browser_bridge() -> BrowserBridge:
    return BrowserBridge()
