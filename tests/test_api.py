import os
import io
import json
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

SAMPLE = """
CONFIDENTIALITY: The receiving party shall keep all Confidential Information secret for a period of five (5) years.
LIABILITY: The signer shall be liable without limitation for any damages arising from the services.
PAYMENT TERMS: Payment is due within ninety (90) days of invoice.
""".strip()

def test_analyze_text_upload():
    payload = {
        "strict_mode": "true",
        "jurisdiction": "General",
        "top_k_precedents": 0,
    }
    files = {"file": ("sample.txt", SAMPLE.encode("utf-8"), "text/plain")}
    r = client.post("/analyze", params=payload, files=files)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "clauses" in data and len(data["clauses"]) > 0
