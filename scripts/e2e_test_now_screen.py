#!/usr/bin/env python3
"""
End-to-end test for the Pippen Now screen API.
Verifies GET /patients/{id}/now returns all required sections.
"""
import sys
import urllib.request
import json

PATIENT_ID = "00000000-0000-0000-0000-000000000001"
BASE_URL = "http://localhost:8000"

PASS = 0
FAIL = 0


def p(msg):
    print(f"[INFO]  {msg}")


def ok(msg):
    global PASS
    PASS += 1
    print(f"[PASS]  {msg}")


def fail(msg):
    global FAIL
    FAIL += 1
    print(f"[FAIL]  {msg}")


def main():
    global PASS, FAIL

    print()
    print("=== Pippen Now Screen E2E Test ===")
    print()

    # Health check
    p("Checking backend health...")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health") as r:
            status = r.status
    except Exception as e:
        fail(f"Backend unreachable: {e}")
        sys.exit(1)

    if status == 200:
        ok(f"Backend healthy (HTTP {status})")
    else:
        fail(f"Backend unhealthy (HTTP {status})")

    # GET /patients/{id}/now
    p(f"Calling GET /patients/{PATIENT_ID}/now...")
    try:
        req = urllib.request.Request(f"{BASE_URL}/patients/{PATIENT_ID}/now")
        with urllib.request.urlopen(req) as r:
            body = r.read().decode("utf-8")
            http_status = r.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        http_status = e.code
    except Exception as e:
        fail(f"Request failed: {e}")
        sys.exit(1)

    if http_status == 200:
        ok(f"/now returned HTTP 200")
    else:
        fail(f"/now returned HTTP {http_status} (expected 200)")
        print(f"  Response: {body[:200]}")
        sys.exit(1)

    # Parse JSON
    p("Validating JSON response...")
    try:
        data = json.loads(body)
        ok("Response is valid JSON")
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON: {e}")
        sys.exit(1)

    # Check required top-level keys
    p("Checking required sections...")
    required = ["patient_id", "generated_at", "recommendations", "changes", "risk", "brief", "active_alerts"]
    for key in required:
        if key in data:
            ok(f"Response contains '{key}'")
        else:
            fail(f"Response missing '{key}'")

    # Check recommendations is a list
    p("Checking recommendations type...")
    if isinstance(data.get("recommendations"), list):
        ok("recommendations is a list")
        if len(data["recommendations"]) > 0:
            rec = data["recommendations"][0]
            rec_fields = ["id", "priority", "headline", "explanation", "suggested_action", "confidence"]
            for f in rec_fields:
                if f in rec:
                    ok(f"  recommendation[0] has '{f}'")
                else:
                    fail(f"  recommendation[0] missing '{f}'")
    else:
        fail("recommendations is not a list")

    # Check changes is a list
    p("Checking changes type...")
    if isinstance(data.get("changes"), list):
        ok("changes is a list")
    else:
        fail("changes is not a list")

    # Check risk fields
    p("Checking risk object structure...")
    risk_fields = ["patient_id", "risk_score", "risk_level", "confidence", "generated_at"]
    risk = data.get("risk", {})
    for f in risk_fields:
        if f in risk:
            ok(f"  risk has '{f}'")
        else:
            fail(f"  risk missing '{f}'")

    # Check brief fields
    p("Checking brief object structure...")
    brief_fields = ["brief_date", "patient_id", "summary"]
    brief = data.get("brief", {})
    for f in brief_fields:
        if f in brief:
            ok(f"  brief has '{f}'")
        else:
            fail(f"  brief missing '{f}'")

    # Check active_alerts is a list
    p("Checking active_alerts type...")
    if isinstance(data.get("active_alerts"), list):
        ok("active_alerts is a list")
    else:
        fail("active_alerts is not a list")

    # Summary
    print()
    print("=== Results ===")
    print(f"Passed: {PASS}")
    print(f"Failed: {FAIL}")
    print()

    if FAIL > 0:
        print("E2E test FAILED")
        sys.exit(1)
    else:
        print("E2E test PASSED — Now screen is functional")
        # Print a sample of what we got
        print()
        p("Sample response summary:")
        print(f"  Recommendations: {len(data.get('recommendations', []))}")
        print(f"  Changes:        {len(data.get('changes', []))}")
        print(f"  Risk score:     {data.get('risk', {}).get('risk_score', 'N/A')}")
        print(f"  Brief summary:  {data.get('brief', {}).get('summary', 'N/A')[:60]}...")
        sys.exit(0)


if __name__ == "__main__":
    main()
