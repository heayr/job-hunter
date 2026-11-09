import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

HH_AUTH_URL = "https://hh.ru/oauth/authorize"
HH_TOKEN_URL = "https://hh.ru/oauth/token"
DEFAULT_REDIRECT_URI = "https://httpbin.org/get"  # standard helper redirect or custom uri


class HHAuth:
    """Manages HeadHunter OAuth 2.0 authorization, token storage, and refresh."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = DEFAULT_REDIRECT_URI, token_file: str = "tokens/hh_token.json"):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.redirect_uri = redirect_uri.strip()
        self.token_file = token_file
        self.tokens: Dict[str, Any] = {}
        self.load_tokens()

    def get_authorization_url(self) -> str:
        """Generates the URL where user must log in and authorize the application."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        return f"{HH_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchanges authorization code for access_token and refresh_token."""
        data = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code.strip(),
            "redirect_uri": self.redirect_uri,
        }).encode("utf-8")

        req = urllib.request.Request(
            HH_TOKEN_URL,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "JobHunter/1.0"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                resp_data["saved_at"] = time.time()
                self.tokens = resp_data
                self.save_tokens()
                return resp_data
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HH OAuth Error ({e.code}): {error_body}")

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refreshes an expired access_token using refresh_token."""
        refresh_token = self.tokens.get("refresh_token")
        if not refresh_token:
            raise RuntimeError("No refresh_token found. Please authorize again.")

        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }).encode("utf-8")

        req = urllib.request.Request(
            HH_TOKEN_URL,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "JobHunter/1.0"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                resp_data["saved_at"] = time.time()
                self.tokens = resp_data
                self.save_tokens()
                return resp_data
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HH Token Refresh Error ({e.code}): {error_body}")

    def get_valid_access_token(self) -> str:
        """Returns valid access_token, refreshing it automatically if expired."""
        if not self.tokens or not self.tokens.get("access_token"):
            raise RuntimeError("Access token missing. Run authorization first.")

        expires_in = self.tokens.get("expires_in", 1209600)
        saved_at = self.tokens.get("saved_at", 0)

        # If token expires in less than 5 minutes, refresh it
        if time.time() - saved_at > (expires_in - 300):
            self.refresh_access_token()

        return self.tokens.get("access_token", "")

    def load_tokens(self) -> None:
        """Loads tokens from disk."""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r", encoding="utf-8") as f:
                    self.tokens = json.load(f)
            except Exception:
                self.tokens = {}

    def save_tokens(self) -> None:
        """Saves tokens to disk."""
        os.makedirs(os.path.dirname(self.token_file) or ".", exist_ok=True)
        with open(self.token_file, "w", encoding="utf-8") as f:
            json.dump(self.tokens, f, ensure_ascii=False, indent=2)
