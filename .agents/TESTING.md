# TESTING STRATEGY

Testing is part of implementation.

---

# Backend

Test:

- routes
- validation
- database operations
- error handling
- AI integration boundaries
- parsing

---

# Frontend

Test:

- API handling
- state
- rendering
- tabs
- modals
- null values
- empty states
- errors

---

# AI

Test:

- valid JSON
- malformed JSON
- missing fields
- invalid values
- empty output
- API errors

---

# Parser

Test:

- valid PDF
- valid DOCX
- empty document
- corrupted document
- unsupported format

---

# Playwright

Test:

- browser startup
- navigation
- selectors
- form filling
- timeout
- failed submission
- successful submission

---

# Regression

After significant changes verify:

1. application starts
2. frontend loads
3. API works
4. database works
5. existing features work
6. console has no unexpected errors