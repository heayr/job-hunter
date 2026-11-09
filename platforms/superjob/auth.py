import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

SJ_AUTH_URL = "https://www.superjob.ru/authorize/"
SJ_TOKEN_URL = "https://api.superjob.ru/2.0/oauth2/token/"


class SuperJobAuth:
    """Manages SuperJob OAuth 2.0 authorization, tokens and refresh."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "https://httpbin.org/get", token_file: str = "tokens/superjob_token.json"):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()  # In SuperJob, client_secret is also used as App-Token (X-Api-App-Id)
        self.redirect_uri = redirect_uri.strip()
        self.token_file = token_file
        self.tokens: Dict[str, Any] = {}
        self.load_tokens()

    def get_authorization_url(self) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        return f"{SJ_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        params = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code.strip(),
            "redirect_uri": self.redirect_uri,
        }
        url = f"{SJ_TOKEN_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "JobHunter/1.0"})

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                data["saved_at"] = time.time()
                self.tokens = data
                self.save_tokens()
                return data
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"SuperJob OAuth Error ({e.code}): {error_body}")

    def refresh_access_token(self) -> Dict[str, Any]:
        refresh_token = self.tokens.get("refresh_token")
        if not refresh_token:
            raise RuntimeError("No refresh_token found for SuperJob.")

        params = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }
        url = f"{SJ_TOKEN_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "JobHunter/1.0"})

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                data["saved_at"] = time.time()
                self.tokens = data
                self.save_tokens()
                return data
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"SuperJob Token Refresh Error ({e.code}): {error_body}")

    def get_valid_access_token(self) -> str:
        if not self.tokens or not self.tokens.get("access_token"):
            raise RuntimeError("SuperJob access token missing. Please authorize first.")

        expires_in = self.tokens.get("expires_in", 604800)
        saved_at = self.tokens.get("saved_at", 0)

        if time.time() - saved_at > (expires_in - 300):
            self.refresh_access_token()

        return self.tokens.get("access_token", "")

    def load_tokens(self) -> None:
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r", encoding="utf-8") as f:
                    self.tokens = json.load(f)
            except Exception:
                self.tokens = {}

    def save_tokens(self) -> None:
        os.makedirs(os.path.dirname(self.token_file) or ".", exist_ok=True)
        with open(self.token_file, "w", encoding="utf-8") as f:
            json.dump(self.tokens, f, ensure_ascii=False, indent=2)
