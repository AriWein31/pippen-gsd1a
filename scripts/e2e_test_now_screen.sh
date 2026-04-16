#!/bin/bash
# End-to-end test for the Now screen API endpoint.
# Verifies that GET /patients/{id}/now returns all required sections.

set -e

PATIENT_ID="00000000-0000-0000-0000-000000000001"
BACKEND_URL="http://localhost:8000"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓ PASS${NC}: $1"; }
fail() { echo -e "${RED✗ FAIL${NC}: $1"; exit 1; }
info() { echo -e "${YELLOW}INFO${NC}: $1"; }

echo ""
echo "=== Pippen Now Screen E2E Test ==="
echo ""

# Check health
info "Checking backend health..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health")
if [ "$HEALTH_STATUS" = "200" ]; then
    pass "Backend is healthy (HTTP $HEALTH_STATUS)"
else
    fail "Backend health check failed (HTTP $HEALTH_STATUS)"
fi

# Call /now endpoint
info "Calling GET /patients/$PATIENT_ID/now..."
RESPONSE=$(curl -s -w "\n__HTTP_STATUS__:%{http_code}" "$BACKEND_URL/patients/$PATIENT_ID/now")
HTTP_STATUS=$(echo "$RESPONSE" | grep -o "__HTTP_STATUS__:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/__HTTP_STATUS__/d')

if [ "$HTTP_STATUS" != "200" ]; then
    fail "/now endpoint returned HTTP $HTTP_STATUS (expected 200)"
else
    pass "/now endpoint returned HTTP 200"
fi

# Validate JSON
info "Validating JSON response..."
echo "$BODY" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null || fail "Response is not valid JSON"

# Check required top-level keys
info "Checking required sections..."
for key in "patient_id" "generated_at" "recommendations" "changes" "risk" "brief" "active_alerts"; do
    if echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); exit(0 if '$key' in d else 1)" 2>/dev/null; then
        pass "Response contains '$key'"
    else
        fail "Response missing '$key'"
    fi
done

# Check recommendations is a list
info "Checking recommendations is a list..."
if echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); assert isinstance(d['recommendations'], list)" 2>/dev/null; then
    pass "recommendations is a list"
else
    fail "recommendations is not a list"
fi

# Check changes is a list
info "Checking changes is a list..."
if echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); assert isinstance(d['changes'], list)" 2>/dev/null; then
    pass "changes is a list"
else
    fail "changes is not a list"
fi

# Check risk has required fields
info "Checking risk object structure..."
for field in "patient_id" "risk_score" "risk_level" "confidence" "generated_at"; do
    if echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); exit(0 if '$field' in d['risk'] else 1)" 2>/dev/null; then
        pass "risk has '$field'"
    else
        fail "risk missing '$field'"
    fi
done

# Check brief has required fields
info "Checking brief object structure..."
for field in "brief_date" "patient_id" "summary"; do
    if echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); exit(0 if '$field' in d['brief'] else 1)" 2>/dev/null; then
        pass "brief has '$field'"
    else
        fail "brief missing '$field'"
    fi
done

# Check active_alerts is a list
info "Checking active_alerts is a list..."
if echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); assert isinstance(d['active_alerts'], list)" 2>/dev/null; then
    pass "active_alerts is a list"
else
    fail "active_alerts is not a list"
fi

echo ""
info "All checks passed. Now screen is functional."
echo ""
