from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Vacancy:
    id: str
    source: str
    title: str
    company: str
    url: str
    salary: str = "Не указана"
    location: str = "РФ / Remote"
    is_remote: bool = False
    skills: List[str] = field(default_factory=list)
    description: str = ""
    published_at: Optional[str] = None
    has_test: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApplyResult:
    success: bool
    vacancy_id: str
    status: str  # "applied", "already_applied", "limit_exceeded", "test_required", "error"
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class BasePlatform(ABC):
    """Abstract base class for job platforms."""

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate or verify existing token."""
        pass

    @abstractmethod
    def search_vacancies(self, query: str, **kwargs) -> List[Vacancy]:
        """Search vacancies on the platform."""
        pass

    @abstractmethod
    def get_resumes(self) -> List[Dict[str, Any]]:
        """Fetch list of user's resumes on the platform."""
        pass

    @abstractmethod
    def apply(self, vacancy_id: str, resume_id: str, message: str = "") -> ApplyResult:
        """Apply to a vacancy."""
        pass
