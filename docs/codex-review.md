---
name: codex-review
description: Reviewer workflow for Codex agents to audit builder outputs using the Multi-Agent Build-Review Framework in this repo.
---

# Codex Review Skill

Use this skill when acting as the **Reviewer** in the Multi-Agent Build-Review Framework (see `docs/Multi-Agent Build-Review Framework.md`). It defines how to load context, what to inspect, and how to report findings.

## When to Use
- You are assigned the Reviewer role and need to audit recent builder changes.
- You must generate `review.json` per the framework and provide actionable feedback.

## Quickstart Checklist
1) Load repo state: skim `git status` and `git diff` to see pending changes.
2) Read framework contract: `docs/Multi-Agent Build-Review Framework.md` (focus on Reviewer Contract and Output Schema).
3) Collect signals: test results (`test_results.log` if present), CI logs, and any coverage notes.
4) Review changes: security, correctness, performance, data integrity, and API contracts.
5) Emit output: write `review.json` matching the schema; include severity and suggestions.

## Required Outputs
- **review.json** (strict schema):
  ```json
  {
    "status": "FAIL or PASS",
    "reviewer": "your-agent-name",
    "issues": [
      {
        "file": "path/relative/to/repo",
        "line": 0,
        "severity": "low|medium|high|critical",
        "category": "security|correctness|performance|style|docs|tests|maintainability",
        "description": "What is wrong and why it matters",
        "suggestion": "Specific, actionable fix"
      }
    ]
  }
  ```
- If no issues: set `status` to `PASS` and leave `issues` empty.

## Review Scope & Priorities
- **Security & auth**: token handling, PII, secrets, RBAC checks, SQL safety.
- **Data integrity**: migrations vs. models, schema defaults, backward compatibility.
- **API contracts**: request/response schemas, validation, status codes, i18n keys.
- **Tests**: coverage for new logic and edge cases; avoid external dependencies in unit tests.
- **Performance**: avoid N+1 queries, unnecessary network calls, and heavy per-request work.
- **Docs & UX**: updated README/usage if behavior changes; UI screenshots/GIFs when relevant.

## Reviewer Workflow
1) **Identify scope**: read `git diff --stat` to map touched areas; open files as needed.
2) **Cross-check migrations**: ensure Alembic scripts align with SQLAlchemy models and default values; verify downgrade safety if required.
3) **Run or read tests**: if tests were run, read `test_results.log`; otherwise, run `pixi run pytest` (or targeted tests) and capture results.
4) **API & schema checks**: compare router changes to `src/schemas/` and OpenAPI expectations; verify HTTP status codes and error handling.
5) **Security pass**: inspect `src/core/security.py`, auth routes, and data access for RBAC/permission checks and secret management.
6) **Summarize findings**: populate `review.json` with clear, ranked issues; prefer grouped issues over many nitpicks.

## Tips
- Keep context small: only open files touched in the diff or referenced by errors.
- Use `ruff` and `mypy` outputs if available; cite line numbers from diff when possible.
- If tests are failing, include the failing command and top stack trace line in `suggestion`.
- If the builder provided `review.json` already, update it instead of overwriting unless corrupt.

## Installation
This is a user-space skill. To install into Codex, copy `docs/codex-review.md` to `$CODEX_HOME/skills/codex-review/SKILL.md` (create directories if missing):
```bash
mkdir -p "$CODEX_HOME/skills/codex-review" \
  && cp docs/codex-review.md "$CODEX_HOME/skills/codex-review/SKILL.md"
```
