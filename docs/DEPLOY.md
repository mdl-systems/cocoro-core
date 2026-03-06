# cocoro-core — miniPC デプロイ手順

## Debian 13.3 インストール時の設定

Debianインストーラーで以下を選択:

```
ホスト名:      cocoro
ユーザー名:     好きな名前
デスクトップ:   ☐ チェック外す（不要）
SSHサーバー:   ☑ チェック入れる
標準ユーティリティ: ☑ チェック入れる
```

---

## インストール後（miniPCに直接 or SSH）

### 1. 初期設定（コピペ用）

```bash
# root権限
sudo -i

# パッケージ更新
apt update && apt upgrade -y

# 必須ツール
apt install -y git curl wget htop ca-certificates gnupg lsb-release

# タイムゾーン
timedatectl set-timezone Asia/Tokyo

# IPアドレス確認（SSHする場合）
ip a | grep inet
```

### 2. Docker インストール（コピペ用）

```bash
# Docker GPG鍵
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# リポジトリ追加
# ※ Debian 13 (trixie) の場合
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" | tee /etc/apt/sources.list.d/docker.list

# インストール
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 一般ユーザーでdocker使えるように
usermod -aG docker $(logname)

# 有効化
systemctl enable docker
systemctl start docker

# rootから抜ける
exit
```

**※ ログアウト → ログインし直す**（dockerグループ反映のため）

### 3. 確認

```bash
docker --version
docker compose version
```

### 4. cocoro-core デプロイ

```bash
cd ~
git clone https://github.com/mdl-systems/cocoro-core.git
cd cocoro-core

# 環境変数設定
cp .env.example infra/docker/.env
nano infra/docker/.env
```

`.env` の中身：
```
LLM_PROVIDER=gemini
GEMINI_API_KEY=ここにAPIキーを入力
GEMINI_MODEL=gemini-2.0-flash
POSTGRES_PASSWORD=cocoro_secret
LOG_LEVEL=INFO
```

### 5. 起動

```bash
cd ~/cocoro-core/infra/docker
docker compose up -d --build
```

初回ビルドは3-5分かかります。

### 6. 動作確認

```bash
# ヘルスチェック
curl http://localhost:8000/health

# 初期人格確認
curl http://localhost:8000/profile | python3 -m json.tool

# 会話テスト
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "こんにちは。自己紹介して"}'
```

---

## ✅ 全ステップ完了の確認

```bash
# この3つが全部成功すれば完了
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/profile | python3 -m json.tool
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "テスト"}' | python3 -m json.tool
```

---

## トラブルシューティング

```bash
# コンテナ状態確認
docker compose ps

# ログ確認
docker compose logs -f cocoro-core
docker compose logs cocoro-postgres
docker compose logs cocoro-redis

# DB接続確認
docker exec cocoro-postgres pg_isready -U cocoro

# 全部やり直す場合
docker compose down -v
docker compose up -d --build
```
