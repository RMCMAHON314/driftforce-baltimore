DriftForce API (local)

Small demo/service for first-pass hallucination/drift detection. Includes a tiny FastAPI app, a demo HTML page, and tests.

Quick start

1. Install Python deps (use a venv):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the API server:

```bash
python app.py
# or
 # uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

3. Open interactive docs: http://localhost:8000/docs

Demo page

- `index.html` contains a live demo widget that POSTs to `/v1/demo` (no auth) or `/v1/check` (requires API key). The UI reads a meta tag `driftforce-api-base` if set, so you can serve the page from a static host and target a different API origin.
- Demo key (non-persistent): `df_demo_key_123` — used for testing and intentionally does not persist events.

Testing

```bash
pytest -q
python smoke_ui.py
```

Notes

- The demo and API are intentionally lightweight. When promoting to production:
  - Replace the demo key and enforce stricter CORS
  - Add auth, rate-limiting, and logging
  - Harden CSP and other headers for the hosted UI
