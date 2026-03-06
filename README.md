# cocoro-core 🧠

> **Personality AI Operating System** — AIに「人格」を与えるOS

Cocoro Core は LLM を「声帯」として使い、人格の一貫性を Memory + Values + Emotion + Decision Graph で保証する AI OS です。

**46 modules / 91 API endpoints / 24 DB tables / 86 tests**

## Features

- 🧠 **AI Brain** — 思考連鎖 (ReasoningEngine)、判断木 (DecisionGraph)、計画生成 (Planner)
- 💬 **Function Calling** — 10ツール自律選択 + マルチツール連鎖（最大3回）
- 👤 **Personality Engine** — Identity / Values / Beliefs / Emotion (6次元) + 記憶統合による人格進化
- 💖 **Emotion Engine** — 6次元感情モデル (happiness/sadness/anger/fear/trust/surprise) → Chat統合 + 判断バイアス警告
- 🧬 **Memory System** — Short-Term (Redis) + Long-Term (PostgreSQL) + Vector Search (pgvector)
- 🔄 **Self Evolution** — 自己観察 → 自己評価 → 改善計画 → 実行 + メタ認知
- 🤖 **Agent Organization** — Dev / Sales / Marketing Agent + 部門管理 + タスク委任
- ⚡ **Async Task Queue** — Redis キュー + Event Bus + Worker Manager
- 🛡️ **Governance** — 入力倫理チェック + 変更許可 + 安全性監視
- 📊 **Growth Tracker** — シンクロ率 (余弦類似度) + 勾配調整 + Creative Friction
- 🧪 **Testing Suite** — Boot Wizard (40問) + Calibration + Test Bench (200問)
- 📦 **Clone Engine** — 人格バックアップ / 復元 / 差分比較
- 📅 **Schedule Management** — スケジュール登録・確認（Function Calling経由）
- 🌐 **Web Search** — DuckDuckGo API 連携

## Quick Start

```bash
# 1. Clone
git clone https://github.com/mdl-systems/cocoro-core.git
cd cocoro-core

# 2. 環境変数
cp .env.example infra/docker/.env
# .env に GEMINI_API_KEY を設定

# 3. 起動
cd infra/docker && docker compose up -d --build

# 4. テスト
docker exec cocoro-core python -m pytest tests/ -v

# 5. 会話
curl -X POST http://localhost:8001/chat \
  -H "Authorization: Bearer cocoro-secret-2026" \
  -H "Content-Type: application/json" \
  -d '{"message": "こんにちは、自己紹介して"}'
```

## Architecture

詳細は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照。

```
Layer 10: API Gateway     (FastAPI + Nginx, 91 endpoints)
Layer 9:  Governance       (Ethics + Safety + Value Scoring)
Layer 8:  Organization    (Departments + Agent Registry)
Layer 7:  Agent Execution (Task Router + Worker + Queue + EventBus)
Layer 6:  AI Brain        (Reasoning + Decision Pipeline + Planner + Tools)
Layer 5:  Evolution       (Observation + Evaluation + Improvement + Meta)
Layer 4:  Personality     (Identity + Values + Beliefs + Emotion + Goals + Growth)
Layer 3:  Memory          (Short-Term + Long-Term + Vector)
Layer 2:  Infrastructure  (PostgreSQL + Redis + Docker)
```

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11 |
| API | FastAPI |
| LLM | Google Gemini 2.5 Flash Lite |
| Database | PostgreSQL 16 + pgvector |
| Cache/Queue | Redis 7 |
| Container | Docker Compose |

## License

AGPL-3.0 — See [LICENSE](LICENSE)
