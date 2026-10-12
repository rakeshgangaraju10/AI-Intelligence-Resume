#!/usr/bin/env bash
# End-to-end smoke test of the Stage 1 API against a running server.
#   Usage: scripts/smoke_test_api.sh path/to/resume.pdf [base_url]
# Requires: curl, python3 (for JSON pretty-printing). Uses a throwaway account.
set -euo pipefail

PDF="${1:?usage: $0 path/to/resume.pdf [base_url]}"
BASE="${2:-http://localhost:8000/api/v1}"
JAR="$(mktemp)"
trap 'rm -f "$JAR"' EXIT
EMAIL="smoke-$(date +%s)@example.com"
PASSWORD="Smoke-Test-Pass-2026"

csrf() { awk '$6 == "csrftoken" {print $7}' "$JAR" | tail -1; }
pretty() { python3 -m json.tool; }

echo "== health";   curl -sf "$BASE/health/" | pretty
echo "== csrf";     curl -sf -c "$JAR" -b "$JAR" "$BASE/auth/csrf/" -o /dev/null && echo "cookie set"

echo "== register $EMAIL"
curl -sf -c "$JAR" -b "$JAR" -H "X-CSRFToken: $(csrf)" -H "Content-Type: application/json" \
  -d "{\"full_name\":\"Smoke Test\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  "$BASE/auth/register/" | pretty

echo "== upload $PDF"
RESUME_JSON="$(curl -s -c "$JAR" -b "$JAR" -H "X-CSRFToken: $(csrf)" \
  -F "file=@${PDF};type=application/pdf" -F "title=Smoke test resume" "$BASE/resumes/")"
echo "$RESUME_JSON" | python3 -c 'import json,sys; d=json.load(sys.stdin); d["extracted_text"]=d.get("extracted_text","")[:200]+"..."; print(json.dumps(d, indent=2))'
RESUME_ID="$(echo "$RESUME_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

echo "== list";     curl -sf -b "$JAR" "$BASE/resumes/" | pretty
echo "== delete";   curl -sf -o /dev/null -w "HTTP %{http_code}\n" -X DELETE -b "$JAR" -H "X-CSRFToken: $(csrf)" "$BASE/resumes/$RESUME_ID/"
echo "== get after delete (expect 404)"
curl -s -o /dev/null -w "HTTP %{http_code}\n" -b "$JAR" "$BASE/resumes/$RESUME_ID/"
