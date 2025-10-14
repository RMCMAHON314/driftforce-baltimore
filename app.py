from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import sqlite3
import json
import re
import uuid
from datetime import datetime
import secrets
import uvicorn

app = FastAPI(title="DriftForce", version="1.0.0")

# Add CORS support for browser-based testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class CheckRequest(BaseModel):
    prompt: str
    response: str
    context: Optional[Dict[str, Any]] = {}

class CheckResponse(BaseModel):
    drift_detected: bool
    drift_score: float
    issues: List[Dict[str, str]]
    analysis_id: str

def init_db():
    conn = sqlite3.connect('driftforce.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS accounts 
                 (api_key TEXT PRIMARY KEY, email TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS events 
                 (id TEXT PRIMARY KEY, api_key TEXT, drift_detected INTEGER, 
                  drift_score REAL, issues TEXT, created_at TEXT)''')
    
    # Always ensure demo key exists
    c.execute("INSERT OR REPLACE INTO accounts VALUES (?, ?, ?)",
              ("df_demo_key_123", "demo@driftforce.ai", datetime.utcnow().isoformat()))
    
    conn.commit()
    conn.close()

def detect_hallucination(prompt: str, response: str) -> Dict:
    score = 0.0
    issues = []
    
    # Check for AI disclosure
    ai_patterns = [
        r"as an AI",
        r"I'm an AI",
        r"I am an AI",
        r"language model",
        r"I cannot browse",
        r"I don't have access to"
    ]
    
    for pattern in ai_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            score += 0.35
            issues.append({
                "type": "ai_disclosure",
                "severity": "high",
                "detail": "AI self-reference detected"
            })
            break
    
    # Check for fake URLs
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    response_urls = set(re.findall(url_pattern, response))
    prompt_urls = set(re.findall(url_pattern, prompt))
    
    # Clean URLs
    response_urls = {url.rstrip('.,;:!?') for url in response_urls}
    prompt_urls = {url.rstrip('.,;:!?') for url in prompt_urls}
    
    new_urls = response_urls - prompt_urls
    if new_urls:
        score += 0.4
        for url in list(new_urls)[:1]:  # Only report first fake URL
            issues.append({
                "type": "fake_url",
                "severity": "critical",
                "detail": f"URL not in prompt: {url}"
            })
    
    # Check for unsourced statistics
    stat_patterns = [r'\b\d+(?:\.\d+)?%', r'\b\d+\s*(?:out of|of)\s*\d+']
    
    for pattern in stat_patterns:
        response_stats = re.findall(pattern, response, re.IGNORECASE)
        prompt_stats = re.findall(pattern, prompt, re.IGNORECASE)
        
        if response_stats and not prompt_stats:
            score += 0.25
            issues.append({
                "type": "unsourced_stat",
                "severity": "medium",
                "detail": "Unverifiable statistic"
            })
            break
    
    return {
        "drift_detected": score >= 0.3,
        "drift_score": min(score, 1.0),
        "issues": issues
    }

@app.on_event("startup")
async def startup():
    init_db()
    print("\n✅ Database initialized with demo key")
    print("🔑 Demo API key: df_demo_key_123")
    print("📚 Interactive docs: http://localhost:8000/docs")
    print("🌐 Live API: https://driftforce-api.onrender.com\n")

@app.get("/")
def root():
    return {
        "message": "DriftForce API - Detect LLM Hallucinations",
        "docs": "https://driftforce-api.onrender.com/docs",
        "demo_key": "df_demo_key_123"
    }

@app.get("/health")
def health_check():
    try:
        conn = sqlite3.connect('driftforce.db')
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "healthy", "api": "running"}
    except:
        return {"status": "unhealthy"}

@app.post("/v1/check", response_model=CheckResponse)
def check(request: CheckRequest, authorization: Optional[str] = Header(None)):
    """Check for hallucination in LLM response"""
    
    # Flexible authorization handling for Swagger compatibility
    api_key = None
    
    if authorization:
        auth = authorization.strip()
        # Handle different authorization formats
        if auth.startswith("Bearer "):
            api_key = auth[7:].strip()  # Remove "Bearer " prefix
        elif auth.startswith("bearer "):
            api_key = auth[7:].strip()  # Handle lowercase
        else:
            api_key = auth  # Use as-is
    
    # Default to demo key if not provided (for Swagger testing)
    if not api_key:
        api_key = "df_demo_key_123"
    
    # Validate API key exists
    conn = sqlite3.connect('driftforce.db')
    c = conn.cursor()
    c.execute("SELECT email FROM accounts WHERE api_key = ?", (api_key,))
    account = c.fetchone()
    
    if not account:
        conn.close()
        raise HTTPException(401, f"Invalid API key: {api_key}")
    
    conn.close()
    
    # Run detection
    analysis = detect_hallucination(request.prompt, request.response)
    analysis_id = str(uuid.uuid4())
    
    # Store event (skip for demo to avoid database bloat)
    if api_key != "df_demo_key_123":
        conn = sqlite3.connect('driftforce.db')
        c = conn.cursor()
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

@app.post("/v1/demo")
def demo_check(request: CheckRequest):
    """Demo endpoint - no auth required for testing"""
    analysis = detect_hallucination(request.prompt, request.response)
    
    return {
        "drift_detected": analysis["drift_detected"],
        "drift_score": analysis["drift_score"],
        "issues": analysis["issues"],
        "analysis_id": str(uuid.uuid4()),
        "note": "Demo endpoint - Get API key at https://buy.stripe.com/5kQ3cu5SHbdd59t2SR9MY00"
    }

@app.post("/v1/register")
def register(email: str):
    """Register for an API key"""
    if not email or "@" not in email:
        raise HTTPException(400, "Valid email required")
    
    api_key = f"df_live_{secrets.token_urlsafe(24)}"
    
    conn = sqlite3.connect('driftforce.db')
    c = conn.cursor()
    
    try:
        c.execute("INSERT INTO accounts VALUES (?, ?, ?)",
                  (api_key, email, datetime.utcnow().isoformat()))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(400, "Email already registered")
    finally:
        conn.close()
    
    return {
        "api_key": api_key,
        "email": email,
        "payment_link": "https://buy.stripe.com/5kQ3cu5SHbdd59t2SR9MY00"
    }

@app.get("/v1/metrics")
def get_metrics(authorization: Optional[str] = Header(None)):
    """Get usage metrics"""
    
    # Handle authorization
    api_key = None
    
    if authorization:
        auth = authorization.strip()
        if auth.startswith("Bearer "):
            api_key = auth[7:].strip()
        elif auth.startswith("bearer "):
            api_key = auth[7:].strip()
        else:
            api_key = auth
    
    if not api_key:
        api_key = "df_demo_key_123"
    
    conn = sqlite3.connect('driftforce.db')
    c = conn.cursor()
    
    # Check if API key exists
    c.execute("SELECT 1 FROM accounts WHERE api_key = ?", (api_key,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(401, "Invalid API key")
    
    # Get metrics for this API key
    c.execute("""
        SELECT 
            COUNT(*) as total_checks,
            SUM(drift_detected) as drift_events,
            AVG(drift_score) as avg_score,
            MAX(drift_score) as max_score
        FROM events 
        WHERE api_key = ?
        AND datetime(created_at) > datetime('now', '-24 hours')
    """, (api_key,))
    
    row = c.fetchone()
    conn.close()
    
    if row:
        total = row[0] or 0
        drifted = row[1] or 0
        avg_score = row[2] or 0
        max_score = row[3] or 0
        
        return {
            "period": "24h",
            "total_checks": total,
            "drift_events": drifted,
            "drift_rate": round((drifted / total * 100), 1) if total > 0 else 0,
            "avg_drift_score": round(avg_score, 3),
            "max_drift_score": round(max_score, 3)
        }
    
    return {"period": "24h", "total_checks": 0}

if __name__ == "__main__":
    print("🚀 Starting DriftForce API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)