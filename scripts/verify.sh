#!/usr/bin/env bash
# One-shot verification: backend tests, frontend build check, HTTP smoke tests.
# Exits 0 only when every stage passes.
set -u

API_URL="${API_URL:-http://api:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://frontend:80}"
FAIL=0

stage() {
  echo ""
  echo "==================== $1 ===================="
}

# 1) Backend code tests ------------------------------------------------------
stage "1/3 后端代码测试 (pytest)"
cd /verify/backend
/opt/venv/bin/python -m pytest -q
if [ $? -ne 0 ]; then
  echo "!! 后端测试失败"
  FAIL=1
else
  echo ">> 后端测试通过"
fi

# 2) Frontend build check (tsc + vite) ---------------------------------------
stage "2/3 前端构建检查 (tsc + vite build)"
cd /verify/frontend
npm run build
if [ $? -ne 0 ]; then
  echo "!! 前端构建失败"
  FAIL=1
else
  echo ">> 前端构建通过"
fi

# 3) HTTP smoke ---------------------------------------------------------------
stage "3/3 HTTP 冒烟测试"
wait_http() {
  # $1 url, $2 label, $3 expected-substring (optional)
  local url="$1" label="$2" want="${3:-}" i body
  for i in $(seq 1 30); do
    body="$(curl -fsS --max-time 5 "$url" 2>/dev/null)" && {
      if [ -z "$want" ] || printf '%s' "$body" | grep -q "$want"; then
        echo ">> $label OK ($url)"
        return 0
      fi
    }
    sleep 2
  done
  echo "!! $label 不可用或内容不符: $url"
  return 1
}

wait_http "$API_URL/health" "API 健康检查" '"ok"' || FAIL=1
wait_http "$FRONTEND_URL/" "前端页面" "root" || FAIL=1

echo ">> 调用 POST /api/adjudicate 冒烟"
SMOKE_BODY="$(cat <<'JSON'
{
  "streamA": [
    {"time": 100, "code": "TRIG"},
    {"time": 250, "code": "BEAM"},
    {"time": 755, "code": "BEAM"}
  ],
  "streamB": [
    {"time": 100, "code": "TRIG"},
    {"time": 250, "code": "BEAM"},
    {"time": 750, "code": "BEAM"}
  ],
  "minOffset": -10,
  "maxOffset": 10,
  "jump": 5,
  "minHits": 2
}
JSON
)"
RESP="$(curl -fsS --max-time 5 -X POST "$API_URL/api/adjudicate" \
  -H 'Content-Type: application/json' -d "$SMOKE_BODY")"
if [ $? -ne 0 ]; then
  echo "!! 裁决接口调用失败"
  FAIL=1
else
  echo "$RESP"
  printf '%s' "$RESP" | grep -q '"feasible":true' \
    && printf '%s' "$RESP" | grep -q '"matchCount":3' \
    || { echo "!! 裁决返回不符合预期"; FAIL=1; }
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "VERIFY RESULT: PASS"
  exit 0
fi
echo "VERIFY RESULT: FAIL"
exit 1
