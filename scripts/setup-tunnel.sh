#!/bin/bash
# ============================================================
# setup-tunnel.sh — Cloudflare Tunnel セットアップ
# Usage: sudo bash scripts/setup-tunnel.sh
# ============================================================
set -euo pipefail

TUNNEL_NAME="cocoro"
HOSTNAME="console.cocoro.ai"
LOCAL_SERVICE="http://localhost:80"
CLOUDFLARED_CONFIG="${HOME}/.cloudflared/config.yml"

echo "================================================================"
echo " Cocoro OS — Cloudflare Tunnel Setup"
echo "================================================================"
echo ""

# ------------------------------------------------
# 1. cloudflared インストール
# ------------------------------------------------
echo "[1/6] Installing cloudflared..."
if command -v cloudflared &>/dev/null; then
    echo "  cloudflared already installed: $(cloudflared --version)"
else
    apt-get update -qq
    apt-get install -y cloudflared
    echo "  cloudflared installed: $(cloudflared --version)"
fi

# ------------------------------------------------
# 2. Cloudflare 認証
# ------------------------------------------------
echo ""
echo "[2/6] Authenticating with Cloudflare..."
echo "  ブラウザが開きます。Cloudflareにログインして認証してください。"
cloudflared tunnel login

# ------------------------------------------------
# 3. トンネル作成
# ------------------------------------------------
echo ""
echo "[3/6] Creating tunnel '${TUNNEL_NAME}'..."
# すでに同名トンネルが存在する場合はスキップ
if cloudflared tunnel list 2>/dev/null | grep -q "${TUNNEL_NAME}"; then
    echo "  Tunnel '${TUNNEL_NAME}' already exists. Skipping creation."
else
    cloudflared tunnel create "${TUNNEL_NAME}"
fi

# TUNNEL_ID を取得
TUNNEL_ID=$(cloudflared tunnel list --output json 2>/dev/null \
    | python3 -c "import sys,json; tunnels=json.load(sys.stdin); \
      match=[t for t in tunnels if t['name']=='${TUNNEL_NAME}']; \
      print(match[0]['id'] if match else '')" 2>/dev/null || echo "")

if [[ -z "${TUNNEL_ID}" ]]; then
    echo "ERROR: Failed to retrieve tunnel ID. Check 'cloudflared tunnel list'."
    exit 1
fi
echo "  Tunnel ID: ${TUNNEL_ID}"

# ------------------------------------------------
# 4. DNS ルート登録
# ------------------------------------------------
echo ""
echo "[4/6] Routing DNS: ${HOSTNAME} -> ${TUNNEL_NAME}..."
cloudflared tunnel route dns "${TUNNEL_NAME}" "${HOSTNAME}" || {
    echo "  WARNING: DNS routing may already be set. Continuing..."
}

# ------------------------------------------------
# 5. config.yml 生成
# ------------------------------------------------
echo ""
echo "[5/6] Generating ${CLOUDFLARED_CONFIG}..."
mkdir -p "${HOME}/.cloudflared"

# 認証情報ファイルのパスを確認
CREDS_FILE="${HOME}/.cloudflared/${TUNNEL_ID}.json"
if [[ ! -f "${CREDS_FILE}" ]]; then
    # Debian/Ubuntu では /root/.cloudflared/ に保存される場合も
    ALT_CREDS="/root/.cloudflared/${TUNNEL_ID}.json"
    if [[ -f "${ALT_CREDS}" ]]; then
        CREDS_FILE="${ALT_CREDS}"
    fi
fi

cat > "${CLOUDFLARED_CONFIG}" << EOF
# Cloudflare Tunnel 設定 — cocoro-core
# 生成日時: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

tunnel: ${TUNNEL_ID}
credentials-file: ${CREDS_FILE}

ingress:
  # Cocoro Console (Nginx 経由)
  - hostname: ${HOSTNAME}
    service: ${LOCAL_SERVICE}
    originRequest:
      # LLM ストリーミングのタイムアウトに対応
      connectTimeout: 30s
      noTLSVerify: false
  # フォールバック (全未マッチリクエスト)
  - service: http_status:404
EOF

echo "  Config written to: ${CLOUDFLARED_CONFIG}"
cat "${CLOUDFLARED_CONFIG}"

# ------------------------------------------------
# 6. systemd サービス登録 & 起動
# ------------------------------------------------
echo ""
echo "[6/6] Installing systemd service..."
cloudflared service install
systemctl enable cloudflared
systemctl start cloudflared

echo ""
echo "================================================================"
echo " ✅ Cloudflare Tunnel Setup Complete!"
echo ""
echo "  Tunnel Name : ${TUNNEL_NAME}"
echo "  Tunnel ID   : ${TUNNEL_ID}"
echo "  Public URL  : https://${HOSTNAME}"
echo "  Local Target: ${LOCAL_SERVICE}"
echo ""
echo "  Status check: systemctl status cloudflared"
echo "  Tunnel logs : journalctl -u cloudflared -f"
echo "================================================================"
