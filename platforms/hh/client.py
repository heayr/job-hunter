import json
import re
import urllib.parse
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from platforms.base import BasePlatform, Vacancy, ApplyResult
from platforms.hh.auth import HHAuth


class HHClient(BasePlatform):
    """Client for HeadHunter official REST API (api.hh.ru)."""

    BASE_URL = "https://api.hh.ru"

    def __init__(self, auth: HHAuth, user_agent_email: str = "applicant@example.com"):
        self.auth = auth
        self.user_agent = f"JobHunterApp/1.0 ({user_agent_email})"

    def _headers(self, requires_auth: bool = True) -> Dict[str, str]:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json"
        }
        if requires_auth:
            token = self.auth.get_valid_access_token()
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def authenticate(self) -> bool:
        """Verifies if token is loaded and valid."""
        try:
            resumes = self.get_resumes()
            return isinstance(resumes, list)
        except Exception:
            return False

    def get_resumes(self) -> List[Dict[str, Any]]:
        """Fetches the user's resumes from HeadHunter."""
        url = f"{self.BASE_URL}/resumes/mine"
        req = urllib.request.Request(url, headers=self._headers(requires_auth=True))

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("items", [])
                result = []
                for item in items:
                    result.append({
                        "id": item.get("id"),
                        "title": item.get("title", "Без названия"),
                        "status": item.get("status", {}).get("name", "Не указан"),
                        "url": item.get("alternate_url", ""),
                        "skills": [s.get("name") for s in item.get("skill_set", [])]
                    })
                return result
        except urllib.error.HTTPError as e:
            error_msg = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Error fetching resumes ({e.code}): {error_msg}")

    def search_vacancies(
        self,
        query: str,
        area: Optional[int] = None,
        salary: Optional[int] = None,
        only_with_salary: bool = False,
        experience: Optional[str] = None,
        schedule: Optional[str] = None,
        period: int = 7,
        per_page: int = 50,
        page: int = 0
    ) -> List[Vacancy]:
        """Searches vacancies via api.hh.ru."""
        params: Dict[str, Any] = {
            "text": query,
            "order_by": "publication_time",
            "period": period,
            "per_page": min(per_page, 100),
            "page": page,
        }

        if area:
            params["area"] = area
        if salary:
            params["salary"] = salary
        if only_with_salary:
            params["only_with_salary"] = "true"
        if experience:
            params["experience"] = experience
        if schedule:
            params["schedule"] = schedule

        url = f"{self.BASE_URL}/vacancies?{urllib.parse.urlencode(params)}"
        # Search can work with or without auth, but using auth gives accurate application status
        req = urllib.request.Request(url, headers=self._headers(requires_auth=bool(self.auth.tokens.get("access_token"))))

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                vacancies: List[Vacancy] = []

                for item in data.get("items", []):
                    if item.get("archived"):
                        continue

                    # Extract salary string
                    salary_str = "Не указана"
                    if item.get("salary"):
                        sal = item["salary"]
                        fr = sal.get("from")
                        to = sal.get("to")
                        curr = sal.get("currency", "RUR")
                        if fr and to:
                            salary_str = f"{fr} - {to} {curr}"
                        elif fr:
                            salary_str = f"от {fr} {curr}"
                        elif to:
                            salary_str = f"до {to} {curr}"

                    is_remote = item.get("schedule", {}).get("id") == "remote"

                    vacancies.append(Vacancy(
                        id=str(item.get("id")),
                        source="hh.ru",
                        title=item.get("name", "Вакансия"),
                        company=item.get("employer", {}).get("name", "Компания на HH"),
                        url=item.get("alternate_url", f"https://hh.ru/vacancy/{item.get('id')}"),
                        salary=salary_str,
                        location=item.get("area", {}).get("name", "РФ"),
                        is_remote=is_remote,
                        published_at=item.get("published_at"),
                        has_test=bool(item.get("has_test")),
                        raw_data=item
                    ))

                return vacancies
        except urllib.error.HTTPError as e:
            error_msg = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Error searching HH vacancies ({e.code}): {error_msg}")

    def get_vacancy_details(self, vacancy_id: str) -> Dict[str, Any]:
        """Fetches detailed vacancy description and requirements."""
        url = f"{self.BASE_URL}/vacancies/{vacancy_id}"
        req = urllib.request.Request(url, headers=self._headers(requires_auth=False))

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                desc_html = data.get("description", "")
                desc_clean = re.sub(r'<[^>]+>', ' ', desc_html).strip()
                desc_clean = re.sub(r'\s+', ' ', desc_clean)
                key_skills = [s.get("name", "") for s in data.get("key_skills", [])]

                return {
                    "id": str(data.get("id")),
                    "title": data.get("name", ""),
                    "company": data.get("employer", {}).get("name", ""),
                    "description": desc_clean,
                    "key_skills": key_skills,
                    "has_test": bool(data.get("has_test")),
                    "test": data.get("test")
                }
        except urllib.error.HTTPError as e:
            error_msg = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Error fetching vacancy details ({e.code}): {error_msg}")

    def apply(self, vacancy_id: str, resume_id: str, message: str = "") -> ApplyResult:
        """
        Sends an application (negotiation) to a vacancy via POST api.hh.ru/negotiations.
        """
        url = f"{self.BASE_URL}/negotiations"

        payload = {
            "vacancy_id": str(vacancy_id),
            "resume_id": str(resume_id),
        }
        if message and message.strip():
            payload["message"] = message.strip()

        data = urllib.parse.urlencode(payload).encode("utf-8")

        headers = self._headers(requires_auth=True)
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = urllib.request.Request(url, data=data, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                # 201 Created is the expected success response from HH
                return ApplyResult(
                    success=True,
                    vacancy_id=vacancy_id,
                    status="applied",
                    message="Отклик успешно доставлен",
                    details={"status_code": resp.status}
                )
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            try:
                err_json = json.loads(error_body)
            except Exception:
                err_json = {}

            errors = err_json.get("errors", [])
            error_types = [err.get("value") or err.get("type") for err in errors]

            if "negotiations_limit_exceeded" in error_types or e.code == 429:
                return ApplyResult(
                    success=False,
                    vacancy_id=vacancy_id,
                    status="limit_exceeded",
                    message="Достигнут суточный лимит откликов на HeadHunter",
                    details=err_json
                )
            elif "already_applied" in error_types or "negotiation_already_exists" in error_types:
                return ApplyResult(
                    success=False,
                    vacancy_id=vacancy_id,
                    status="already_applied",
                    message="Вы уже откликались на эту вакансию ранее",
                    details=err_json
                )
            elif "test_required" in error_types or "requires_test" in error_types:
                return ApplyResult(
                    success=False,
                    vacancy_id=vacancy_id,
                    status="test_required",
                    message="Вакансия требует прохождения обязательного теста/опросника",
                    details=err_json
                )
            else:
                return ApplyResult(
                    success=False,
                    vacancy_id=vacancy_id,
                    status="error",
                    message=f"Ошибка отклика ({e.code}): {error_body}",
                    details=err_json
                )
