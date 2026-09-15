# Operational Rules for Gemini Agent

1. **Token Economy**:
   - Never re-read dependencies (`node_modules`, build artifacts, lockfiles).
   - Use AST/grep searches instead of full-file reads whenever possible.
   - Do not echo back full files if only one function changed.

2. **Zero Placeholders**:
   - Writing `// TODO`, `/* implementation */`, or omitting logic is treated as a runtime failure.
   - If context is missing to write full logic, halt and ask a direct clarifying question before outputting code.

3. **Deterministic Implementation**:
   - Write concrete, executable code with explicit error branches.
   - Prefer pure functions and typed boundaries.