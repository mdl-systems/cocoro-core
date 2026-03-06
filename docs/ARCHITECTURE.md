# cocoro-core — Personality AI Operating System

> AI に「人格」を持たせるOS。LLMは「声帯」に過ぎない。  
> 人格の一貫性は Memory + Values + Emotion + Decision Graph で保証する。

**Stats:** 46 modules / 91 API endpoints / 24 DB tables / 86 tests

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 10: External Interface (API Gateway)                      │
│  ┌──────────┐                                                   │
│  │ FastAPI   │  POST /chat     POST /think     POST /decide     │
│  │  :8000    │  POST /tasks/*  POST /org/*     POST /schedules  │
│  │  Nginx    │  GET  /health   GET  /emotion   GET  /clone/*    │
│  │  :8001    │  GET  /growth/* GET  /evolve/*  GET  /calibrate  │
│  │           │  POST /boot/*   POST /test/*    GET  /decide/... │
│  └─────┬────┘  91 endpoints                                    │
├────────┼────────────────────────────────────────────────────────┤
│ Layer 9: Governance (倫理・安全)                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │Governance    │  │Safety        │  │Value Scoring │         │
│  │Engine        │  │Engine        │  │Engine        │         │
│  │(入力倫理検査) │  │(安全性評価)   │  │(応答価値判定) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
├─────────────────────────────────────────────────────────────────┤
│ Layer 8: AI Organization (組織管理)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
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
│  Decision Graph Pipeline:                                       │
│    Memory → Value → Emotion → Decision                          │
│    (記憶検索) (価値観) (感情バイアス警告)  (統合判断)              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ LLM Runtime (Gemini 2.5 Flash Lite / Ollama)       │       │
│  │   ・通常生成  ・Function Calling  ・Rate Limiter     │       │
│  └─────────────────────────────────────────────────────┘       │
├─────────────────────────────────────────────────────────────────┤
│ Layer 5: Evolution (自己進化)                                    │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────┐  │
│  │Self       │ │Self       │ │Improvement│ │Meta          │  │
│  │Observation│ │Evaluation │ │Engine     │ │Cognition     │  │
│  │(自己観察)  │ │(自己評価)  │ │(改善計画)  │ │(メタ認知)     │  │
│  └───────────┘ └───────────┘ └───────────┘ └──────────────┘  │
│  ┌───────────┐ ┌───────────┐                                  │
│  │Intelligence│ │Safety     │                                  │
│  │Engine     │ │Monitor    │                                  │
│  │(知性測定)  │ │(安全監視)  │                                  │
│  └───────────┘ └───────────┘                                  │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: Personality (人格エンジン)                               │
│  ┌────────┐ ┌───────┐ ┌────────┐ ┌─────────┐ ┌────────┐     │
│  │Identity│ │Values │ │Beliefs │ │History  │ │Emotion │     │
│  │Engine  │ │System │ │System  │ │Tracker  │ │Engine  │     │
│  │(自己)   │ │(価値観)│ │(信念)   │ │(人格史)  │ │(6感情)  │     │
│  └────┬───┘ └───┬───┘ └───┬────┘ └────┬────┘ └───┬────┘     │
│       └─────────┴─────────┴───────────┴──────────┘            │
│  ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐  │
│  │Goals   │ │Growth  │ │Clone   │ │Calibrate │ │Cognitive│  │
│  │Engine  │ │Tracker │ │Engine  │ │Engine    │ │Profile  │  │
│  │(目標)   │ │(成長)   │ │(バック │ │(校正)    │ │(認知)   │  │
│  │        │ │+Sync%  │ │ アップ) │ │          │ │         │  │
│  └────────┘ └────────┘ └─────────┘ └──────────┘ └────────┘  │
│              Personality Engine + Consolidation                  │
│     (6要素統合 + Emotion→Chat連動 + 記憶統合 → 人格進化)         │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: Memory (記憶システム)                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                │
│  │Short-Term│  │Long-Term │  │Vector Memory │                │
│  │ (Redis)  │  │(Postgres)│  │ (pgvector)   │                │
│  │ 会話履歴  │  │ 全記録    │  │ 意味検索     │                │
│  └──────────┘  └──────────┘  └──────────────┘                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: Infrastructure                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                │
│  │PostgreSQL│  │  Redis   │  │  Docker      │                │
│  │  + pg    │  │ (Cache/  │  │  Compose     │                │
│  │  vector  │  │  Queue)  │  │              │                │
│  └──────────┘  └──────────┘  └──────────────┘                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: OS       (Debian 13)                                   │
│ Layer 0: Hardware (miniPC: N95 / 16GB / 512GB SSD)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Philosophy

**人格 = Identity + Memory + Values + Emotion + Reasoning**

- LLM は「道具」であり、人格OSの **「声帯」** に過ぎない
- 人格の一貫性は LLM の外側（Memory + Values + Emotion + Decision Graph）で保証
- AI は経験を通じて成長する（Memory Consolidation → Personality Evolution）
- 感情は判断とトーンに連続的に影響する（6次元感情モデル）
- 組織として複数Agentが協調し、専門性を発揮する
- 倫理的制約はGovernance層で強制する

---

## Data Flow

```
User Input
  │
  ├─[1] Short-Term Memory に保存 (Redis)
  │     Long-Term Memory に保存 (PostgreSQL + emotion付き)
  │
  ├─[2] Governance: 入力の倫理チェック → 不適切ならブロック
  │
  ▼
Decision Graph (入力分類 + 感情分析)
  │
  ├── Emotion Engine: ユーザー感情 → 6次元パラメータ更新
  │     happiness, sadness, anger, fear, trust, surprise
  │
  ├── chat ──────→ Function Calling Engine (マルチツール連鎖)
  │   │             │ Step1: LLM → ツール判断 → 実行
  │   │             │ Step2: 結果蓄積 → 追加ツール判断
  │   │             │ Step3: テキスト応答生成
  │   │             ▼
  │   │           Response (ツール結果統合)
  │   │
  │   └── System Prompt = Personality(6要素) + Emotion Tone Directive
  │        └── Creative Friction (シンクロ率 > 85% で独立性維持)
  │
  ├── think ─────→ Reasoning Engine ← Personality (価値観フィルタ)
  │                                  ← Memory (過去の経験)
  │
  ├── decide ────→ Decision Graph (フルパイプライン)
  │                  Memory → Value → Emotion → Decision
  │                  (記憶検索) (価値観) (バイアス警告) (統合判断)
  │
  ├── delegate ──→ Task Router → Worker Manager → Agent 実行
  │                              └→ Task Queue (Redis)
  │                              └→ Event Bus (完了通知)
  │
  └── learn ─────→ Learning Log → Personality 更新
  │
  ▼
Memory Storage (Long-Term + emotion metadata)
  │
  ├── Self Observation: 会話・判断・感情変化を記録
  │
  ├── Emotion Decay: 自然な感情減衰（会話ごと）
  │
  ▼ (6時間ごと)
Memory Consolidation → Personality Evolution (人格成長)
  └→ Growth Tracker → Sync Rate (シンクロ率)
  └→ Gradient Adjustment (理想に向かう価値観調整)
```

---

## Emotion Engine — 6次元感情モデル

```
感情パラメータ (0.0 - 1.0):
  happiness ██████████ 0.5 (中立値)
  sadness   █         0.1
  anger                0.0
  fear      █         0.1
  trust     ██████    0.6
  surprise  ██        0.2

ラベルマッピング:
  happy    → happiness+0.20, sadness-0.05, trust+0.05
  grateful → happiness+0.15, trust+0.15, sadness-0.05
  excited  → happiness+0.15, surprise+0.15, fear-0.05
  curious  → surprise+0.10, happiness+0.05, fear-0.03
  sad      → sadness+0.20, happiness-0.10, trust-0.05
  angry    → anger+0.25, happiness-0.10, trust-0.10
  anxious  → fear+0.20, happiness-0.05, trust-0.05, sadness+0.05

Chat統合:
  ・dominant emotion → 応答トーン指示 (6パターン)
  ・intensity >= 0.1 → トーン指示をsystem promptに注入
  ・会話後に自動 decay (中立値に10%接近)

判断への影響:
  ・happiness → 楽観的バイアス警告
  ・sadness   → 悲観的バイアス警告
  ・anger     → 攻撃的バイアス警告
  ・fear      → 回避バイアス警告
  ・trust     → 信頼過多バイアス警告
  ・surprise  → 新奇性バイアス警告
```

---

## Decision Graph — Full Pipeline

```
v1仕様: Memory → Value → Emotion → Decision

Stage 1: Memory (記憶検索)
  ├── 関連する過去の会話を検索 (long_term.search)
  ├── 関連する学習データを検索 (long_term.search_learnings)
  └── 過去の関連判断を取得 (get_past_decisions)

Stage 2: Value (価値観適用)
  ├── weight >= 0.6 の価値観を抽出
  └── 判断コンテキストとして注入

Stage 3: Emotion (感情バイアス警告)
  ├── 現在の dominant emotion + intensity を計算
  └── 感情バイアス警告を注入（6種類）

Stage 4: Decision (統合判断)
  ├── LLM が全コンテキストを統合して判断
  └── 出力: decision, reasoning, values_applied,
            memory_influence, emotion_influence,
            confidence, risk, alternatives
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

---

## Growth & Sync Rate

```
シンクロ率: ユーザー理想 (ideal_profile) と現在の価値観の余弦類似度

計算:  cos_sim(current_values, ideal_values) × 100

動的学習率 (イエスマン防止):
  sync < 70%   → 加速 (1.5x)  まだ距離がある
  70-85%       → 通常 (1.0x)
  85-92%       → 減速 (0.3x)  収束に近い
  > 92%        → 停止 (0.0)   Divergence Ceiling

Creative Friction:
  sync > 85% → AIが建設的に反論する指示をsystem promptに注入
  → 「イエスマン化」を防ぎ、AI固有の視点を維持
```

---

## Personality Setup & Testing

```
Boot Wizard (初期設定):
  ・40問のインタビューで人格を構築
  ・カテゴリ: 価値観, 性格, 思考, 対人, 感情, 美学, 仕事,
              リスク, 人生観, 日常

Calibration Engine (校正):
  ・ジレンマ問題で価値観の一貫性を検証
  ・理論 vs 実践の差異を発見

Decision Sampling (意思決定サンプル):
  ・価値観を可視化するための標本的質問

Test Bench (200問テスト):
  ・10カテゴリ × 20問 = 200問で人格一致率を測定
  ・LLM回答 vs 理想回答の一致率計算
```

---

## Directory Structure

```
cocoro-core/                        46 modules
├── api/
│   └── server.py                   # FastAPI メインサーバー (91 endpoints)
├── brain/
│   ├── llm_runtime.py              # LLM統合 (Gemini/Ollama, FC, Rate Limiter)
│   ├── reasoning/
│   │   └── reasoning_engine.py     # 思考エンジン (Chain-of-Thought)
│   ├── decision_engine/
│   │   └── decision_graph.py       # 判断エンジン (Memory→Value→Emotion→Decision)
│   ├── planner/
│   │   └── planner.py              # 計画立案エンジン
│   └── tools/
│       └── tool_registry.py        # ツール定義 + 実行エンジン (10ツール)
├── personality/
│   ├── personality_engine.py       # 人格統合エンジン (6要素 + 感情トーン)
│   ├── identity/identity.py        # 自己認識 (名前・役割・性格)
│   ├── values/value_system.py      # 価値観システム (優先度・重み付け)
│   ├── beliefs/belief_system.py    # 信念システム (世界観・原則)
│   ├── history/life_history.py     # 人格変化履歴
│   ├── emotion/emotion_engine.py   # 感情エンジン (6次元連続値)
│   ├── goals/goal_engine.py        # 目標管理エンジン
│   ├── growth_tracker.py           # 成長 + シンクロ率 + 勾配調整
│   ├── clone_engine.py             # 人格バックアップ/復元/差分
│   ├── calibration.py              # 人格校正エンジン
│   ├── cognitive_profile.py        # 認知プロファイル分析
│   ├── setup/boot_wizard.py        # 初期設定ウィザード (40問)
│   └── test/
│       ├── decision_sampling.py    # 意思決定サンプリング
│       └── test_bench.py           # 200問テストベンチ
├── memory/
│   ├── memory_engine.py            # 記憶統合エンジン
│   ├── short_term/short_term.py    # 短期記憶 (Redis)
│   ├── long_term/long_term.py      # 長期記憶 (PostgreSQL)
│   ├── vector_memory/vector_memory.py  # ベクトル検索 (pgvector)
│   └── consolidation.py            # 記憶定期統合 → 人格進化
├── evolution/
│   ├── self_observation.py         # 自己観察 (8カテゴリ)
│   ├── self_evaluation.py          # 自己評価
│   ├── improvement.py              # 改善計画生成・実行
│   ├── meta_cognition.py           # メタ認知 (自己認識)
│   ├── intelligence.py             # 知性測定
│   ├── value_scoring.py            # 応答の価値判定
│   └── safety.py                   # 安全性監視
├── governance/
│   └── governance_engine.py        # 倫理チェック + ルール管理
├── agent/
│   ├── task_router/router.py       # タスク振分けエンジン
│   ├── worker_manager/manager.py   # Worker管理 (非同期タスク実行)
│   ├── task_queue.py               # タスクキュー (Redis)
│   ├── event_bus.py                # イベントバス (Redis Pub/Sub)
│   ├── organization/manager.py     # 組織管理 (部門・Agent・委任)
│   └── webhook/notifier.py         # 外部通知
├── infra/
│   ├── configs/settings.py         # 設定管理
│   └── docker/
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── init.sql                # DB初期化 (24テーブル)
│       └── nginx.conf
├── tests/                          # 86テスト (6ファイル)
│   ├── test_agent.py               # TaskRouter (8)
│   ├── test_brain.py               # Planner + Decision + Reasoning + LLM (14)
│   ├── test_emotion.py             # EmotionState + EmotionEngine (28)
│   ├── test_growth.py              # cosine_sim + gradient + learning_rate (18)
│   ├── test_memory.py              # Consolidation parser (4)
│   └── test_personality.py         # PersonalityEngine + Observation (14)
├── docs/
│   └── ARCHITECTURE.md             # このファイル
└── requirements.txt
```

---

## API Endpoints (91 total)

### Core
| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | メイン会話 (分類 → 感情更新 → FC → 応答) |
| `POST` | `/think` | 深い思考 (Chain-of-Thought) |
| `POST` | `/decide` | 意思決定 (Memory→Value→Emotion→Decision) |
| `GET` | `/decide/pipeline` | Decision Pipeline 情報 |
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
| `GET,PUT` | `/identity` | 自己認識 |
| `GET,PUT` | `/values` | 価値観 |
| `GET,PUT` | `/beliefs` | 信念 |
| `GET` | `/personality/profile` | 完全プロフィール |
| `GET,POST` | `/goals` | 目標管理 |
| `PUT,DELETE` | `/goals/{id}` | 目標更新・削除 |

### Emotion
| Method | Path | Description |
|---|---|---|
| `GET` | `/emotion` | 感情状態 + プロンプト文 |
| `GET` | `/emotion/state` | 6次元感情パラメータ |
| `POST` | `/emotion/adjust` | 感情調整 |
| `GET` | `/emotion/history` | 感情変化履歴 |
| `POST` | `/emotion/decay` | 手動減衰 |

### Tasks & Agent
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

### Growth & Sync
| Method | Path | Description |
|---|---|---|
| `GET` | `/growth/report` | 成長レポート |
| `GET` | `/growth/timeline` | 進化タイムライン |
| `GET` | `/sync/rate` | シンクロ率 |
| `POST` | `/sync/record` | シンクロ率記録 |
| `GET` | `/sync/timeline` | シンクロ率推移 |

### Evolution
| Method | Path | Description |
|---|---|---|
| `GET` | `/observe/recent` | 自己観察データ |
| `GET` | `/observe/stats` | 観察統計 |
| `POST` | `/evolve/evaluate` | 自己評価 |
| `POST` | `/evolve/improve` | 改善計画生成 |
| `POST` | `/evolve/execute` | 改善計画実行 |
| `GET` | `/evolve/dashboard` | 進化ダッシュボード |
| `GET` | `/evolve/metacognition` | メタ認知レポート |
| `GET` | `/evolve/intelligence` | 知性レポート |
| `GET` | `/evolve/safety` | 安全性レポート |

### Personality Testing
| Method | Path | Description |
|---|---|---|
| `POST` | `/boot/start` | Boot Wizard 開始 |
| `POST` | `/boot/answer` | 質問回答 |
| `GET` | `/boot/progress` | 進捗確認 |
| `GET` | `/boot/result` | セットアップ結果 |
| `POST` | `/calibrate/start` | 校正開始 |
| `POST` | `/calibrate/answer` | 校正回答 |
| `GET` | `/calibrate/report` | 校正レポート |
| `POST` | `/test/bench/start` | 200問テスト開始 |
| `POST` | `/test/bench/answer` | テスト回答 |
| `GET` | `/test/bench/score` | テストスコア |

### Clone (人格バックアップ)
| Method | Path | Description |
|---|---|---|
| `GET` | `/clone/backup` | 人格完全バックアップ |
| `POST` | `/clone/restore` | 人格復元 |
| `POST` | `/clone/diff` | 差分比較 |

### Schedules
| Method | Path | Description |
|---|---|---|
| `GET` | `/schedules` | スケジュール一覧 |
| `POST` | `/schedules` | スケジュール追加 |
| `DELETE` | `/schedules/{id}` | スケジュール削除 |

### Governance
| Method | Path | Description |
|---|---|---|
| `POST` | `/governance/check` | 倫理チェック |
| `POST` | `/governance/modify` | 変更許可チェック |
| `GET` | `/governance/report` | ガバナンスレポート |

---

## Database Schema

### PostgreSQL Tables (24テーブル)

```sql
-- 記憶系 (5)
messages              -- 全会話ログ (session_id, role, content, emotion)
learning_log          -- 学習記録 (lesson, category, importance)
thought_log           -- 思考記録 (question, reasoning, conclusion)
decision_log          -- 判断記録 (question, decision, confidence, values)
knowledge_store       -- ベクトル記憶 (content, embedding, tags)

-- 人格系 (7)
personality_identity  -- 自己認識 (name, profile, philosophy)
values_system         -- 価値観 (name, weight, category, description)
personality_beliefs   -- 信念 (statement, confidence, source, evidence_count)
personality_history   -- 人格変化履歴
emotion_state         -- 感情状態 (6パラメータ)
emotion_history       -- 感情変化履歴 (trigger, before, after)
goals                 -- 目標 (title, goal_type, priority, status)

-- 成長系 (4)
ideal_profile         -- 理想の人格プロファイル (key, value)
sync_rate_history     -- シンクロ率推移
clone_backups         -- 人格バックアップ記録
calibration_results   -- 校正結果

-- 進化系 (2)
self_observations     -- 自己観察記録 (obs_type, summary, impact_score)
improvement_plans     -- 改善計画記録

-- タスク・組織系 (4)
tasks                 -- タスク管理 (title, status, assigned_agent, result)
departments           -- 部門 (name, description, manager_agent)
agent_registry        -- Agent台帳 (agent_type, role, capabilities)
task_delegations      -- タスク委任記録

-- スケジュール系 (1)
schedules             -- スケジュール (title, start_at, end_at, recurrence)

-- ガバナンス系 (1)
governance_rules      -- 倫理ルール (rule_type, content, severity)
```

### Redis Keys

```
stm:{session_id}      -- 短期記憶 (List, TTL: 24h)
queue:tasks            -- タスクキュー (List)
result:{task_id}       -- タスク結果 (String, TTL: 1h)
events:{channel}       -- イベント (Pub/Sub)
```

---

## Error Handling

```
Global Exception Handlers (3層):
  1. LLMError      → 503 {"error": "AI応答エラー", "type": "llm_error"}
  2. PostgresError  → 503 {"error": "DBエラー",     "type": "database_error"}
  3. Exception      → 500 {"error": "内部エラー",    "type": "internal_error"}

全APIは JSON形式でエラーを返す（HTML 500ページなし）
float精度: 全API出力を round(x, 3) で正規化
```

---

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.11 |
| API Framework | FastAPI | 0.109 |
| LLM Provider | Google Gemini | 2.5 Flash Lite |
| LLM Fallback | Ollama | (local) |
| Database | PostgreSQL + pgvector | 16 |
| Cache/Queue | Redis | 7 |
| Container | Docker Compose | - |
| Reverse Proxy | Nginx | - |
| Test | pytest + pytest-asyncio | 86 tests |

---

## Version History

| Version | Feature | Status |
|---|---|---|
| v1 | Prototype (LLM + Memory + Decision Graph) | ✅ Complete |
| v2 | System化 (FastAPI + Docker + PostgreSQL) | ✅ Complete |
| v2.5 | Intelligence (Reasoning + Planner + Values) | ✅ Complete |
| v3 | AIエージェント (Task Router + Worker Manager) | ✅ Complete |
| v3.5 | Personality Testing (Boot Wizard + Calibration) | ✅ Complete |
| v4 | AI OS (Async Queue + Event Bus + Webhook) | ✅ Complete |
| v5 | Self Evolution (Observation + Evaluation + Improvement) | ✅ Complete |
| v6 | AI Brain (Function Calling + Tool Chain × 10) | ✅ Complete |
| v7 | AI Organization (Departments + Agent Registry) | ✅ Complete |
| G | Phase G: Test Bench 200q + Clone Engine | ✅ Complete |
| A | Phase A: Emotion→Chat + Error Handling + Float fix | ✅ Complete |
| B | Phase B: 86 Tests + Decision Full Pipeline | ✅ Complete |
