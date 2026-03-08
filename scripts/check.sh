#!/bin/bash
# ================================================================
# cocoro-core — 動作確認スクリプト
# サーバー上（Docker内）で実行してください
#
# 使い方:
#   chmod +x scripts/check.sh
#   ./scripts/check.sh
#   ./scripts/check.sh --host http://localhost:8001  # Nginx経由
#   ./scripts/check.sh --host http://localhost:8000  # 直接
# ================================================================

set -euo pipefail

# --- 設定 ---
HOST="${1:-http://localhost:8001}"
API_KEY="${COCORO_API_KEY:-cocoro-dev-2026}"
AUTH="Authorization: Bearer ${API_KEY}"
SESSION_ID="check-$(date +%s)"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

OK="${GREEN}[OK]${NC}"
NG="${RED}[NG]${NC}"
INFO="${CYAN}[--]${NC}"

pass=0
fail=0

check() {
  local label="$1"
  local result="$2"
  local expected="$3"
  if echo "$result" | grep -q "$expected"; then
    echo -e "${OK} $label"
    ((pass++))
  else
    echo -e "${NG} $label"
    echo "  expected: $expected"
    echo "  got:      $(echo "$result" | head -c 200)"
    ((fail++))
  fi
}

echo ""
echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN} cocoro-core 動作確認スクリプト${NC}"
echo -e "${CYAN} Host: ${HOST}${NC}"
echo -e "${CYAN}================================================================${NC}"
echo ""

# ================================================================
# ① LLM接続確認
# ================================================================
echo -e "${YELLOW}■ ① LLM接続確認${NC}"

r=$(curl -sf "${HOST}/health" || echo '{"error":"connection_failed"}')
check "GET /health - 接続OK" "$r" '"status":"ok"'
check "GET /health - LLM healthy" "$r" '"healthy":true'
echo "  LLM状態: $(echo "$r" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('llm',{})))" 2>/dev/null || echo "$r")"
echo ""

# ================================================================
# ② /chat 動作確認
# ================================================================
echo -e "${YELLOW}■ ② /chat エンドポイント確認${NC}"

r=$(curl -sf -X POST "${HOST}/chat" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"こんにちは！あなたの名前を教えてください\", \"session_id\": \"${SESSION_ID}\"}" \
  || echo '{"error":"request_failed"}')

check "POST /chat - レスポンス成功" "$r" '"response":'
check "POST /chat - session_id 返却" "$r" '"session_id":'
check "POST /chat - action 返却" "$r" '"action":'
check "POST /chat - emotion 返却" "$r" '"emotion":'
echo "  応答: $(echo "$r" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response','')[:100])" 2>/dev/null || echo "$r" | head -c 200)"
echo ""

# ================================================================
# ③ Memory保存の動作確認（会話をまたいで記憶しているか）
# ================================================================
echo -e "${YELLOW}■ ③ Memory保存確認${NC}"

# 1回目: 情報を伝える
r1=$(curl -sf -X POST "${HOST}/chat" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"私の好きな食べ物はラーメンです。覚えておいてください。\", \"session_id\": \"${SESSION_ID}\"}" \
  || echo '{"error":"request_failed"}')
check "1回目のメッセージ送信" "$r1" '"response":'

# 2回目: 同一セッション内で記憶を問い合わせ
r2=$(curl -sf -X POST "${HOST}/chat" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"私が好きな食べ物は何だったか覚えていますか？\", \"session_id\": \"${SESSION_ID}\"}" \
  || echo '{"error":"request_failed"}')
check "2回目のメッセージ送信 (同一セッション)" "$r2" '"response":'

# Long-term memory に保存されているか確認
r3=$(curl -sf "${HOST}/memory/search?q=%E9%A3%9F%E3%81%B9%E7%89%A9&limit=5" \
  -H "$AUTH" \
  || echo '{"error":"request_failed"}')
check "GET /memory/search - 「食べ物」を検索" "$r3" '"results"'

echo "  記憶検索結果: $(echo "$r3" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('results',[]); print(f'{len(r)}件')" 2>/dev/null || echo "?")"
echo "  2回目の応答: $(echo "$r2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response','')[:150])" 2>/dev/null || echo "$r2" | head -c 200)"
echo ""

# Memory Stats 確認
r4=$(curl -sf "${HOST}/memory/stats" -H "$AUTH" || echo '{"error":"request_failed"}')
check "GET /memory/stats - 統計取得OK" "$r4" '"conversation_log"'
echo "  メモリ統計: $(echo "$r4" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, ensure_ascii=False))" 2>/dev/null || echo "$r4" | head -c 300)"
echo ""

# ================================================================
# ④ Emotion状態の確認
# ================================================================
echo -e "${YELLOW}■ ④ Emotion状態確認${NC}"

# 感情状態を取得
r5=$(curl -sf "${HOST}/emotion/state" -H "$AUTH" || echo '{"error":"request_failed"}')
check "GET /emotion/state - 6次元感情取得" "$r5" '"happiness"'
echo "  感情状態:"
echo "$r5" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for k in ['happiness','sadness','anger','fear','trust','surprise']:
        v = d.get(k, '?')
        bar = '█' * int(float(v) * 10) if isinstance(v, (int,float)) else ''
        print(f'    {k:<12} {bar:<10} {v}')
except:
    print('    ' + sys.stdin.read()[:200])
" 2>/dev/null || echo "  $r5" | head -c 300

# 感情ラベルを使って感情を変化させる
echo ""
echo "  感情を「happy」に調整して変化を確認..."
r6=$(curl -sf -X POST "${HOST}/emotion/adjust" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"emotion": "happy", "intensity": null}' \
  || echo '{"error":"request_failed"}')
check "POST /emotion/adjust (happy)" "$r6" '"adjustments"'

# 変化後の状態確認
r7=$(curl -sf "${HOST}/emotion/state" -H "$AUTH" || echo '{"error":"request_failed"}')
echo "  感情変化後:"
echo "$r7" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for k in ['happiness','sadness','trust']:
        v = d.get(k, '?')
        bar = '█' * int(float(v) * 10) if isinstance(v, (int,float)) else ''
        print(f'    {k:<12} {bar:<10} {v}')
except:
    print('    ' + sys.stdin.read()[:200])
" 2>/dev/null || echo "  $r7" | head -c 200

# 感情履歴
r8=$(curl -sf "${HOST}/emotion/history?limit=3" -H "$AUTH" || echo '{"error":"request_failed"}')
check "GET /emotion/history - 履歴取得OK" "$r8" '"history"'
echo ""

# ================================================================
# 結果サマリ
# ================================================================
total=$((pass + fail))
echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN} 結果: ${pass}/${total} 通過${NC}"
if [ $fail -eq 0 ]; then
  echo -e "${GREEN} ✅ 全チェック通過！cocoro-core は正常に動作しています。${NC}"
else
  echo -e "${RED} ❌ ${fail}件 失敗。上記のエラーを確認してください。${NC}"
fi
echo -e "${CYAN}================================================================${NC}"
echo ""

exit $fail
