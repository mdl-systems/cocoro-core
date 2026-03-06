# cocoro-core — Personality AI Operating System

> AI に「人格」を持たせるOS。LLMは「声帯」に過ぎない。  
> 人格の一貫性は Memory + Values + Decision Graph で保証する。

---

## System Architecture (v7+)

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 9: External Interface (API Gateway)                       │
│  ┌──────────┐                                                   │
│  │ FastAPI   │  POST /chat     POST /think    POST /decide      │
│  │  :8000    │  POST /tasks/*  POST /org/*    POST /schedules   │
│  │  Nginx    │  GET  /health   GET  /memory   GET  /identity    │
│  │  :8001    │  GET  /growth/* GET  /org/*    GET  /schedules   │
│  └─────┬────┘                                                   │
├────────┼────────────────────────────────────────────────────────┤
│ Layer 8: AI Organization (組織管理)                              │
│  ┌─────▼────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │Organization  │  │Department    │  │Agent          │         │
│  │Manager       │  │Management    │  │Registry       │         │
│  │(組織統率)     │  │(部門管理)     │  │(Agent台帳)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
├─────────────────────────────────────────────────────────────────┤
│ Layer 7: Agent Execution (エージェント実行)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │Task      │  │Worker    │  │Task      │  │Event     │      │
│  │Router    │→ │Manager   │  │Queue     │  │Bus       │      │
│  │(振分け)   │  │(実行管理) │  │(Redis)   │  │(Redis)   │      │
│  └──────────┘  └────┬─────┘  └──────────┘  └──────────┘      │
│                ┌────┴────┐                                     │
│                │ Workers │  [Dev / Sales / Marketing Agent]    │
│                └─────────┘                                     │
├─────────────────────────────────────────────────────────────────┤
│ Layer 6: AI Brain (推論・判断・ツール)                            │
│  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │Reasoning  │ │Decision  │ │Planner   │ │Tool          │    │
│  │Engine     │ │Graph     │ │          │ │Executor      │    │
│  │(思考連鎖)  │ │(判断木)   │ │(計画生成) │ │(FC連鎖 x10)  │    │
│  └───────────┘ └──────────┘ └──────────┘ └──────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ LLM Runtime (Gemini 2.0 Flash / Ollama fallback)    │       │
│  │   ・通常生成  ・Function Calling  ・Rate Limiter     │       │
│  └─────────────────────────────────────────────────────┘       │
├─────────────────────────────────────────────────────────────────┤
│ Layer 5: Personality (人格エンジン)                               │
│  ┌────────┐ ┌───────┐ ┌────────┐ ┌─────────┐ ┌────────┐     │
│  │Identity│ │Values │ │Beliefs │ │History  │ │Growth  │     │
│  │Engine  │ │System │ │System  │ │Tracker  │ │Tracker │     │
│  │(自己)   │ │(価値観)│ │(信念)   │ │(人格史)  │ │(成長)   │     │
│  └────┬───┘ └───┬───┘ └───┬────┘ └────┬────┘ └───┬────┘     │
│       └─────────┴─────────┴───────────┴──────────┘            │
│              Personality Engine + Consolidation                  │
│        (人格の一貫性保証 + 記憶定期統合 → 人格進化)                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: Memory (記憶システム)                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                │
│  │Short-Term│  │Long-Term │  │Vector Memory │                │
│  │ (Redis)  │  │(Postgres)│  │ (pgvector)   │                │
│  │ 会話履歴  │  │ 全記録    │  │ 意味検索     │                │
│  └──────────┘  └──────────┘  └──────────────┘                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: Infrastructure                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                │
│  │PostgreSQL│  │  Redis   │  │  Docker      │                │
│  │  + pg    │  │ (Cache/  │  │  Compose     │                │
│  │  vector  │  │  Queue)  │  │              │                │
│  └──────────┘  └──────────┘  └──────────────┘                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: OS       (Debian 13)                                   │
│ Layer 1: Hardware (miniPC: N95 / 16GB / 512GB SSD)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Philosophy

**人格 = Identity + Memory + Values + Reasoning**

- LLM は「道具」であり、人格OSの **「声帯」** に過ぎない
- 人格の一貫性は LLM の外側（Memory + Values + Decision Graph）で保証
- AI は経験を通じて成長する（Memory Consolidation → Personality Evolution）
- 組織として複数Agentが協調し、専門性を発揮する

---

## Data Flow

```
User Input
  │
  ├─[1] Short-Term Memory に保存 (Redis)
  │
  ▼
Decision Graph (入力分類)
  │
  ├── chat ──────→ Function Calling Engine (マルチツール連鎖)
  │                  │ Step1: LLM → ツール判断 → 実行
  │                  │ Step2: 結果蓄積 → 追加ツール判断
  │                  │ Step3: テキスト応答生成
  │                  ▼
  │                Response (ツール結果統合)
  │
  ├── think ─────→ Reasoning Engine ← Personality (価値観フィルタ)
  │                                  ← Memory (過去の経験)
  │
  ├── decide ────→ Decision Graph ← Value System (判断基準)
  │
  ├── delegate ──→ Task Router → Worker Manager → Agent 実行
  │                              └→ Task Queue (Redis)
  │                              └→ Event Bus (完了通知)
  │
  └── learn ─────→ Learning Log → Personality 更新
  │
  ▼
Memory Storage (Long-Term)
  │
  ▼ (6時間ごと)
Memory Consolidation → Personality Evolution (人格成長)
```

---

## Function Calling — AI Tool System

AIが自律的にツールを選択・連鎖実行する。最大3ツール連鎖対応。

### 利用可能ツール（10ツール）

| # | ツール名 | 用途 | 引数 |
|---|---|---|---|
| 1 | `search_memory` | 過去の会話検索 | `query` |
| 2 | `create_task` | タスク自動作成 | `title`, `description`, `agent` |
| 3 | `get_org_status` | 組織状況確認 | - |
| 4 | `search_learnings` | 学習内容検索 | `category` |
| 5 | `get_personality` | 人格情報取得 | - |
| 6 | `get_current_time` | 現在日時 | - |
| 7 | `web_search` | Web検索 (DuckDuckGo) | `query` |
| 8 | `add_schedule` | スケジュール追加 | `title`, `start_at`, `end_at`, `reminder_minutes` |
| 9 | `list_schedules` | スケジュール一覧 | `days` |
| 10 | `list_recent_tasks` | タスク一覧 | `status` |

### マルチツール連鎖

```
"組織とタスクの状況をまとめて教えて"
  │
  ▼ Step 1: Function Calling
  get_org_status() → 結果蓄積
  │
  ▼ Step 2: Function Calling (前回結果を含む)
  list_recent_tasks() → 結果蓄積
  │
  ▼ Step 3: テキスト生成 (全結果を統合)
  "組織は3名体制で全員稼働中、タスクは5件完了..."
```

---

## Directory Structure

```
cocoro-core/
├── api/
│   └── server.py           # FastAPI メインサーバー (全エンドポイント)
├── brain/
│   ├── llm_runtime.py       # LLM統合 (Gemini/Ollama, Function Calling)
│   ├── reasoning/           # 思考エンジン (Chain-of-Thought)
│   ├── decision_engine/     # 判断エンジン (分類 + 意思決定)
│   ├── planner/             # 計画立案エンジン
│   └── tools/
│       └── tool_registry.py # ツール定義 + 実行エンジン (10ツール)
├── personality/
│   ├── personality_engine.py # 人格統合エンジン
│   ├── identity.py          # 自己認識 (名前・役割・性格)
│   ├── values.py            # 価値観システム (優先度・重み付け)
│   ├── beliefs.py           # 信念システム (世界観・原則)
│   ├── history.py           # 人格変化履歴
│   └── growth_tracker.py    # 成長トラッカー
├── memory/
│   ├── memory_engine.py     # 記憶統合エンジン
│   ├── short_term.py        # 短期記憶 (Redis)
│   ├── long_term.py         # 長期記憶 (PostgreSQL)
│   ├── vector_store.py      # ベクトル検索 (pgvector)
│   └── consolidation.py     # 記憶定期統合 → 人格進化
├── agent/
│   ├── task_router/         # タスク振分けエンジン
│   ├── worker_manager/      # Worker管理 (非同期タスク実行)
│   ├── task_queue.py        # タスクキュー (Redis)
│   ├── event_bus.py         # イベントバス (Redis Pub/Sub)
│   ├── organization/        # 組織管理 (部門・Agent台帳・委任)
│   └── webhook/             # 外部通知 (Discord等)
├── infra/
│   ├── configs/             # 設定管理
│   └── docker/
│       ├── Dockerfile       # Pythonアプリイメージ
│       ├── docker-compose.yml
│       ├── init.sql          # DB初期化 (全テーブル定義)
│       └── nginx.conf        # リバースプロキシ
├── tests/                   # pytest テスト (25テスト)
├── docs/
│   └── ARCHITECTURE.md      # このファイル
└── requirements.txt
```

---

## API Endpoints

### Core
| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | メイン会話 (分類 → 処理 → Function Calling) |
| `POST` | `/think` | 深い思考 (Chain-of-Thought) |
| `POST` | `/decide` | 意思決定 (価値観ベース) |
| `GET` | `/health` | ヘルスチェック |

### Memory
| Method | Path | Description |
|---|---|---|
| `GET` | `/memory/search` | 長期記憶検索 |
| `GET` | `/memory/learnings` | 学習内容一覧 |
| `POST` | `/memory/consolidate` | 記憶統合トリガー |

### Personality
| Method | Path | Description |
|---|---|---|
| `GET` | `/identity` | 自己認識 |
| `GET,PUT` | `/values` | 価値観 |
| `GET,PUT` | `/beliefs` | 信念 |
| `GET` | `/personality/profile` | 完全プロフィール |

### Tasks
| Method | Path | Description |
|---|---|---|
| `GET` | `/tasks` | タスク一覧 |
| `POST` | `/tasks/async` | 非同期タスク投入 |
| `GET` | `/tasks/{id}/result` | タスク結果取得 |
| `GET` | `/queue/status` | キュー状態 |

### Organization
| Method | Path | Description |
|---|---|---|
| `GET` | `/org/report` | 組織レポート |
| `GET` | `/org/departments` | 部門一覧 |
| `GET` | `/org/agents` | Agent一覧 |
| `POST` | `/org/agents/register` | Agent登録 |
| `POST` | `/org/delegate` | タスク委任 |

### Schedules
| Method | Path | Description |
|---|---|---|
| `GET` | `/schedules` | スケジュール一覧 |
| `POST` | `/schedules` | スケジュール追加 |
| `DELETE` | `/schedules/{id}` | スケジュール削除 |

### Growth
| Method | Path | Description |
|---|---|---|
| `GET` | `/growth/report` | 成長レポート |
| `GET` | `/growth/timeline` | 進化タイムライン |

---

## Database Schema

### PostgreSQL Tables (12テーブル)

```sql
-- 記憶系
messages              -- 全会話ログ (session_id, role, content, emotion)
learning_log          -- 学習記録 (lesson, category, importance)
thought_log           -- 思考記録 (question, reasoning, conclusion)
decision_log          -- 判断記録 (question, decision, confidence, values)
knowledge_store       -- ベクトル記憶 (content, embedding, tags)

-- 人格系
personality_identity  -- 自己認識 (name, role, traits)
personality_values    -- 価値観 (value, priority, weight)
personality_beliefs   -- 信念 (belief, confidence, source)
personality_history   -- 人格変化履歴 (change_type, before, after)

-- タスク・組織系
tasks                 -- タスク管理 (title, status, assigned_agent, result)
departments           -- 部門 (name, description, manager_agent)
agent_registry        -- Agent台帳 (agent_type, role, capabilities, performance)
task_delegations      -- タスク委任記録

-- スケジュール系
schedules             -- スケジュール (title, start_at, end_at, recurrence)
```

### Redis Keys

```
stm:{session_id}      -- 短期記憶 (List, TTL: 24h)
queue:tasks            -- タスクキュー (List)
result:{task_id}       -- タスク結果 (String, TTL: 1h)
events:{channel}       -- イベント (Pub/Sub)
```

---

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.11 |
| API Framework | FastAPI | 0.109 |
| LLM Provider | Google Gemini | 2.0 Flash |
| LLM Fallback | Ollama | (local) |
| Database | PostgreSQL + pgvector | 16 |
| Cache/Queue | Redis | 7 |
| Container | Docker Compose | - |
| Reverse Proxy | Nginx | - |
| Test | pytest + pytest-asyncio | - |

---

## Version History

| Version | Feature | Status |
|---|---|---|
| v1 | Prototype (LLM + Memory) | ✅ Complete |
| v2 | System化 (FastAPI + Docker + PostgreSQL) | ✅ Complete |
| v3 | AIエージェント (Task Router + Worker Manager) | ✅ Complete |
| v4 | AI OS (Async Queue + Event Bus + Webhook) | ✅ Complete |
| v5 | Personality OS (Memory Consolidation + Growth) | ✅ Complete |
| v6 | AI Brain (Function Calling + Tool Chain) | ✅ Complete |
| v7 | AI Organization (Departments + Agent Registry) | ✅ Complete |
| v6+ | Tool Expansion (10ツール + マルチ連鎖) | ✅ Complete |
| v8 | AI Governance (Rules + Ethics + Audit) | 📋 Planned |
