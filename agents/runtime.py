import json
import time
from enum import Enum
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from tracker.db import update_vacancy_fsm_state, get_vacancy_fsm_state, get_db_connection


class ApplicationState(str, Enum):
    DISCOVERED = "DISCOVERED"
    ANALYZING = "ANALYZING"
    RESEARCHING = "RESEARCHING"
    MATCHED = "MATCHED"
    STRATEGY_READY = "STRATEGY_READY"
    ARTIFACTS_READY = "ARTIFACTS_READY"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"


# Valid State Transitions Table
ALLOWED_TRANSITIONS: Dict[ApplicationState, Set[ApplicationState]] = {
    ApplicationState.DISCOVERED: {ApplicationState.ANALYZING, ApplicationState.FAILED},
    ApplicationState.ANALYZING: {ApplicationState.RESEARCHING, ApplicationState.FAILED},
    ApplicationState.RESEARCHING: {ApplicationState.MATCHED, ApplicationState.FAILED},
    ApplicationState.MATCHED: {ApplicationState.STRATEGY_READY, ApplicationState.FAILED},
    ApplicationState.STRATEGY_READY: {ApplicationState.ARTIFACTS_READY, ApplicationState.FAILED},
    ApplicationState.ARTIFACTS_READY: {ApplicationState.WAITING_APPROVAL, ApplicationState.FAILED},
    ApplicationState.WAITING_APPROVAL: {ApplicationState.SUBMITTED, ApplicationState.FAILED, ApplicationState.STRATEGY_READY},
    ApplicationState.SUBMITTED: set(),
    ApplicationState.FAILED: {ApplicationState.DISCOVERED, ApplicationState.ANALYZING} # Retry capability
}


class InvalidStateTransitionError(Exception):
    pass


class AgentRuntime:
    """
    Finite State Machine Runtime governing vacancy lifecycle execution.
    Manages state transitions, timeouts, retry limits, and step audit records.
    """
    def __init__(self, vacancy_id: str, timeout_sec: float = 30.0, max_retries: int = 2):
        self.vacancy_id = vacancy_id
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        self.state = self._load_current_state()
        self.history: List[Dict[str, Any]] = []

    def _load_current_state(self) -> ApplicationState:
        try:
            val = get_vacancy_fsm_state(self.vacancy_id)
            return ApplicationState(val)
        except Exception:
            return ApplicationState.DISCOVERED

    def transition_to(self, next_state: ApplicationState, reason: str = "") -> None:
        """
        Validates and performs an atomic state transition.
        Raises InvalidStateTransitionError if the transition is illegal.
        """
        if next_state not in ALLOWED_TRANSITIONS.get(self.state, set()):
            raise InvalidStateTransitionError(
                f"Illegal state transition from {self.state} to {next_state} for vacancy {self.vacancy_id}"
            )

        prev_state = self.state
        self.state = next_state
        update_vacancy_fsm_state(self.vacancy_id, self.state.value)

        record = {
            "from_state": prev_state.value,
            "to_state": next_state.value,
            "reason": reason,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.history.append(record)

    def execute_lifecycle(self, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the full FSM lifecycle step-by-step from current state up to WAITING_APPROVAL.
        """
        from agents.multi_agent_roles import (
            JobAnalystAgent,
            CompanyResearcherAgent,
            CandidateStrategistAgent,
            WriterAgent,
            CriticAgent,
            FactCheckerAgent
        )

        ctx = dict(initial_context)
        ctx["vacancy_id"] = self.vacancy_id
        start_time = time.time()

        try:
            # 1. DISCOVERED -> ANALYZING
            if self.state == ApplicationState.DISCOVERED:
                self.transition_to(ApplicationState.ANALYZING, "Starting Job Understanding")
                ja = JobAnalystAgent()
                ctx.update(ja.execute(ctx))

            # 2. ANALYZING -> RESEARCHING
            if self.state == ApplicationState.ANALYZING:
                if (time.time() - start_time) > self.timeout_sec:
                    raise TimeoutError("Execution timed out in ANALYZING")
                self.transition_to(ApplicationState.RESEARCHING, "Starting Company Research")
                cr = CompanyResearcherAgent()
                ctx.update(cr.execute(ctx))

            # 3. RESEARCHING -> MATCHED
            if self.state == ApplicationState.RESEARCHING:
                if (time.time() - start_time) > self.timeout_sec:
                    raise TimeoutError("Execution timed out in RESEARCHING")
                self.transition_to(ApplicationState.MATCHED, "Reframing candidate evidence")
                # Strategy agent step 1
                strat_agent = CandidateStrategistAgent()
                strat_res = strat_agent.execute(ctx)
                ctx.update(strat_res)

            # 4. MATCHED -> STRATEGY_READY
            if self.state == ApplicationState.MATCHED:
                self.transition_to(ApplicationState.STRATEGY_READY, "Application Strategy formulated")

            # 5. STRATEGY_READY -> ARTIFACTS_READY
            if self.state == ApplicationState.STRATEGY_READY:
                if (time.time() - start_time) > self.timeout_sec:
                    raise TimeoutError("Execution timed out in STRATEGY_READY")
                writer = WriterAgent()
                critic = CriticAgent()
                fact_checker = FactCheckerAgent()

                ctx.update(writer.execute(ctx))
                ctx.update(critic.execute(ctx))
                ctx.update(fact_checker.execute(ctx))

                self.transition_to(ApplicationState.ARTIFACTS_READY, "Tailored artifacts and critique complete")

            # 6. ARTIFACTS_READY -> WAITING_APPROVAL
            if self.state == ApplicationState.ARTIFACTS_READY:
                self.transition_to(ApplicationState.WAITING_APPROVAL, "Ready for human review and submission")

            ctx["fsm_state"] = self.state.value
            ctx["fsm_history"] = self.history
            ctx["success"] = True
            return ctx

        except Exception as e:
            self.transition_to(ApplicationState.FAILED, f"Runtime error: {str(e)}")
            ctx["fsm_state"] = self.state.value
            ctx["fsm_history"] = self.history
            ctx["success"] = False
            ctx["error"] = str(e)
            return ctx
