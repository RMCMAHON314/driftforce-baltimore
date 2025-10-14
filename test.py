import requests
import json

print("🧪 Testing DriftForce API...")

try:
    r = requests.get("http://localhost:8000/")
    print("✅ Server is running!")
except:
    print("❌ Server not running. Start it first!")
    exit()

headers = {"Authorization": "Bearer df_demo_key_123"}
data = {
    "prompt": "What is your refund policy?",
    "response": "As an AI model, visit https://fake.com for our 97% success rate"
}

r = requests.post("http://localhost:8000/v1/check", 
                  json=data, headers=headers)

result = r.json()
print(f"\n🎯 Hallucination detected: {result['drift_detected']}")
print(f"📊 Drift score: {result['drift_score']}")

print("\n✅ MVP is working!")