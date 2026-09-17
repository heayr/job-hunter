import unittest
from agents.tool_system import (
    ToolRegistry,
    ToolDefinition,
    ToolPermission,
    ToolValidationError
)

class TestToolSystem(unittest.TestCase):
    def test_registered_tools_list(self):
        tools = ToolRegistry.list_tools()
        self.assertGreaterEqual(len(tools), 6)
        names = [t["name"] for t in tools]
        self.assertIn("understand_job", names)
        self.assertIn("research_company", names)
        self.assertIn("reframe_evidence", names)
        self.assertIn("generate_tailored_resume", names)
        self.assertIn("audit_ats", names)
        self.assertIn("verify_facts", names)

    def test_tool_schema_validation_success(self):
        res = ToolRegistry.execute_tool("understand_job", {
            "title": "Senior React Engineer",
            "company": "TechCorp",
            "description": "Building modern React apps"
        })
        self.assertTrue(res["success"])
        self.assertIn("result", res)
        self.assertEqual(res["result"]["role_overview"]["title"], "Senior React Engineer")

    def test_tool_schema_validation_failure_missing_arg(self):
        res = ToolRegistry.execute_tool("understand_job", {
            "company": "TechCorp"
            # Missing required "title"
        })
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "VALIDATION_ERROR")
        self.assertIn("missing required argument", res["error"].lower())

    def test_tool_schema_validation_failure_wrong_type(self):
        res = ToolRegistry.execute_tool("understand_job", {
            "title": 12345  # Should be string
        })
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "VALIDATION_ERROR")
        self.assertIn("must be a string", res["error"].lower())

    def test_audit_ats_tool_execution(self):
        sample_resume = {
            "candidate_identity": {"name": "Егор", "target_title": "Senior Frontend", "contacts": "@PotatoChipasu"},
            "professional_summary": "Autonomous Senior Product Engineer specializing in React 19.",
            "highlighted_skills": ["React 19", "TypeScript", "Next.js 16"],
            "relevant_experience": [{"role": "Senior Engineer", "company": "TechCorp", "accomplishments": ["Built core client apps"]}],
            "education": [{"degree": "Technical", "institution": "BMSTU", "years": "2020"}]
        }
        sample_ju = {
            "role_overview": {"title": "Senior Frontend Developer"},
            "facts": {"explicit_requirements": ["React 19", "TypeScript"]}
        }
        res = ToolRegistry.execute_tool("audit_ats", {
            "resume_dict": sample_resume,
            "job_understanding": sample_ju,
            "lang": "ru"
        })
        self.assertTrue(res["success"])
        self.assertIn("ats_score", res["result"])

    def test_verify_facts_tool_execution(self):
        res_ok = ToolRegistry.execute_tool("verify_facts", {
            "text": "React 19 and Next.js 16 engineering."
        })
        self.assertTrue(res_ok["success"])
        self.assertTrue(res_ok["result"]["verified"])

        res_danger = ToolRegistry.execute_tool("verify_facts", {
            "text": "Solidity smart contract and Kafka cluster."
        })
        self.assertTrue(res_danger["success"])
        self.assertFalse(res_danger["result"]["verified"])

if __name__ == "__main__":
    unittest.main()
