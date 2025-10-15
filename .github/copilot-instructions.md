# Copilot instructions for DriftForce (driftforce-api)

This file contains concise, actionable guidance to help an AI coding agent be productive in this repository.

Key facts
- Primary app: `app.py` — a FastAPI service that implements hallucination/drift detection.
- DB: `driftforce.db` (SQLite) created on startup by `init_db()`; tables: `accounts(api_key,email,created_at)` and `events(id,api_key,drift_detected,drift_score,issues,created_at)`.
- Demo key: `df_demo_key_123` is inserted at startup and is treated as a non-persistent/demo account (events are not stored for it).
- Dev deps: `requirements.txt` (FastAPI, uvicorn, pydantic). See that file for pinned versions.

Run & debug
- Start locally (either will work):

```zsh
# Option A: run the included runner
python app.py

# Option B: run Uvicorn directly (auto-reload helpful during edits)
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

- Interactive docs are available at: `http://localhost:8000/docs` (the app prints this on startup).
- Test harness: `test.py` demonstrates calling `/v1/check` with the demo key and can be used as a quick smoke test.

API surface and important behaviors
- Public endpoints to focus on in edits and tests:
  - `GET /` — root status + demo key
  - `GET /health` — quick SQLite connectivity check
  - `POST /v1/check` — main detection endpoint (requires API key via `Authorization` header or falls back to demo key). Returns the `CheckResponse` Pydantic model.
  - `POST /v1/demo` — demo endpoint (no auth, never writes to DB)
  - `POST /v1/register` — creates a `df_live_...` API key and stores it in `accounts`
  - `GET /v1/metrics` — usage metrics; requires API key and queries `events` over the last 24 hours

Auth conventions (important)
- Header formats accepted: `Authorization: Bearer <key>`, `Authorization: bearer <key>`, or a bare API key string in the header. If no header is provided the server uses the demo key for Swagger/testing.
- Demo key bypass: when `api_key == 'df_demo_key_123'` the app will not persist events (deliberate to avoid DB bloat). When writing features that record events, respect this guard.

Detection logic and patterns (use when extending rules)
- Core detector: `detect_hallucination(prompt, response)` in `app.py`.
- Current checks (weights and behavior are implemented in code):
  - AI self-reference detection (regexes like `as an AI`, `I am an AI`, `language model`) — adds ~0.35 to score and creates an `ai_disclosure` issue.
  - Fake/new URL detection — looks for URLs in the response not present in the prompt; first new URL reported, critical severity, ~0.4 score.
  - Unsourced statistics detection (percentages or "X out of Y") — medium severity, ~0.25 score.
- Final decision: `drift_detected` is set when `drift_score >= 0.3` (see `return` in the detector).

Storage & telemetry notes
- Schema is explicit in `init_db()`. New live keys are of the form `df_live_<token>`.
- Events are persisted to `events` only for non-demo keys; ensure migrations or schema changes preserve this behavior unless intentionally changing it.

Patterns & conventions observed
- Simplicity: single-file FastAPI app (no separate service layers). Prefer minimal, well-scoped edits to `app.py` and add new modules when logic grows.
- Use Pydantic models for request/response types (`CheckRequest`, `CheckResponse`) — extend these when adding endpoints or fields.
- Time handling uses `datetime.utcnow().isoformat()` and SQLite `datetime(...)` queries; be cautious of timezone assumptions when changing metrics logic.
- CORS is permissive (`allow_origins=['*']`) for browser testing — tighten only if changing public hosting behavior.

Files to reference for examples
- `app.py` — primary implementation and examples of patterns to follow (auth parsing, DB init, detection rules).
- `test.py` — concrete example of how to call the API and assert basic behavior.
- `requirements.txt` — dependency versions to use when adding packages.
- `customers.txt` — business notes (payment link, API key template) — useful when implementing billing/registration workflows.

What NOT to change without human sign-off
- The demo-key behavior (non-persistent) and the database schema for `accounts`/`events` as they are relied on by the demo and metrics endpoints.
- The scoring threshold (`0.3`) without experimental validation — it's used to toggle `drift_detected`.

Quick examples
- Example header accepted by `/v1/check` (from `test.py`): `Authorization: Bearer df_demo_key_123`
- The app prints the demo key and local docs URL at startup; use these to speed up manual testing.

If anything in this guidance is unclear or you want adjustments (more examples, stricter linting/format suggestions, or adding test templates), tell me which parts to expand and I will iterate.

Demo usage (what it does and how to run)
- Purpose: the demo is a lightweight, deterministic hallucination/drift detector. It runs simple regex-based checks on an LLM response to flag:
  - AI self-reference ("as an AI", "I am an AI") — high severity
  - New/fake URLs introduced in the response that don't appear in the prompt — critical
  - Unsourced statistics (percentages or "X out of Y") — medium

- Quick run (local):

```zsh
# Start the server (background or in a separate terminal)
python app.py

# Example: curl against the demo endpoint (no auth required)
curl -X POST http://localhost:8000/v1/demo \
  -H "Content-Type: application/json" \
  -d '{"prompt":"How do I cancel?","response":"As an AI model, visit https://fake.com — 97% success"}'
```

- Example (Python requests):

```python
import requests

data = {"prompt": "What's the refund policy?",
        "response": "As an AI, see https://fake.com — 97% success"}

r = requests.post('http://localhost:8000/v1/demo', json=data)
print(r.json())
```

- How the demo helps: it provides an explainable, fast first-pass filter to catch common hallucination patterns. Use it in dev or CI to flag suspicious responses before human review or automated publishing.

