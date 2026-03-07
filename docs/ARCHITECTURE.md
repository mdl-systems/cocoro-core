# cocoro-core — Personality AI Operating System

> AI に「人格」を持たせるOS。LLMは「声帯」に過ぎない。  
> 人格の一貫性は Memory + Values + Emotion + Decision Graph で保証する。

**Stats:** 53 modules / 131 API endpoints / 24 DB tables / 231 tests (9 test files)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 11: Dashboard & Voice (UI/UX)                             │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │Dashboard UI  │  │Voice         │                            │
│  │(/dashboard)  │  │Interface     │                            │
│  │リアルタイム   │  │(Web Speech   │                            │


│  │全機能可視化   │  │ API連携)     │                            │
│  └──────────────┘  └──────────────┘                            │
├─────────────────────────────────────────────────────────────────┤
│ Layer 10: External Interface (API Gateway)                      │
│  ┌──────────┐                                                   │
│  │ FastAPI   │  POST /chat     POST /think     POST /decide     │
│  │  :8000    │  POST /tasks/*  POST /org/*     POST /schedules  │
│  │  Nginx    │  GET  /health   GET  /emotion   GET  /clone/*    │
│  │  :8001    │  GET  /growth/* GET  /evolve/*  GET  /calibrate  │
│  │           │  POST /boot/*   POST /test/*    GET  /decide/... │
│  │           │  GET  /plugins  POST /voice/*   GET  /llm/*      │
│  │           │  POST /users/*  POST /comm/*    GET  /dashboard  │
│  │           │  GET  /security/status          GET /governance/* │
│  └─────┬────┘  131 endpoints                                   │
├────────┼────────────────────────────────────────────────────────┤
│ Layer 9.5: Security Middleware (D-10)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │Rate Limiter  │  │IP Filter     │  │Login Throttle│         │
│  │(Token Bucket)│  │(White/Black) │  │(Brute Force) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │Security      │  │HTTPS         │  Security Headers:         │
│  │Headers       │  │Enforcement   │  X-Content-Type-Options     │
│  │(6ヘッダー)    │  │(HSTS)        │  X-Frame-Options, X-XSS    │
│  └──────────────┘  └──────────────┘  Referrer-Policy, Perms    │
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
│  │ LLM Runtime (Gemini 2.5 Flash / Ollama)            │       │
│  │   ・通常生成  ・Function Calling  ・Rate Limiter     │       │
│  │                                                     │       │
│  │ Local LLM Manager (C-4)                             │       │
│  │   ・モデル管理  ・ヘルスチェック  ・FC エミュレーション │       │
│  │   ・Ollama API  ・モデル切り替え  ・自動フォールバック │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Plugin System (C-5)                                 │       │
│  │   ・動的プラグイン登録  ・math/time/format/random    │       │
│  │   ・有効/無効切替      ・ツール定義自動生成          │       │
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
│                                                                 │
│  ┌────────────────┐ ┌────────────────┐ ┌──────────────────┐   │
│  │Emotion Behavior│ │Multi-User      │ │Peer              │   │
│  │Adapter (C-6)   │ │Manager (C-2)   │ │Communication(C-3)│   │
│  │感情→行動パラメ │ │セッション管理   │ │人格間コミュ       │   │
│  │ータ変換        │ │プリファレンス   │ │ニケーション       │   │
│  └────────────────┘ └────────────────┘ └──────────────────┘   │
│              Personality Engine + Consolidation                  │
│     (6要素統合 + Emotion→Chat連動 + 記憶統合 → 人格進化)         │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: Memory (記憶システム)                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                │
│  │Short-Term│  │Long-Term │  │Vector Memory │                │
│  │ (Redis)  │  │(Postgres)│  │ (pgvector)   │                │
│  │ 会話履歴  │  │ 全記録    │  │ 意味検索     │                │
│  └──────────┘  └──────────┘  └──────────────┘                │
│  ┌──────────────────────────────────────────┐                  │
│  │ Memory Archiver (C-7)                    │                  │
│  │   ・自動アーカイブ  ・重複検出  ・統計    │                  │
│  └──────────────────────────────────────────┘                  │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: Infrastructure                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                │
│  │PostgreSQL│  │  Redis   │  │  Docker      │                │
│  │  + pg    │  │ (Cache/  │  │  Compose     │                │
│  │  vector  │  │  Queue)  │  │              │                │
│  └──────────┘  └──────────┘  └──────────────┘                │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                │
│  │Migration │  │CORS +    │  │Structured    │                │
│  │Runner    │  │Security  │  │JSON Logging  │                │
│  │(A-5)     │  │Middleware│  │(A-6)         │                │
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
- 感情は行動パラメータにも変換される（C-6: Emotion→Behavior Adapter）
- 組織として複数Agentが協調し、専門性を発揮する
- 複数のcocoro人格が協議で合意形成できる（C-3: Peer Communication）
- 倫理的制約はGovernance層で強制する
- マルチユーザーを個別セッションで分離管理する（C-2）
- 音声で対話可能、感情が声のトーンに反映される（C-8）

---

## Data Flow

```
User Input (テキスト or 音声)
  │
  ├─[0] Voice Interface: 音声認識 → コマンド解析 (C-8)
  │
  ├─[1] Multi-User: セッション取得/作成 (C-2)
  │     ユーザー固有プリファレンス適用
  │
  ├─[2] Short-Term Memory に保存 (Redis)
  │     Long-Term Memory に保存 (PostgreSQL + emotion付き)
  │
  ├─[3] Governance: 入力の倫理チェック → 不適切ならブロック
  │
  ▼
Decision Graph (入力分類 + 感情分析)
  │
  ├── Emotion Engine: ユーザー感情 → 6次元パラメータ更新
  │     happiness, sadness, anger, fear, trust, surprise
  │     │
  │     └── Emotion Behavior Adapter (C-6)
  │           → 行動パラメータ変換 (創造性/リスク許容/饒舌度/共感力)
  │           → 判断閾値調整 + 応答修飾生成
  │
  ├── chat ──────→ Function Calling Engine (マルチツール連鎖)
  │   │             │ Step1: LLM → ツール判断 → 実行
  │   │             │ Step2: 結果蓄積 → 追加ツール判断
  │   │             │ Step3: テキスト応答生成
  │   │             ▼
  │   │           Response (ツール結果統合)
  │   │             │
  │   │             └── Plugin System (C-5): 拡張ツール実行
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
Response Generation
  │
  ├── Voice Interface: 感情→音声パラメータ変換 (C-8)
  │     rate/pitch/volume が感情に連動
  │
  ├── Peer Communication: 必要に応じて他人格と協議 (C-3)
  │
  ├── Dashboard: リアルタイム更新 (C-1)
  │
  ▼
Memory Storage (Long-Term + emotion metadata)
  │
  ├── Self Observation: 会話・判断・感情変化を記録
  │
  ├── Emotion Decay: 自然な感情減衰（会話ごと）
  │
  ├── Memory Archiver: 古い記憶の自動整理 (C-7)
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

行動適応 (C-6):
  感情 → creativity_boost / risk_tolerance / verbosity /
          empathy_level / response_tone / decision_speed
  例: happiness → 創造性↑ リスク許容↑ 饒舌↑
      fear      → 創造性↓ リスク許容↓ 共感↑

音声パラメータ (C-8):
  感情 → rate / pitch / volume
  例: happiness → rate 1.1 / pitch 1.15 / volume 0.9
      sadness   → rate 0.85 / pitch 0.85 / volume 0.6
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

### 利用可能ツール（10ツール + プラグイン）

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

### Plugin System (C-5)

動的に追加可能なプラグインシステム。ビルトイン4種：

| Plugin | 機能 | 例 |
|---|---|---|
| `math` | 数式計算 | `2+3*4` → `14` |
| `time` | 日時情報 | 現在時刻、日付計算 |
| `format` | テキスト整形 | JSON/CSV変換 |
| `random` | 乱数生成 | ランダム選択、サイコロ |

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

## Multi-User Support (C-2)

```
セッション管理:
  ・ユーザーごとのセッション自動作成/取得
  ・セッションID (8文字ハッシュ)
  ・自動期限切れ (デフォルト60分)
  ・メッセージカウント追跡

プリファレンス:
  ・ユーザーごとの設定保存 (tone, language 等)
  ・プロンプトプレフィックス自動生成
  ・コンテキスト分離

統計:
  ・アクティブセッション数
  ・総メッセージ数
  ・ユーザー別アクティビティ
```

---

## Peer Communication (C-3)

```
人格間コミュニケーションプロトコル:
  ・複数 cocoro 人格が協議で意思決定
  ・ピア登録 (ID, 名前, エンドポイント, 人格要約)
  ・ピア解除

Discussion (協議セッション):
  ・トピックベースの協議開始
  ・意見追加 (stance: agree/disagree/neutral/question)
  ・結論付け + コンセンサスプロンプト生成
  ・協議ステータス管理 (active/concluded)

ダイレクトメッセージ:
  ・人格間の直接通信
  ・受信箱管理
  ・メッセージタイプ分類 (general/urgent/info)
```

---

## Local LLM Manager (C-4)

```
Ollama完全統合:
  ・モデル一覧 (GET /api/tags)
  ・モデル切り替え
  ・モデル詳細情報 (パラメータ, テンプレート)
  ・ヘルスチェック

Function Calling エミュレーション:
  ・プロンプトベースでツール定義を埋め込み
  ・LLM応答からJSON形式のツール呼び出しを解析
  ・Gemini FC互換インターフェース

フォールバック:
  ・LLM_PROVIDER=ollama → Ollama優先
  ・Ollama不可 → Gemini API にフォールバック
  ・環境変数: OLLAMA_BASE_URL, OLLAMA_MODEL
```

---

## Voice Interface (C-8)

```
音声コマンド認識 (10パターン):
  こんにちは     → greeting
  感情を教えて   → emotion_check
  タスクある？   → task_list
  覚えて         → memory_action
  設定変更       → settings
  ありがとう     → gratitude
  ヘルプ         → help
  黙って         → mute
  さようなら     → farewell
  名前は？       → identity

感情→音声パラメータ変換:
  neutral   → rate 1.0  / pitch 1.0  / volume 0.8
  happiness → rate 1.1  / pitch 1.15 / volume 0.9
  sadness   → rate 0.85 / pitch 0.85 / volume 0.6
  anger     → rate 1.15 / pitch 1.2  / volume 1.0
  fear      → rate 1.2  / pitch 1.3  / volume 0.5

ブラウザ連携: Web Speech API (SpeechRecognition + SpeechSynthesis)
```

---

## Dashboard UI (C-1)

```
リアルタイムダッシュボード (/dashboard):
  ・15秒自動更新
  ・認証付き (API Key)
  ・ダークモード UI

表示パネル:
  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
  │ 💗 感情状態   │ │ 🎭 行動適応  │ │ ⚡ システム   │
  │ 6次元グリッド │ │ バーグラフ   │ │ 概要        │
  ├─────────────┤ ├─────────────┤ ├─────────────┤
  │ 🔌 プラグイン │ │ 👥 セッション│ │ 🔗 人格間通信│
  │ 有効/無効一覧│ │ アクティブ数 │ │ ピア/協議    │
  ├─────────────┤ ├─────────────┤ ├─────────────┤
  │ 🧠 メモリ統計│ │ 🎤 音声入力  │ │ 🤖 LLM状態  │
  │ テーブル行数 │ │ STT + TTS  │ │ Ollama/Gemini│
  └─────────────┘ └─────────────┘ └─────────────┘
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

## Production Hardening (Phase A)

```
A-1/A-2/A-3: 基本安定化
  ・全テスト通過確認
  ・エラーハンドリング強化
  ・float精度正規化

A-4: CORS Middleware
  ・全オリジン許可 (開発用)
  ・OPTIONS preflight 対応

A-5: DB Migration Runner
  ・バージョン管理付きマイグレーション
  ・起動時自動実行
  ・手動実行/状態確認 API

A-6: Structured Logging
  ・JSON形式ログ出力
  ・RotatingFileHandler (/var/log/cocoro/)
  ・タイムスタンプ + レベル + ソース
```

---

## Directory Structure

```
cocoro-core/                        53 modules
├── api/
│   ├── server.py                   # FastAPI メインサーバー (131 endpoints)
│   ├── security.py                 # セキュリティミドルウェア (D-10)
│   └── static/
│       └── dashboard.html          # ダッシュボードUI (C-1)
├── brain/
│   ├── llm_runtime.py              # LLM統合 (Gemini/Ollama, FC, Rate Limiter)
│   ├── local_llm.py                # ローカルLLM管理 (C-4: Ollama)
│   ├── reasoning/
│   │   └── reasoning_engine.py     # 思考エンジン (Chain-of-Thought)
│   ├── decision_engine/
│   │   └── decision_graph.py       # 判断エンジン (Memory→Value→Emotion→Decision)
│   ├── planner/
│   │   └── planner.py              # 計画立案エンジン
│   └── tools/
│       ├── tool_registry.py        # ツール定義 + 実行エンジン (10ツール)
│       └── plugin_system.py        # プラグインシステム (C-5)
├── personality/
│   ├── personality_engine.py       # 人格統合エンジン (6要素 + 感情トーン)
│   ├── identity/identity.py        # 自己認識 (名前・役割・性格)
│   ├── values/value_system.py      # 価値観システム (優先度・重み付け)
│   ├── beliefs/belief_system.py    # 信念システム (世界観・原則)
│   ├── history/life_history.py     # 人格変化履歴
│   ├── emotion/emotion_engine.py   # 感情エンジン (6次元連続値)
│   ├── emotion_adapter.py          # 感情→行動適応 (C-6)
│   ├── goals/goal_engine.py        # 目標管理エンジン
│   ├── growth_tracker.py           # 成長 + シンクロ率 + 勾配調整
│   ├── clone_engine.py             # 人格バックアップ/復元/差分
│   ├── calibration.py              # 人格校正エンジン
│   ├── cognitive_profile.py        # 認知プロファイル分析
│   ├── multi_user.py               # マルチユーザー管理 (C-2)
│   ├── peer_communication.py       # 人格間コミュニケーション (C-3)
│   ├── voice_interface.py          # 音声インターフェース (C-8)
│   ├── setup/boot_wizard.py        # 初期設定ウィザード (40問)
│   └── test/
│       ├── decision_sampling.py    # 意思決定サンプリング
│       └── test_bench.py           # 200問テストベンチ
├── memory/
│   ├── memory_engine.py            # 記憶統合エンジン
│   ├── short_term/short_term.py    # 短期記憶 (Redis)
│   ├── long_term/long_term.py      # 長期記憶 (PostgreSQL)
│   ├── vector_memory/vector_memory.py  # ベクトル検索 (pgvector)
│   ├── consolidation.py            # 記憶定期統合 → 人格進化
│   └── memory_archiver.py          # 長期記憶自動整理 (C-7)
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
│   ├── migration.py                # DBマイグレーション (A-5)
│   └── docker/
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── init.sql                # DB初期化 (24テーブル)
│       └── nginx.conf
├── tests/                          # 231テスト (9ファイル)
│   ├── test_agent.py               # TaskRouter (13)
│   ├── test_brain.py               # Planner + Decision + Reasoning + LLM (14)
│   ├── test_e2e.py                 # E2E APIテスト D-1 (99: 全APIカテゴリ)
│   ├── test_emotion.py             # EmotionState + EmotionEngine (28)
│   ├── test_growth.py              # cosine_sim + gradient + learning_rate (18)
│   ├── test_memory.py              # Consolidation parser (4)
│   ├── test_next_gen.py            # C-2〜C-8 全テスト (42)
│   ├── test_personality.py         # PersonalityEngine + Observation (14)
│   └── test_security.py            # Security D-10 (19: RateLimiter/IPFilter/LoginThrottle)
├── docs/
│   └── ARCHITECTURE.md             # このファイル
└── requirements.txt
```

---

## API Endpoints (131 total)

### Core
| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | メイン会話 (分類 → 感情更新 → FC → 応答) |
| `POST` | `/think` | 深い思考 (Chain-of-Thought) |
| `POST` | `/decide` | 意思決定 (Memory→Value→Emotion→Decision) |
| `GET` | `/decide/pipeline` | Decision Pipeline 情報 |
| `GET` | `/health` | ヘルスチェック |
| `GET` | `/dashboard` | ダッシュボードUI (C-1) |

### Memory
| Method | Path | Description |
|---|---|---|
| `GET` | `/memory/search` | 長期記憶検索 |
| `GET` | `/memory/learnings` | 学習内容一覧 |
| `POST` | `/memory/consolidate` | 記憶統合トリガー |
| `GET` | `/memory/stats` | メモリ統計 (C-7) |
| `POST` | `/memory/archive` | アーカイブ実行 (C-7) |
| `GET` | `/memory/archive/history` | アーカイブ履歴 (C-7) |

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
| `GET` | `/emotion/adaptation` | 感情→行動適応 (C-6) |
| `GET` | `/emotion/decision-threshold` | 判断閾値 (C-6) |
| `GET` | `/emotion/response-modifiers` | 応答修飾 (C-6) |

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
| `POST` | `/governance/check` | 倒理チェック |
| `GET` | `/governance/report` | ガバナンス総合レポート |
| `GET` | `/governance/log` | ガバナンスログ履歴 |

### Security (D-10)
| Method | Path | Description |
|---|---|---|
| `GET` | `/security/status` | セキュリティ状況一覧 |
| `POST` | `/auth/token` | JWTトークン発行 (Login Throttle統合) |

### Plugins (C-5)
| Method | Path | Description |
|---|---|---|
| `GET` | `/plugins` | プラグイン一覧 + 統計 |
| `POST` | `/plugins/execute` | プラグイン実行 |
| `GET` | `/plugins/tools` | ツール定義一覧 |
| `GET` | `/plugins/stats` | プラグイン統計 |

### Local LLM (C-4)
| Method | Path | Description |
|---|---|---|
| `GET` | `/llm/local/models` | モデル一覧 |
| `GET` | `/llm/local/health` | ヘルスチェック |
| `POST` | `/llm/local/switch` | モデル切り替え |
| `GET` | `/llm/local/info` | モデル詳細 |
| `GET` | `/llm/local/stats` | LLM統計 |

### Multi-User (C-2)
| Method | Path | Description |
|---|---|---|
| `POST` | `/users/session` | セッション作成/取得 |
| `DELETE` | `/users/session/{user_id}` | セッション終了 |
| `GET` | `/users/sessions` | アクティブセッション一覧 |
| `POST` | `/users/preference` | ユーザー設定保存 |
| `GET` | `/users/preferences/{user_id}` | ユーザー設定取得 |
| `GET` | `/users/stats` | ユーザー統計 |

### Peer Communication (C-3)
| Method | Path | Description |
|---|---|---|
| `POST` | `/comm/peer` | ピア登録 |
| `GET` | `/comm/peers` | ピア一覧 |
| `POST` | `/comm/discussion` | 協議開始 |
| `POST` | `/comm/discussion/{id}/opinion` | 意見追加 |
| `POST` | `/comm/discussion/{id}/conclude` | 協議結論 |
| `GET` | `/comm/discussions` | 協議一覧 |
| `POST` | `/comm/message` | DM送信 |
| `GET` | `/comm/inbox` | 受信箱 |
| `GET` | `/comm/stats` | 通信統計 |

### Voice Interface (C-8)
| Method | Path | Description |
|---|---|---|
| `POST` | `/voice/parse` | 音声コマンド解析 |
| `POST` | `/voice/speak` | テキスト読み上げ準備 |
| `GET` | `/voice/settings` | 音声設定取得 |
| `POST` | `/voice/settings` | 音声設定変更 |
| `GET` | `/voice/stats` | 音声統計 |

### Migration (A-5)
| Method | Path | Description |
|---|---|---|
| `GET` | `/migrate/status` | マイグレーション状態 |
| `POST` | `/migrate/run` | マイグレーション実行 |

---

## Database Schema

### PostgreSQL Tables (24テーブル)

```sql
-- 記憶系 (5)
conversation_log      -- 全会話ログ (session_id, role, content, emotion)
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
| LLM Provider | Google Gemini | 2.5 Flash |
| LLM Local | Ollama (C-4) | (local) |
| Database | PostgreSQL + pgvector | 16 |
| Cache/Queue | Redis | 7 |
| Container | Docker Compose | - |
| Reverse Proxy | Nginx | - |
| Test | pytest + pytest-asyncio | 231 tests (9 files) |
| Voice | Web Speech API | Browser |

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
| A | Phase A: Production Hardening (CORS + Migration + Logging) | ✅ Complete |
| B | Phase B: 86→133 Tests + Decision Full Pipeline | ✅ Complete |
| C-1 | Dashboard UI (リアルタイムWebダッシュボード) | ✅ Complete |
| C-2 | Multi-User Support (セッション管理) | ✅ Complete |
| C-3 | Peer Communication (人格間コミュニケーション) | ✅ Complete |
| C-4 | Local LLM Manager (Ollama完全統合) | ✅ Complete |
| C-5 | Plugin System (動的プラグイン) | ✅ Complete |
| C-6 | Emotion Behavior Adapter (感情→行動適応) | ✅ Complete |
| C-7 | Memory Archiver (長期記憶自動整理) | ✅ Complete |
| C-8 | Voice Interface (音声インターフェース) | ✅ Complete |
| D-1 | E2E Tests (99 API統合テスト) | ✅ Complete |
| D-10 | Security (Rate Limit / IP Filter / Login Throttle / Headers) | ✅ Complete |

---

## Security Architecture (D-10)

```
Security Middleware (全リクエストに適用):
  1. IP Filter       — ホワイトリスト/ブラックリスト
  2. Rate Limiter    — Token Bucket (パス別レート制御)
  3. Login Throttle  — 認証失敗カウント + IPロックアウト
  4. Security Headers— 6ヘッダー自動付与
  5. HTTPS Enforce   — HTTP→HTTPSリダイレクト + HSTS

Rate Limit 設定:
  /auth/*     → 10回/100秒  (ブルートフォース防止)
  /chat       → 30回/60秒   (会話保護)
  その他      → 120回/60秒

Login Throttle:
  デフォルト: 10回失敗で300秒ロックアウト
  認証成功でカウンターリセット

環境変数:
  IP_WHITELIST            カンマ区切り。空=全IP許可
  IP_BLACKLIST            カンマ区切り。ブラックリスト優先
  FORCE_HTTPS             true/false
  RATE_LIMIT_ENABLED      true/false
  LOGIN_MAX_FAILURES      デフォルト 10
  LOGIN_LOCKOUT_SECONDS   デフォルト 300
```

---

## PersonalityVector — 8次元人格ベクトル

```
8D PersonalityVector (v3.5/v4 準拠):
  honesty        █████████ 0.9  core       誠実であること
  efficiency     ███████   0.7  work       効率を重視すること
  growth         ████████  0.8  core       継続的に成長すること
  empathy        ██████    0.6  social     共感を持って接すること
  logic          ████████  0.8  thinking   論理的に判断すること
  courage        ████      0.4  core       リスクを恐れないこと
  risk_tolerance █████     0.5  decision   不確実性を受け入れる力
  curiosity      ███████   0.7  thinking   未知への探究心と学習意欲

シンクロ率 = cos_sim(current_8D, ideal_8D) × 100
勾配降下法で理想ベクトルに漸近 (イエスマン防止: 92%で停止)
```

---

## Governance Layer

```
GovernanceManager (統合管理):
  ├── EthicsEngine       harm/law/value 3段階チェック
  │     ・有害キーワード検出 (11パターン)
  │     ・機密トピック検出 (4パターン)
  │     ・リスクレベル: safe/caution/warning/blocked
  ├── SafetyMonitor      自己改変・急変検知
  │     ・価値観変更幅 ≤ 0.10/step
  │     ・感情変動幅 ≤ 0.30/step
  │     ・過度な変更は自動ブロック
  └── AlignmentEngine    オーナー整合性監視
        ・シンクロ率 < 50% → warning (乖離)
        ・シンクロ率 > 92% → caution (イエスマンリスク)
        ・ログ: governance_log テーブルに全記録
```

---

## Testing Strategy

```
231 Tests / 9 Files / 1.42s

ユニットテスト (132):
  test_agent.py       ── TaskRouterルーティング (13)
  test_brain.py       ── Planner/Decision/Reasoning/LLM (14)
  test_emotion.py     ── EmotionState/EmotionEngine (28)
  test_growth.py      ── cosine_sim/gradient/learning_rate (18)
  test_memory.py      ── Consolidation parser (4)
  test_next_gen.py    ── Plugin/MultiUser/PeerComm/Voice/LLM (42)
  test_personality.py ── PersonalityEngine/SelfObservation (14)

E2Eテスト (99):
  test_e2e.py         ── 全APIカテゴリ統合テスト (D-1)
    Health/Dashboard/Decision/Emotion/Growth/Evolution/
    Personality/Cognitive/Clone/Migration/Plugins/LLM/
    MultiUser/PeerComm/Voice/Org/Memory/ValueScoring/
    Intelligence/Safety/Queue/Auth/Error/Goals/Governance/Security

セキュリティテスト (19):
  test_security.py    ── RateLimiter/LoginThrottle/IPFilter (D-10)

全テストはDocker内で実行: pytest tests/ -v --tb=short
```
