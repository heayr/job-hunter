import os
import json
import time
import uuid
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

from tracker.db import (
    create_agent_session,
    update_agent_session,
    record_session_step,
    get_agent_session
)
from agents.tool_system import ToolRegistry, ToolPermission
from agents.event_bus import get_event_bus
from generator.llm_generator import get_api_key, GEMINI_MODELS
from generator.candidate_profile import get_canonical_profile


SYSTEM_PROMPT_TEMPLATE = """You are an Autonomous AI Career Agent acting on behalf of a Senior Engineer.
Your goal is to inspect a job vacancy application form in the browser, determine its structure, match it with the candidate's canonical verified experience, fill the form accurately, verify everything, and stop for human approval.

CRITICAL INVARIANTS:
1. ZERO HALLUCINATION: You are strictly forbidden from inventing companies, skills, years of experience, credentials, or metrics. All technical claims must come from the candidate's Master Experience.
2. SUPERVISED SAFETY: In SUPERVISED mode, you must NEVER submit the form automatically. When the form is completely filled and verified, you MUST call 'request_human_approval'.
3. ERROR RECOVERY: If an element is not found or changed, do NOT panic. Call 'browser_inspect_page' to re-inspect the live DOM and adapt.
4. UNKNOWN QUESTIONS: If a question requires personal information or policies not in Master Experience (e.g. unknown salary or complex legal question), do NOT guess. Call 'ask_user_clarification'.

AVAILABLE TOOLS:
{tools_schema}

CANDIDATE MASTER PROFILE (CANONICAL TRUTH):
- Name: {candidate_name}
- Email: {candidate_email}
- Phone: {candidate_phone}
- Location: {candidate_location}
- Telegram: {candidate_telegram}
- LinkedIn: {candidate_linkedin}
- GitHub: {candidate_github}
- Portfolio: {candidate_portfolio}
- Verified Skills: {candidate_skills}
- Key Evidence & Experience:
{candidate_evidence}

RESPONSE FORMAT:
You MUST respond with a single valid JSON object containing:
{{
  "thought": "Your concise step-by-step reasoning about what you observe and what to do next",
  "action": "name_of_the_tool_to_call",
  "arguments": {{ ... tool arguments ... }}
}}
"""


