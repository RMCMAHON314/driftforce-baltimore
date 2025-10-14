from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict, List
import sqlite3
import json
import re
import uuid
from datetime import datetime
import secrets
import uvicorn

app = FastAPI(title="DriftForce", version="1.0.0")

class CheckRequest(BaseModel):
    prompt: str
    response: str
    context: Optional[Dict] = {}

class CheckResponse(BaseModel):
    drift_detected: bool
    drift_score: float
    issues: List[Dict]
    analysis_id: str

def init_db():
    conn = sqlite3.connect('driftforce.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS accounts 
                 (api_key TEXT PRIMARY KEY, email TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS events 
                 (id TEXT PRIMARY KEY, api_key TEXT, drift_detected INTEGER, 
                  drift_score REAL, issues TEXT, created_at TEXT)''')
    c.execute("INSERT OR IGNORE INTO accounts VALUES (?, ?, ?)",
              ("df_demo_key_123", "demo@driftforce.ai", datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def detect_hallucination(prompt: str, response: str) -> Dict:
    score = 0.0
    issues = []
    
    if re.search(r"as an AI|I'm an AI|language model", response, re.IGNORECASE):
        score += 0.35
        issues.append({"type": "ai_disclosure", "severity": "high", "detail": "AI self-reference"})
    
    response_urls = set(re.findall(r'https?://[^\s]+', response))
    prompt_urls = set(re.findall(r'https?://[^\s]+', prompt))
    new_urls = response_urls - prompt_urls
    if new_urls:
        score += 0.4
        issues.append({"type": "fake_url", "severity": "critical", "detail": f"URL: {list(new_urls)[0]}"})
    
    if re.search(r'\d+%', response) and not re.search(r'\d+%', prompt):
        score += 0.25
        issues.append({"type": "unsourced_stat", "severity": "medium", "detail": "Percentage claim"})
    
    return {
        "drift_detected": score >= 0.3,
        "drift_score": min(score, 1.0),
        "issues": issues
    }

@app.on_event("startup")
async def startup():
    init_db()
    print("\n✅ Database initialized")
    print("🔑 Demo API key: df_demo_key_123")
    print("📚 Docs at: http://localhost:8000/docs\n")

@app.get("/")
def root():
    return {"message": "DriftForce API - Working!"}

@app.post("/v1/check", response_model=CheckResponse)
def check(request: CheckRequest, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing API key")
    
    api_key = authorization.replace("Bearer ", "").strip()
    
    conn = sqlite3.connect('driftforce.db')
    c = conn.cursor()
    c.execute("SELECT * FROM accounts WHERE api_key = ?", (api_key,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(401, "Invalid API key")
    
    analysis = detect_hallucination(request.prompt, request.response)
    analysis_id = str(uuid.uuid4())
    
    c.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
              (analysis_id, api_key, int(analysis["drift_detected"]), 
               analysis["drift_score"], json.dumps(analysis["issues"]), 
               datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    
    return CheckResponse(
        drift_detected=analysis["drift_detected"],
        drift_score=analysis["drift_score"],
        issues=analysis["issues"],
        analysis_id=analysis_id
    )

if __name__ == "__main__":
    print("🚀 Starting DriftForce API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)