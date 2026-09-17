import unittest
from agents.runtime import (
    ApplicationState,
    AgentRuntime,
    InvalidStateTransitionError,
    ALLOWED_TRANSITIONS
)
from tracker.db import (
    init_db,
    save_vacancy,
    update_vacancy_fsm_state,
    get_vacancy_fsm_state,
    get_db_connection
)

class TestAgentRuntime(unittest.TestCase):
    def setUp(self):
        init_db()
        self.vac = {
            "id": "vac_fsm_test_01",
            "title": "Senior Frontend Developer",
            "company": "FSMCorp",
            "url": "https://fsmcorp.example.com/jobs/1",
            "source": "test",
            "description": "React 19, TypeScript, Next.js 16"
        }
        save_vacancy(self.vac)

    def tearDown(self):
        conn = get_db_connection()
        conn.execute("DELETE FROM vacancies WHERE id = ?", (self.vac["id"],))
        conn.commit()
        conn.close()

    def test_initial_fsm_state_is_discovered(self):
        state = get_vacancy_fsm_state(self.vac["id"])
        self.assertEqual(state, ApplicationState.DISCOVERED.value)

    def test_valid_state_transitions(self):
        runtime = AgentRuntime(self.vac["id"])
        self.assertEqual(runtime.state, ApplicationState.DISCOVERED)

        # 1. DISCOVERED -> ANALYZING
        runtime.transition_to(ApplicationState.ANALYZING, "Job requirements parsing")
        self.assertEqual(runtime.state, ApplicationState.ANALYZING)
        self.assertEqual(get_vacancy_fsm_state(self.vac["id"]), "ANALYZING")

        # 2. ANALYZING -> RESEARCHING
        runtime.transition_to(ApplicationState.RESEARCHING, "Company intelligence")
        self.assertEqual(runtime.state, ApplicationState.RESEARCHING)

        # 3. RESEARCHING -> MATCHED
        runtime.transition_to(ApplicationState.MATCHED, "Candidate evidence reframing")
        self.assertEqual(runtime.state, ApplicationState.MATCHED)

        # 4. MATCHED -> STRATEGY_READY
        runtime.transition_to(ApplicationState.STRATEGY_READY, "Application strategy formulated")
        self.assertEqual(runtime.state, ApplicationState.STRATEGY_READY)

        # 5. STRATEGY_READY -> ARTIFACTS_READY
        runtime.transition_to(ApplicationState.ARTIFACTS_READY, "Tailored CV and letters ready")
        self.assertEqual(runtime.state, ApplicationState.ARTIFACTS_READY)

        # 6. ARTIFACTS_READY -> WAITING_APPROVAL
        runtime.transition_to(ApplicationState.WAITING_APPROVAL, "Ready for user review")
        self.assertEqual(runtime.state, ApplicationState.WAITING_APPROVAL)

        # 7. WAITING_APPROVAL -> SUBMITTED
        runtime.transition_to(ApplicationState.SUBMITTED, "Applied via form/email")
        self.assertEqual(runtime.state, ApplicationState.SUBMITTED)

    def test_illegal_state_transition_raises_error(self):
        runtime = AgentRuntime(self.vac["id"])
        self.assertEqual(runtime.state, ApplicationState.DISCOVERED)

        # Direct jump DISCOVERED -> SUBMITTED without intermediate stages must be rejected
        with self.assertRaises(InvalidStateTransitionError):
            runtime.transition_to(ApplicationState.SUBMITTED, "Illegal skip")

    def test_failure_transition_and_recovery(self):
        runtime = AgentRuntime(self.vac["id"])
        runtime.transition_to(ApplicationState.ANALYZING, "Analyzing")
        runtime.transition_to(ApplicationState.FAILED, "Network timeout")
        self.assertEqual(runtime.state, ApplicationState.FAILED)

        # Allowed recovery transition FAILED -> ANALYZING (Retry)
        runtime.transition_to(ApplicationState.ANALYZING, "Retrying after failure")
        self.assertEqual(runtime.state, ApplicationState.ANALYZING)

    def test_execute_lifecycle_end_to_end(self):
        runtime = AgentRuntime(self.vac["id"])
        initial_ctx = {
            "title": self.vac["title"],
            "description": self.vac["description"],
            "company": self.vac["company"],
            "url": self.vac["url"],
            "lang": "ru",
            "use_ai": False
        }
        res = runtime.execute_lifecycle(initial_ctx)

        self.assertTrue(res["success"])
        self.assertEqual(res["fsm_state"], ApplicationState.WAITING_APPROVAL.value)
        self.assertEqual(get_vacancy_fsm_state(self.vac["id"]), ApplicationState.WAITING_APPROVAL.value)
        self.assertGreaterEqual(len(res["fsm_history"]), 5)

if __name__ == "__main__":
    unittest.main()