class CareerAgentBrain:
    """
    Cognitive ReAct Agent Brain executing the autonomous Career Agent loop.
    Observes DOM state, reasons via LLM, calls atomic tools, records steps,
    and manages state transitions and human-in-the-loop approvals.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        vacancy_id: Optional[str] = None,
        target_url: str = "",
        mode: str = "SUPERVISED",
        max_steps: int = 25
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.vacancy_id = vacancy_id
        self.target_url = target_url
        self.mode = mode
        self.max_steps = max_steps
        self.scratchpad: List[Dict[str, Any]] = []
        self.step_counter = 0
        self.event_bus = get_event_bus()
        self.plan_subgoals = ["DISCOVER_FORM", "FILL_FIELDS", "VERIFY_DATA", "REQUEST_APPROVAL"]
        self.current_subgoal = "DISCOVER_FORM"
        self._action_signatures: List[str] = []

    def _build_tools_description(self) -> str:
        tools = ToolRegistry.list_tools()
        desc_lines = []
        for t in tools:
            desc_lines.append(f"- Tool: {t['name']}")
            desc_lines.append(f"  Description: {t['description']}")
            desc_lines.append(f"  Parameters: {json.dumps(t['schema'].get('properties', {}), ensure_ascii=False)}")
            desc_lines.append(f"  Required: {json.dumps(t['schema'].get('required', []))}")
        return "\n".join(desc_lines)

    def _format_candidate_context(self, profile: Dict[str, Any]) -> Dict[str, str]:
        ident = profile.get("identity", {})
        contacts = ident.get("contacts", {})
        evidence = profile.get("evidence", [])
        ev_summary = []
        for ev in evidence[:10]:
            ev_summary.append(f"  * [{ev.get('id')}]: {ev.get('claim')} (Tech: {', '.join(ev.get('technologies', []))})")

        return {
            "candidate_name": ident.get("name", "Candidate"),
            "candidate_email": contacts.get("email", ""),
            "candidate_phone": contacts.get("phone", ""),
            "candidate_location": ident.get("location", ""),
            "candidate_telegram": contacts.get("telegram", ""),
            "candidate_linkedin": contacts.get("linkedin", ""),
            "candidate_github": contacts.get("github", ""),
            "candidate_portfolio": contacts.get("portfolio", ""),
            "candidate_skills": ", ".join(profile.get("skills", [])),
            "candidate_evidence": "\n".join(ev_summary) if ev_summary else "  * General fullstack engineering evidence"
        }

    def _call_llm_decision(self, prompt: str) -> Dict[str, Any]:
        """Calls LM Studio (Local LLM) or Gemini API with structured JSON output enforcing ReAct decision."""
        from generator.llm_generator import get_llm_config, call_lm_studio
        cfg = get_llm_config()
        provider = cfg.get("provider", "gemini")

        # 1. If provider is LM Studio, call local model first
        if provider == "lm_studio":
            raw_json = call_lm_studio(prompt, json_mode=True)
            if raw_json:
                try:
                    # Clean possible markdown wrapping
                    cleaned = re.sub(r'^```(?:json)?\s*', '', raw_json.strip())
                    cleaned = re.sub(r'\s*```$', '', cleaned).strip()
                    return json.loads(cleaned)
                except Exception:
                    pass

        # 2. Otherwise try Gemini models
        api_key = cfg.get("gemini_api_key", "")
        if api_key:
            payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "response_mime_type": "application/json"
                }
            }
            data_bytes = json.dumps(payload).encode("utf-8")

            for model in GEMINI_MODELS:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"}, method="POST")
                try:
                    with urllib.request.urlopen(req, timeout=25) as resp:
                        res_json = json.loads(resp.read().decode("utf-8"))
                        text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                        return json.loads(text)
                except Exception as e:
                    continue

        # 3. If Gemini failed (e.g. 429), try LM Studio as automatic local fallback
        if provider != "lm_studio":
            raw_json = call_lm_studio(prompt, json_mode=True)
            if raw_json:
                try:
                    cleaned = re.sub(r'^```(?:json)?\s*', '', raw_json.strip())
                    cleaned = re.sub(r'\s*```$', '', cleaned).strip()
                    return json.loads(cleaned)
                except Exception:
                    pass

        return self._heuristic_fallback_decision()

    def _get_cover_letter_for_vacancy(self) -> str:
        """Retrieves tailored pitch/cover letter from SQLite vacancy or canonical profile."""
        from tracker.db import get_db_connection
        if self.vacancy_id:
            conn = get_db_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT cover_letter, short_dm FROM vacancies WHERE id = ?", (self.vacancy_id,))
                row = cur.fetchone()
                if row:
                    if row["cover_letter"] and row["cover_letter"].strip():
                        return row["cover_letter"].strip()
                    if row["short_dm"] and row["short_dm"].strip():
                        return row["short_dm"].strip()
            except Exception:
                pass
            finally:
                conn.close()

        prof = get_canonical_profile(lang="ru")
        ident = prof.get("identity", {})
        name = ident.get("name", "Егор")
        contacts = ident.get("contacts", {})
        return (
            f"Здравствуйте!\n\n"
            f"Меня заинтересовала данная позиция. Имею более 6 лет коммерческого опыта в разработке "
            f"(React, TypeScript, Next.js, Node.js) с фокусом на высокую производительность, чистую архитектуру и автономное ведение фичей в production.\n\n"
            f"Буду рад обсудить задачи и детальнее рассказать о релевантных проектах.\n\n"
            f"С уважением,\n{name}\nTG: {contacts.get('telegram', '@PotatoChipasu')} | Телефон: {contacts.get('phone', '+79998291788')}"
        )

    def _heuristic_fallback_decision(self, prompt: str = "") -> Dict[str, Any]:
        """
        Deterministic fallback when external LLM API is unavailable.
        Ensures agent can execute test workflows offline.
        """
        # Step 1: Open page if target url exists and hasn't been opened
        if self.step_counter == 1 and self.target_url:
            return {
                "thought": f"Opening target application page {self.target_url}",
                "action": "browser_open_page",
                "arguments": {"url": self.target_url}
            }

        # Step 2: Inspect page
        has_inspected = any(s["tool_name"] == "browser_inspect_page" for s in self.scratchpad)
        if not has_inspected:
            return {
                "thought": "Inspecting live page form elements to determine required fields",
                "action": "browser_inspect_page",
                "arguments": {}
            }

        # Check if auth barrier was detected on page (e.g. HH.ru login or Habr login)
        last_insp_obs = None
        for s in reversed(self.scratchpad):
            if s["tool_name"] == "browser_inspect_page" and s.get("observation"):
                obs = s["observation"].get("observation", s["observation"])
                if isinstance(obs, dict):
                    last_insp_obs = obs
                    break

        if last_insp_obs and last_insp_obs.get("auth_required"):
            portal_reason = last_insp_obs.get("auth_reason") or "Требуется авторизация на сайте вакансии"
            return {
                "thought": f"Auth barrier detected: {portal_reason}. Halting with clear instructions for user.",
                "action": "fail_session_with_error",
                "arguments": {
                    "error": f"⚠️ {portal_reason}. Пожалуйста, войдите в свой аккаунт на открытой вкладке Chrome и запустите отклик повторно."
                }
            }

        # Step 3: Classify inspected elements if not classified yet or if newly loaded view after click
        last_insp_idx = -1
        last_class_idx = -1
        last_click_idx = -1
        last_insp_elements = []
        for i, s in enumerate(self.scratchpad):
            if s["tool_name"] == "browser_inspect_page" and s.get("observation"):
                last_insp_idx = i
                obs = s["observation"].get("observation", s["observation"])
                if isinstance(obs, dict):
                    last_insp_elements = obs.get("interactive_elements", [])
            elif s["tool_name"] == "candidate_classify_form":
                last_class_idx = i
            elif s["tool_name"] == "browser_click_element":
                last_click_idx = i

        needs_classification = (last_class_idx == -1 and last_insp_idx > -1) or (last_click_idx > last_class_idx and last_insp_idx > last_click_idx)
        if needs_classification and last_insp_elements:
            return {
                "thought": "Classifying page form fields against candidate Master Experience",
                "action": "candidate_classify_form",
                "arguments": {"elements": last_insp_elements}
            }

        # Retrieve latest classified elements
        classified = []
        for s in reversed(self.scratchpad):
            if s["tool_name"] == "candidate_classify_form" and s.get("observation"):
                classified = s["observation"].get("classified_elements", [])
                break

        # Step 3.5: If page has an entry button (e.g. "Откликнуться" before form modal is opened)
        entry_btn = next((item for item in classified if item.get("category") == "APPLY_ENTRY_BUTTON"), None)
        clicked_entry_ids = {s["arguments"].get("element_id") for s in self.scratchpad if s["tool_name"] == "browser_click_element"}
        if entry_btn and entry_btn.get("element_id") not in clicked_entry_ids:
            return {
                "thought": f"Opening application modal by clicking '{entry_btn.get('label', 'Откликнуться')}'",
                "action": "browser_click_element",
                "arguments": {"element_id": entry_btn.get("element_id")}
            }

        # If the immediate prior step was clicking an element (entry button or next step), re-inspect to observe the opened modal form
        last_step = self.scratchpad[-1] if self.scratchpad else {}
        if last_step.get("tool_name") == "browser_click_element":
            return {
                "thought": "Re-inspecting DOM to observe application form fields after clicking button",
                "action": "browser_inspect_page",
                "arguments": {}
            }

        # Check compiled resume artifact
        compiled_cv = None
        for s in self.scratchpad:
            if s["tool_name"] == "candidate_compile_resume" and s.get("observation"):
                compiled_cv = s["observation"]
                break

        uploaded_ids = {s["arguments"].get("element_id") for s in self.scratchpad if s["tool_name"] == "browser_upload_cv"}
        filled_ids = {s["arguments"].get("element_id") for s in self.scratchpad if s["tool_name"] == "browser_fill_field"}
        selected_ids = {s["arguments"].get("element_id") for s in self.scratchpad if s["tool_name"] == "browser_select_option"}

        # Step 4: If there is a file input for resume and not yet compiled, compile it
        for item in classified:
            eid = item.get("element_id")
            cat = item.get("category")
            if cat == "RESUME_FILE" and not compiled_cv:
                return {
                    "thought": "Compiling tailored ATS resume with evidence provenance linking",
                    "action": "candidate_compile_resume",
                    "arguments": {"session_id": self.session_id}
                }
            elif cat == "RESUME_FILE" and compiled_cv and eid not in uploaded_ids:
                return {
                    "thought": f"Uploading compiled tailored resume to element {eid}",
                    "action": "browser_upload_cv",
                    "arguments": {
                        "element_id": eid,
                        "file_base64": compiled_cv.get("file_base64", ""),
                        "file_name": compiled_cv.get("file_name", "CV.txt")
                    }
                }

        # Step 5: Fill or select standard fields
        for item in classified:
            eid = item.get("element_id")
            action = item.get("action")
            val = item.get("recommended_value")

            if action == "fill" and eid not in filled_ids and val:
                return {
                    "thought": f"Filling {item.get('category')} field '{item.get('label')}'",
                    "action": "browser_fill_field",
                    "arguments": {"element_id": eid, "value": str(val)}
                }
            elif action == "select" and eid not in selected_ids and val:
                return {
                    "thought": f"Selecting option '{val}' for field '{item.get('label')}'",
                    "action": "browser_select_option",
                    "arguments": {"element_id": eid, "option": str(val)}
                }

        # Step 5.5: Fill tailored cover letter into cover letter textarea
        for item in classified:
            eid = item.get("element_id")
            cat = item.get("category")
            if cat == "COVER_LETTER" and eid not in filled_ids:
                cl_text = self._get_cover_letter_for_vacancy()
                return {
                    "thought": f"Filling tailored cover letter into field '{item.get('label')}'",
                    "action": "browser_fill_field",
                    "arguments": {"element_id": eid, "value": cl_text}
                }

        # Step 6: Handle custom questions
        for item in classified:
            eid = item.get("element_id")
            cat = item.get("category")
            if cat == "CUSTOM_TECHNICAL_QUESTION" and eid not in filled_ids:
                # Check if we already generated answer
                ans_step = next((s for s in self.scratchpad if s["tool_name"] == "candidate_answer_question" and s["arguments"].get("question") == item.get("label")), None)
                if not ans_step:
                    return {
                        "thought": f"Generating truthful evidence-grounded answer for '{item.get('label')}'",
                        "action": "candidate_answer_question",
                        "arguments": {"question": item.get("label", "Describe relevant experience")}
                    }
                else:
                    ans_text = ans_step["observation"].get("answer", "Extensive fullstack engineering background.")
                    return {
                        "thought": f"Filling generated answer into question field {eid}",
                        "action": "browser_fill_field",
                        "arguments": {"element_id": eid, "value": ans_text}
                    }

        # Step 7: Run automated form verification before asking for user approval
        # If we filled any fields or uploaded files, re-inspect to get latest live DOM state
        last_action_idx = max(
            [i for i, s in enumerate(self.scratchpad) if s["tool_name"] in ("browser_fill_field", "browser_upload_cv", "browser_select_option")]
            or [-1]
        )
        last_insp_idx = max(
            [i for i, s in enumerate(self.scratchpad) if s["tool_name"] == "browser_inspect_page"]
            or [-1]
        )
        if last_action_idx > -1 and last_insp_idx < last_action_idx:
            return {
                "thought": "Re-inspecting filled form elements to observe updated values before verification",
                "action": "browser_inspect_page",
                "arguments": {}
            }

        has_verified = any(s["tool_name"] == "candidate_verify_form" for s in self.scratchpad)
        if not has_verified:
            # Get latest interactive elements from the most recent inspect
            last_elements = []
            for s in reversed(self.scratchpad):
                if s["tool_name"] == "browser_inspect_page" and s.get("observation"):
                    obs = s["observation"].get("observation", s["observation"])
                    if isinstance(obs, dict):
                        last_elements = obs.get("interactive_elements", [])
                    break

            # If no elements were discovered or inspect failed, halt with error
            if not last_elements:
                return {
                    "thought": "No form elements found on page or page failed to load in Chrome.",
                    "action": "fail_session_with_error",
                    "arguments": {
                        "error": "Интерактивные поля формы не найдены в браузере. Убедитесь, что расширение Chrome активно и страница вакансии открыта."
                    }
                }

            return {
                "thought": "Running automated verification engine to check completeness and field validity",
                "action": "candidate_verify_form",
                "arguments": {
                    "elements": last_elements,
                    "classified_elements": classified
                }
            }

        # Step 8: Form is verified, now request human approval with verification summary
        verify_step = next((s for s in reversed(self.scratchpad) if s["tool_name"] == "candidate_verify_form"), None)
        verify_obs = verify_step.get("observation", {}) if verify_step else {}
        if isinstance(verify_obs, dict) and verify_obs.get("result"):
            verify_obs = verify_obs.get("result")

        # Anti-BS check: cannot request approval if verification failed or 0 fields were checked
        if not verify_obs.get("is_valid") or verify_obs.get("total_fields_checked", 1) == 0:
            return {
                "thought": "Form verification failed. Halting application pipeline.",
                "action": "fail_session_with_error",
                "arguments": {
                    "error": verify_obs.get("summary", "Верификация формы не пройдена.")
                }
            }

        return {
            "thought": "All application fields and requirements have been fulfilled and verified. Ready for human verification.",
            "action": "request_human_approval",
            "arguments": {
                "summary": {
                    "company": "Target Company",
                    "url": self.target_url,
                    "fields_filled": len(filled_ids),
                    "cv_uploaded": bool(uploaded_ids),
                    "steps_completed": self.step_counter,
                    "verification": verify_obs
                }
            }
        }

    def run(self) -> Dict[str, Any]:
        """
        Runs the full autonomous ReAct agent loop until completion,
        approval requirement, error, or max steps limit.
        """
        create_agent_session(self.session_id, self.vacancy_id, self.target_url, self.mode)
        update_agent_session(self.session_id, state="OBSERVING")

        self.event_bus.publish(self.session_id, "agent.started", {
            "session_id": self.session_id,
            "target_url": self.target_url,
            "mode": self.mode
        })

        profile = get_canonical_profile(lang="ru")
        cand_ctx = self._format_candidate_context(profile)
        tools_desc = self._build_tools_description()

        final_status = "COMPLETED"
        error_msg = None

        while self.step_counter < self.max_steps:
            self.step_counter += 1
            start_step_time = time.time()

            # 1. Update Planner subgoal based on execution state
            has_inspected = any(s["tool_name"] == "browser_inspect_page" for s in self.scratchpad)
            has_classified = any(s["tool_name"] == "candidate_classify_form" for s in self.scratchpad)
            has_filled = any(s["tool_name"] in ("browser_fill_field", "browser_upload_cv") for s in self.scratchpad)
            has_verified = any(s["tool_name"] == "candidate_verify_form" for s in self.scratchpad)

            if not has_inspected or not has_classified:
                self.current_subgoal = "DISCOVER_FORM"
            elif not has_filled:
                self.current_subgoal = "FILL_FIELDS"
            elif not has_verified:
                self.current_subgoal = "VERIFY_DATA"
            else:
                self.current_subgoal = "REQUEST_APPROVAL"

            # 2. Build prompt from scratchpad history
            recent_steps = self.scratchpad[-5:]
            scratchpad_text = "\n".join([
                f"Step {s['step']}: Thought: {s['thought']} | Action: {s['tool_name']}({json.dumps(s['arguments'])}) -> Result: {json.dumps(s.get('observation', {}))[:300]}"
                for s in recent_steps
            ]) if recent_steps else "None yet."

            prompt = SYSTEM_PROMPT_TEMPLATE.format(
                tools_schema=tools_desc,
                **cand_ctx
            ) + f"\n\nCURRENT GOAL: Prepare and fill application for {self.target_url}\nCURRENT SUBGOAL: {self.current_subgoal}\nSTEP NUMBER: {self.step_counter} / {self.max_steps}\nRECENT SCRATCHPAD:\n{scratchpad_text}\n\nWhat is your next thought and action?"

            # 3. Think & Decide
            update_agent_session(self.session_id, state="PLANNING")
            self.event_bus.publish(self.session_id, "agent.thinking", {"step": self.step_counter, "subgoal": self.current_subgoal})

            decision = self._call_llm_decision(prompt)
            thought = decision.get("thought", "")
            action = decision.get("action", "")
            arguments = decision.get("arguments", {})

            # Anti-stuck watchdog: detect 3 consecutive identical actions
            sig = f"{action}:{json.dumps(arguments, sort_keys=True)}"
            self._action_signatures.append(sig)
            if len(self._action_signatures) >= 3 and self._action_signatures[-1] == self._action_signatures[-2] == self._action_signatures[-3]:
                action = "ask_user_clarification"
                thought = "Anti-stuck watchdog: зафиксировано 3 одинаковых действия подряд. Запрашиваю помощь человека."
                arguments = {"question": "Агент застрял на одном шаге 3 раза подряд. Пожалуйста, проверьте страницу в Chrome."}

            # 4. Check for special terminal / approval actions
            if action == "request_human_approval":
                approval_token = str(uuid.uuid4())
                update_agent_session(self.session_id, state="WAITING_FOR_USER", approval_token=approval_token)
                record_session_step(
                    self.session_id, self.step_counter, thought, action, arguments,
                    observation={"approval_token": approval_token},
                    status="WAITING_APPROVAL",
                    duration_ms=int((time.time() - start_step_time) * 1000)
                )
                self.event_bus.publish(self.session_id, "approval.required", {
                    "session_id": self.session_id,
                    "approval_token": approval_token,
                    "summary": arguments.get("summary", {})
                })
                return {
                    "success": True,
                    "session_id": self.session_id,
                    "state": "WAITING_FOR_USER_APPROVAL",
                    "approval_token": approval_token,
                    "steps": self.step_counter,
                    "summary": arguments.get("summary", {})
                }

            if action == "ask_user_clarification":
                q_text = arguments.get("question_to_user") or arguments.get("question", "")
                self.scratchpad.append({
                    "step": self.step_counter,
                    "thought": thought,
                    "tool_name": action,
                    "arguments": arguments,
                    "observation": {"question": q_text}
                })
                update_agent_session(self.session_id, state="WAITING_FOR_USER")
                record_session_step(
                    self.session_id, self.step_counter, thought, action, arguments,
                    observation={"question": q_text},
                    status="WAITING_CLARIFICATION",
                    duration_ms=int((time.time() - start_step_time) * 1000)
                )
                self.event_bus.publish(self.session_id, "user.clarification_needed", {
                    "session_id": self.session_id,
                    "question": q_text,
                    "context": arguments.get("field_context")
                })
                return {
                    "success": True,
                    "session_id": self.session_id,
                    "state": "WAITING_FOR_USER",
                    "question": q_text
                }

            if action == "fail_session_with_error":
                err_text = arguments.get("error", "Агент остановлен из-за ошибки окружения или формы.")
                update_agent_session(self.session_id, state="ERROR", error_message=err_text)
                self.event_bus.publish(self.session_id, "agent.error", {
                    "session_id": self.session_id,
                    "error": err_text
                })
                return {
                    "success": False,
                    "session_id": self.session_id,
                    "state": "ERROR",
                    "error": err_text
                }

            # 4. Tool Execution
            update_agent_session(self.session_id, state="ACTING")
            self.event_bus.publish(self.session_id, "agent.tool.started", {
                "step": self.step_counter,
                "tool": action,
                "arguments": arguments
            })

            tool_res = ToolRegistry.execute_tool(action, arguments)
            duration_ms = int((time.time() - start_step_time) * 1000)

            # 5. Record Observation in scratchpad & database
            step_record = {
                "step": self.step_counter,
                "thought": thought,
                "tool_name": action,
                "arguments": arguments,
                "observation": tool_res.get("result") if tool_res.get("success") else tool_res,
                "status": "SUCCESS" if tool_res.get("success") else "ERROR",
                "duration_ms": duration_ms
            }
            self.scratchpad.append(step_record)

            record_session_step(
                self.session_id,
                self.step_counter,
                thought,
                action,
                arguments,
                observation=step_record["observation"],
                status=step_record["status"],
                duration_ms=duration_ms
            )

            self.event_bus.publish(self.session_id, "agent.tool.completed", {
                "step": self.step_counter,
                "tool": action,
                "success": tool_res.get("success", False),
                "result": step_record["observation"]
            })

        # Max steps exceeded without approval request
        final_status = "FAILED"
        error_msg = f"Agent exceeded maximum step limit ({self.max_steps}) without reaching verification/approval."
        update_agent_session(self.session_id, state="FAILED", error_message=error_msg)
        self.event_bus.publish(self.session_id, "agent.error", {"error": error_msg})

        return {
            "success": False,
            "session_id": self.session_id,
            "state": "FAILED",
            "error": error_msg,
            "steps": self.step_counter
        }
