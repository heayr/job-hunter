import json
import re
import urllib.parse
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from platforms.base import BasePlatform, Vacancy, ApplyResult
from platforms.superjob.auth import SuperJobAuth


class SuperJobClient(BasePlatform):
    """Client for SuperJob REST API (api.superjob.ru/2.0/)."""

    BASE_URL = "https://api.superjob.ru/2.0"

    def __init__(self, auth: SuperJobAuth):
        self.auth = auth

    def _headers(self, requires_auth: bool = True) -> Dict[str, str]:
        headers = {
            "User-Agent": "JobHunter/1.0",
            "X-Api-App-Id": self.auth.client_secret,
            "Accept": "application/json"
        }
        if requires_auth:
            token = self.auth.get_valid_access_token()
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def authenticate(self) -> bool:
        try:
            resumes = self.get_resumes()
            return isinstance(resumes, list)
        except Exception:
            return False

    def get_resumes(self) -> List[Dict[str, Any]]:
        """Fetches user's resumes on SuperJob."""
        url = f"{self.BASE_URL}/user/cvs/"
        req = urllib.request.Request(url, headers=self._headers(requires_auth=True))

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("objects", [])
                result = []
                for item in items:
                    result.append({
                        "id": str(item.get("id")),
                        "title": item.get("profession", "Резюме"),
                        "status": "Активно" if item.get("is_active") else "Скрыто",
                        "url": item.get("link", ""),
                    })
                return result
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Error fetching SuperJob resumes ({e.code}): {error_body}")

    def search_vacancies(
        self,
        query: str,
        period: int = 7,
        count: int = 50,
        page: int = 0,
        **kwargs
    ) -> List[Vacancy]:
        """Searches vacancies on SuperJob."""
        params = {
            "keyword": query,
            "count": min(count, 100),
            "page": page,
            "period": period,
            "order_field": "date",
            "order_direction": "desc"
        }

        url = f"{self.BASE_URL}/vacancies/?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=self._headers(requires_auth=False))

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                vacancies: List[Vacancy] = []

                for item in data.get("objects", []):
                    # Format salary
                    p_from = item.get("payment_from", 0)
                    p_to = item.get("payment_to", 0)
                    curr = item.get("currency", "rub")
                    if p_from and p_to:
                        salary_str = f"{p_from:,} – {p_to:,} {curr}".replace(",", " ")
                    elif p_from:
                        salary_str = f"от {p_from:,} {curr}".replace(",", " ")
                    elif p_to:
                        salary_str = f"до {p_to:,} {curr}".replace(",", " ")
                    else:
                        salary_str = "По договорённости"

                    desc_raw = item.get("candidat", "") or item.get("vacancyRichText", "")
                    desc_clean = re.sub(r'<[^>]+>', ' ', desc_raw).strip()
                    desc_clean = re.sub(r'\s+', ' ', desc_clean)

                    vacancies.append(Vacancy(
                        id=str(item.get("id")),
                        source="superjob",
                        title=item.get("profession", "Вакансия"),
                        company=item.get("firm_name", "Компания на SuperJob"),
                        url=item.get("link", f"https://www.superjob.ru/vakansii/{item.get('id')}.html"),
                        salary=salary_str,
                        location=item.get("town", {}).get("title", "РФ"),
                        is_remote=bool(item.get("place_of_work", {}).get("id") == 2),
                        published_at=str(item.get("date_pub_to")),
                        description=desc_clean,
                        raw_data=item
                    ))

                return vacancies
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Error searching SuperJob vacancies ({e.code}): {error_body}")

    def apply(self, vacancy_id: str, resume_id: str, message: str = "") -> ApplyResult:
        """Sends resume to vacancy on SuperJob via POST /2.0/send_resume/."""
        url = f"{self.BASE_URL}/send_resume/"

        payload = {
            "id_vacancy": str(vacancy_id),
            "id_cv": str(resume_id),
        }
        if message:
            payload["comment"] = message.strip()

        data = urllib.parse.urlencode(payload).encode("utf-8")
        headers = self._headers(requires_auth=True)
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = urllib.request.Request(url, data=data, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if res.get("success") or res.get("id"):
                    return ApplyResult(
                        success=True,
                        vacancy_id=vacancy_id,
                        status="applied",
                        message="Отклик успешно доставлен на SuperJob",
                        details=res
                    )
                return ApplyResult(
                    success=False,
                    vacancy_id=vacancy_id,
                    status="error",
                    message=f"Ошибка отклика: {res}",
                    details=res
                )
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            try:
                err_json = json.loads(error_body)
            except Exception:
                err_json = {}

            error_msg = str(err_json.get("error", {}).get("message") or error_body)

            if "уже отправляли" in error_msg.lower() or "already" in error_msg.lower():
                return ApplyResult(
                    success=False,
                    vacancy_id=vacancy_id,
                    status="already_applied",
                    message="Вы уже отправляли резюме на эту вакансию",
                    details=err_json
                )
            elif "лимит" in error_msg.lower() or e.code == 429:
                return ApplyResult(
                    success=False,
                    vacancy_id=vacancy_id,
                    status="limit_exceeded",
                    message="Превышен лимит откликов на SuperJob",
                    details=err_json
                )
            else:
                return ApplyResult(
                    success=False,
                    vacancy_id=vacancy_id,
                    status="error",
                    message=f"Ошибка отклика SuperJob ({e.code}): {error_msg}",
                    details=err_json
                )
