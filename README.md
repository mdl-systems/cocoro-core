# cocoro-core 🧠

![Version](https://img.shields.io/badge/version-1.0.0-pink)
![Tests](https://img.shields.io/badge/tests-231%20passed-green)
![License](https://img.shields.io/badge/license-AGPL--3.0-blue)

> **Personality AI Operating System** — AI に「人格」を与える OS

Cocoro Core は LLM を**「声帯」**として扱い、人格の一貫性を **Memory + Values + Emotion + Decision Graph** で保証する AI OS です。
LLM が変わっても、記憶・価値観・感情・判断軸は維持されます。

**53 modules / 131 API endpoints / 24 DB tables / 231 tests (9 files)**

---

## ✨ Features

| カテゴリ | 機能 |
|---|---|
| 🧠 **AI Brain** | 思考連鎖 (ReasoningEngine)、判断木 (DecisionGraph)、計画生成 (Planner) |
| 💬 **Function Calling** | 10ツール自律選択 + マルチツール連鎖（最大3回）+ Plugin System |
| 👤 **Personality Engine** | Identity / Values / Beliefs / Emotion (6次元) + 記憶統合による人格進化 |
| 💖 **Emotion Engine** | 6次元感情モデル → Chat統合 + 判断バイアス警告 + 音声パラメータ変換 |
| 🎭 **Emotion→Behavior** | 感情 → 創造性/リスク許容/饒舌度/共感力へのリアルタイム適応 (C-6) |
| 🧬 **Memory System** | Short-Term (Redis) + Long-Term (PostgreSQL) + Vector Search (pgvector) |
| 🗃️ **Memory Archiver** | 古い記憶の自動整理・重複検出・統計 (C-7) |
| 🔄 **Self Evolution** | 自己観察 → 自己評価 → 改善計画 → 実行 + メタ認知 |
| 🤖 **Agent Organization** | Dev / Sales / Marketing Agent + 部門管理 + タスク委任 |
| ⚡ **Async Task Queue** | Redis キュー + Event Bus + Worker Manager |
| 🛡️ **Governance** | 入力倫理チェック + Safety Monitor + Alignment Engine |
| 🔒 **Security (D-10)** | Rate Limiter / IP Filter / Login Throttle / Security Headers / HTTPS |
| 📊 **Growth Tracker** | シンクロ率 (余弦類似度) + 勾配調整 + Creative Friction (イエスマン防止) |
| 🧪 **Personality Testing** | Boot Wizard (40問) + Calibration Engine + Test Bench (200問) |
| 📦 **Clone Engine** | 人格バックアップ / 復元 / 差分比較 |
| 👥 **Multi-User** | ユーザーごとのセッション分離 + プリファレンス管理 (C-2) |
| 🤝 **Peer Communication** | 複数 cocoro 人格間の協議・意思決定 (C-3) |
| 🖥️ **Local LLM** | Ollama 完全統合 + Function Calling エミュレーション + 自動フォールバック (C-4) |
| 📊 **Dashboard UI** | リアルタイムWebダッシュボード (15秒自動更新) (C-1) |
| 🎤 **Voice Interface** | Web Speech API 連携 + 感情→音声パラメータ変換 (C-8) |
| 📅 **Schedules** | スケジュール登録・確認（Function Calling 経由） |
| 🌐 **Web Search** | DuckDuckGo API 連携 |

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/mdl-systems/cocoro-core.git
cd cocoro-core

# 2. 環境変数の設定
cp .env.example infra/docker/.env
# .env に GEMINI_API_KEY と COCORO_API_KEY を設定

# 3. 起動
cd infra/docker && docker compose up -d --build

# 4. ヘルスチェック
curl http://localhost:8001/health

# 5. 会話
curl -X POST http://localhost:8001/chat \
  -H "Authorization: Bearer <COCORO_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"message": "こんにちは、自己紹介して"}'

# 6. テスト実行
docker exec cocoro-core python -m pytest tests/ -v --tb=short
```

### ダッシュボードにアクセス

```
http://localhost:8001/dashboard
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 11: Dashboard & Voice (UI/UX)                         │
├─────────────────────────────────────────────────────────────┤
│ Layer 10: API Gateway    (FastAPI + Nginx, 131 endpoints)   │
├─────────────────────────────────────────────────────────────┤
│ Layer 9.5: Security      (Rate Limit / IP Filter / HTTPS)   │
├─────────────────────────────────────────────────────────────┤
│ Layer 9:  Governance     (Ethics + Safety + Value Scoring)  │
├─────────────────────────────────────────────────────────────┤
│ Layer 8:  Organization   (Departments + Agent Registry)     │
├─────────────────────────────────────────────────────────────┤
│ Layer 7:  Agent Execution(Task Router + Worker + Queue)     │
├─────────────────────────────────────────────────────────────┤
│ Layer 6:  AI Brain       (Reasoning + Decision + Tools×10)  │
├─────────────────────────────────────────────────────────────┤
│ Layer 5:  Evolution      (Observation + Evaluation + Meta)  │
├─────────────────────────────────────────────────────────────┤
│ Layer 4:  Personality    (Identity + Values + Emotion×6)    │
├─────────────────────────────────────────────────────────────┤
│ Layer 3:  Memory         (Short-Term + Long-Term + Vector)  │
├─────────────────────────────────────────────────────────────┤
│ Layer 2:  Infrastructure (PostgreSQL + Redis + Docker)      │
├─────────────────────────────────────────────────────────────┤
│ Layer 1:  OS             (Debian 13)                        │
│ Layer 0:  Hardware       (miniPC: N95 / 16GB / 512GB SSD)  │
└─────────────────────────────────────────────────────────────┘
```

詳細は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照。

---

## ⚙️ Environment Variables

| 変数名 | 説明 | デフォルト |
|---|---|---|
| `LLM_PROVIDER` | `gemini` or `ollama` | `gemini` |
| `GEMINI_API_KEY` | Google Gemini API キー | **必須** |
| `GEMINI_MODEL` | 使用モデル名 | `gemini-2.0-flash` |
| `OLLAMA_MODEL` | Ollama モデル名 | `gemma2:2b` |
| `COCORO_API_KEY` | API認証キー | **必須** |
| `POSTGRES_PASSWORD` | PostgreSQL パスワード | `cocoro_secret` |
| `JWT_SECRET` | JWT署名キー（空=API Key認証） | - |
| `JWT_EXPIRE_HOURS` | JWTトークン有効期間(時間) | `24` |
| `IP_WHITELIST` | 許可IPリスト（カンマ区切り） | 全IP許可 |
| `IP_BLACKLIST` | ブロックIPリスト（カンマ区切り） | - |
| `FORCE_HTTPS` | HTTPS強制 (本番では `true`) | `false` |
| `RATE_LIMIT_ENABLED` | レートリミット有効/無効 | `true` |
| `LOGIN_MAX_FAILURES` | 認証失敗許容回数 | `10` |
| `LOGIN_LOCKOUT_SECONDS` | ロックアウト時間(秒) | `300` |

---

## 🔧 Tech Stack

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.11 |
| API Framework | FastAPI | 0.109 |
| LLM Provider | Google Gemini | 2.5 Flash |
| LLM Local | Ollama (C-4) | (local) |
| Database | PostgreSQL + pgvector | 16 |
| Cache / Queue | Redis | 7 |
| Container | Docker Compose | - |
| Reverse Proxy | Nginx | - |
| Test | pytest + pytest-asyncio | 231 tests (9 files) |
| Voice | Web Speech API | Browser |

---

## 📐 Core Concepts

### Personality Engine — 人格の6要素

| 要素 | 説明 |
|---|---|
| **Identity** | 自己認識（名前・役割・性格） |
| **Values** | 価値観（優先度・重み付き8次元ベクトル） |
| **Beliefs** | 信念（世界観・原則・確信度） |
| **Emotion** | 感情（happiness / sadness / anger / fear / trust / surprise） |
| **Goals** | 目標（短期・長期・優先度） |
| **History** | 人格変化履歴 |

### Decision Graph — 判断パイプライン

```
Memory → Value → Emotion → Decision
（記憶検索）→（価値観適用）→（感情バイアス警告）→（統合判断）
```

### Growth & Sync Rate — 成長システム

```
シンクロ率 = cos_sim(現在の価値観ベクトル, 理想ベクトル) × 100

< 70%  → 学習加速 (1.5x)
70-85% → 通常学習 (1.0x)
85-92% → 学習減速 (0.3x)  ← Creative Friction 発動
> 92%  → 学習停止 (Divergence Ceiling)
```

---

## 🧰 Available Tools (Function Calling)

| # | ツール | 説明 |
|---|---|---|
| 1 | `search_memory` | 過去の会話検索 |
| 2 | `create_task` | タスク自動作成 |
| 3 | `get_org_status` | 組織状況確認 |
| 4 | `search_learnings` | 学習内容検索 |
| 5 | `get_personality` | 人格情報取得 |
| 6 | `get_current_time` | 現在日時 |
| 7 | `web_search` | Web検索 (DuckDuckGo) |
| 8 | `add_schedule` | スケジュール追加 |
| 9 | `list_schedules` | スケジュール一覧 |
| 10 | `list_recent_tasks` | タスク一覧 |
| + | Plugins (C-5) | math / time / format / random |

---

## 📁 Directory Structure

```
cocoro-core/                        53 modules
├── api/
│   ├── server.py                   # FastAPI メインサーバー (131 endpoints)
│   ├── security.py                 # セキュリティミドルウェア (D-10)
│   └── static/dashboard.html      # ダッシュボードUI (C-1)
├── brain/
│   ├── llm_runtime.py              # LLM統合 (Gemini/Ollama, FC)
│   ├── local_llm.py                # ローカルLLM管理 (C-4)
│   ├── reasoning/                  # 思考エンジン
│   ├── decision_engine/            # 判断エンジン (Memory→Value→Emotion→Decision)
│   ├── planner/                    # 計画立案エンジン
│   └── tools/                      # ツール定義 + プラグインシステム (C-5)
├── personality/
│   ├── personality_engine.py       # 人格統合エンジン (6要素)
│   ├── identity/                   # 自己認識
│   ├── values/                     # 価値観システム
│   ├── beliefs/                    # 信念システム
│   ├── emotion/                    # 感情エンジン (6次元)
│   ├── emotion_adapter.py          # 感情→行動適応 (C-6)
│   ├── growth_tracker.py           # 成長 + シンクロ率
│   ├── clone_engine.py             # 人格バックアップ/復元
│   ├── multi_user.py               # マルチユーザー管理 (C-2)
│   ├── peer_communication.py       # 人格間コミュニケーション (C-3)
│   ├── voice_interface.py          # 音声インターフェース (C-8)
│   └── setup/boot_wizard.py        # 初期設定ウィザード (40問)
├── memory/
│   ├── memory_engine.py            # 記憶統合エンジン（クロスセッション記憶対応）
│   ├── short_term/                 # 短期記憶 (Redis)
│   ├── long_term/                  # 長期記憶 (PostgreSQL)
│   ├── vector_memory/              # ベクトル検索 (pgvector)
│   ├── consolidation.py            # 記憶定期統合 → 人格進化
│   └── memory_archiver.py          # 長期記憶自動整理 (C-7)
├── evolution/                      # 自己進化モジュール群
├── governance/                     # 倫理チェック + ルール管理
├── agent/                          # タスクルーター + ワーカー + 組織管理
├── infra/
│   ├── configs/settings.py
│   └── docker/                     # Dockerfile, docker-compose.yml, nginx.conf
├── tests/                          # 231テスト (9ファイル)
├── docs/ARCHITECTURE.md            # 詳細アーキテクチャドキュメント
└── requirements.txt
```

---

## 🧪 Testing

```bash
# 全テスト実行
docker exec cocoro-core python -m pytest tests/ -v --tb=short

# カテゴリ別実行
docker exec cocoro-core python -m pytest tests/test_e2e.py -v        # E2E (99)
docker exec cocoro-core python -m pytest tests/test_emotion.py -v    # Emotion (28)
docker exec cocoro-core python -m pytest tests/test_next_gen.py -v   # C-2〜C-8 (42)
docker exec cocoro-core python -m pytest tests/test_security.py -v   # Security (19)
```

| テストファイル | 対象 | テスト数 |
|---|---|---|
| `test_agent.py` | TaskRouter | 13 |
| `test_brain.py` | Planner / Decision / Reasoning | 14 |
| `test_e2e.py` | E2E API 統合テスト (D-1) | 99 |
| `test_emotion.py` | EmotionState / EmotionEngine | 28 |
| `test_growth.py` | cosine_sim / gradient / learning_rate | 18 |
| `test_memory.py` | Consolidation parser | 4 |
| `test_next_gen.py` | Plugin / MultiUser / PeerComm / Voice / LLM | 42 |
| `test_personality.py` | PersonalityEngine / SelfObservation | 14 |
| `test_security.py` | RateLimiter / LoginThrottle / IPFilter (D-10) | 19 |

---

## 📦 Version History

| Version | Feature | Status |
|---|---|---|
| v1 | Prototype (LLM + Memory + Decision Graph) | ✅ |
| v2 | System化 (FastAPI + Docker + PostgreSQL) | ✅ |
| v2.5 | Intelligence (Reasoning + Planner + Values) | ✅ |
| v3 | AI Agent (Task Router + Worker Manager) | ✅ |
| v3.5 | Personality Testing (Boot Wizard + Calibration) | ✅ |
| v4 | AI OS (Async Queue + Event Bus + Webhook) | ✅ |
| v5 | Self Evolution (Observation + Evaluation + Improvement) | ✅ |
| v6 | AI Brain (Function Calling × 10) | ✅ |
| v7 | AI Organization (Departments + Agent Registry) | ✅ |
| Phase G | Test Bench 200q + Clone Engine | ✅ |
| Phase A | Production Hardening (CORS + Migration + Logging) | ✅ |
| Phase B | 86→133 Tests + Decision Full Pipeline | ✅ |
| C-1 | Dashboard UI (リアルタイムWebダッシュボード) | ✅ |
| C-2 | Multi-User Support (セッション管理) | ✅ |
| C-3 | Peer Communication (人格間コミュニケーション) | ✅ |
| C-4 | Local LLM Manager (Ollama完全統合) | ✅ |
| C-5 | Plugin System (動的プラグイン) | ✅ |
| C-6 | Emotion Behavior Adapter (感情→行動適応) | ✅ |
| C-7 | Memory Archiver (長期記憶自動整理) | ✅ |
| C-8 | Voice Interface (音声インターフェース) | ✅ |
| D-1 | E2E Tests (99 API統合テスト) | ✅ |
| D-10 | Security (Rate Limit / IP Filter / Login Throttle) | ✅ |
| **D-11** | **クロスセッション記憶 + `/memory/search` + nginx固定** | ✅ |

---

## 📄 License

AGPL-3.0 — See [LICENSE](LICENSE)
