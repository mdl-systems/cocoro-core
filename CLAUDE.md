# CLAUDE.md — cocoro-core

> このrepoはCocoro OSのコアエンジンです。
> プロジェクト全体の概要は cocoro-docs/CLAUDE.md を参照してください。

---

## このrepoの役割

**Personality AI OS** のコアエンジン。
LLMを「声帯」として扱い、人格の一貫性を Memory + Values + Emotion + Decision Graph で保証します。
LLMが変わっても、記憶・価値観・感情・判断軸は維持されます。

- **53 modules / 131 API endpoints / 24 DB tables / 231 tests**
- **ライセンス**: AGPL-3.0

---

## テックスタック

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11 |
| API Framework | FastAPI | 0.109 |
| LLM (Cloud) | Google Gemini | 2.5 Flash |
| LLM (Local) | Ollama | - |
| Database | PostgreSQL + pgvector | 16 |
| Cache / Queue | Redis | 7 |
| Container | Docker Compose + Nginx | - |
| Test | pytest + pytest-asyncio | 231 tests (9 files) |

---

## 環境変数

設定ファイル: `infra/docker/.env`（`.env.example` からコピー）

```bash
LLM_PROVIDER=gemini           # or ollama
GEMINI_API_KEY=<key>          # 必須（Gemini使用時）
GEMINI_MODEL=gemini-2.0-flash
COCORO_API_KEY=<key>          # API認証キー（必須）
POSTGRES_PASSWORD=cocoro_secret
JWT_SECRET=<secret>           # 空=API Key認証
FORCE_HTTPS=false             # 本番はtrue
RATE_LIMIT_ENABLED=true
LOGIN_MAX_FAILURES=10
LOGIN_LOCKOUT_SECONDS=300
```

---

## よく使うコマンド

```bash
# 起動
cd infra/docker && docker compose up -d --build

# ヘルスチェック
curl http://localhost:8001/health

# 会話テスト
curl -X POST http://localhost:8001/chat \
  -H "Authorization: Bearer <COCORO_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"message": "こんにちは、自己紹介して"}'

# ダッシュボード（ブラウザ）
open http://localhost:8001/dashboard

# ログ確認
docker logs cocoro-core -f

# コンテナに入る
docker exec -it cocoro-core bash
```

---

## テスト

```bash
# 全件実行
docker exec cocoro-core python -m pytest tests/ -v --tb=short

# カテゴリ別
docker exec cocoro-core python -m pytest tests/test_e2e.py -v        # E2E (99)
docker exec cocoro-core python -m pytest tests/test_emotion.py -v    # Emotion (28)
docker exec cocoro-core python -m pytest tests/test_next_gen.py -v   # C-2〜C-8 (42)
docker exec cocoro-core python -m pytest tests/test_security.py -v   # Security (19)
docker exec cocoro-core python -m pytest tests/test_brain.py -v      # Brain (14)
docker exec cocoro-core python -m pytest tests/test_growth.py -v     # Growth (18)
docker exec cocoro-core python -m pytest tests/test_agent.py -v      # Agent (13)
docker exec cocoro-core python -m pytest tests/test_personality.py -v # Personality (14)
docker exec cocoro-core python -m pytest tests/test_memory.py -v     # Memory (4)
```

---

## アーキテクチャ（11層構造）

```
Layer 11: Dashboard & Voice        (Web UI / Web Speech API)
Layer 10: API Gateway              (FastAPI + Nginx, 131 endpoints)
Layer 9.5: Security                (Rate Limit / IP Filter / HTTPS)
Layer 9:  Governance               (Ethics + Safety + Value Scoring)
Layer 8:  Organization             (Departments + Agent Registry)
Layer 7:  Agent Execution          (Task Router + Worker + Queue)
Layer 6:  AI Brain                 (Reasoning + Decision + Tools×10)
Layer 5:  Evolution                (Observation + Evaluation + Meta)
Layer 4:  Personality              (Identity + Values + Emotion×6)
Layer 3:  Memory                   (Short-Term:Redis / Long-Term:PG / Vector:pgvector)
Layer 2:  Infrastructure           (PostgreSQL + Redis + Docker)
Layer 1:  OS                       (Debian 13)
Layer 0:  Hardware                 (miniPC: N95 / 16GB / 512GB SSD)
```

### Decision Graph パイプライン（順序厳守）
```
Memory → Value → Emotion → Decision
（記憶検索）→（価値観適用）→（感情バイアス警告）→（統合判断）
```

### シンクロ率の学習制御
```
< 70%  → 学習加速 (1.5x)
70-85% → 通常学習 (1.0x)
85-92% → 学習減速 (0.3x)  ← Creative Friction 発動
> 92%  → 学習停止          ← Divergence Ceiling（注意）
```

---

## ディレクトリ構成

```
cocoro-core/
├── api/
│   ├── server.py                   # FastAPI メインサーバー (131 endpoints)
│   ├── security.py                 # セキュリティミドルウェア
│   └── static/dashboard.html      # ダッシュボードUI
├── brain/
│   ├── llm_runtime.py              # LLM統合 (Gemini/Ollama, FC)
│   ├── local_llm.py                # ローカルLLM管理
│   ├── reasoning/                  # 思考エンジン
│   ├── decision_engine/            # 判断エンジン
│   ├── planner/                    # 計画立案エンジン
│   └── tools/                      # ツール定義 + プラグインシステム
├── personality/
│   ├── personality_engine.py       # 人格統合エンジン (6要素)
│   ├── emotion/                    # 感情エンジン (6次元)
│   ├── emotion_adapter.py          # 感情→行動適応
│   ├── growth_tracker.py           # 成長 + シンクロ率
│   ├── clone_engine.py             # 人格バックアップ/復元
│   ├── multi_user.py               # マルチユーザー管理
│   ├── peer_communication.py       # 人格間コミュニケーション
│   ├── voice_interface.py          # 音声インターフェース
│   └── setup/boot_wizard.py        # 初期設定ウィザード (40問)
├── memory/
│   ├── memory_engine.py            # 記憶統合エンジン
│   ├── short_term/                 # 短期記憶 (Redis)
│   ├── long_term/                  # 長期記憶 (PostgreSQL)
│   ├── vector_memory/              # ベクトル検索 (pgvector)
│   ├── consolidation.py            # 記憶定期統合 → 人格進化
│   └── memory_archiver.py          # 長期記憶自動整理
├── evolution/                      # 自己進化モジュール群
├── governance/                     # 倫理チェック + ルール管理
├── agent/                          # タスクルーター + ワーカー + 組織管理
├── infra/
│   ├── configs/settings.py
│   └── docker/                     # Dockerfile, docker-compose.yml, nginx.conf
├── tests/                          # 231テスト (9ファイル)
├── docs/ARCHITECTURE.md
└── requirements.txt
```

---

## Function Calling ツール（10種）

| # | ツール | 説明 |
|---|--------|------|
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
| + | Plugins | math / time / format / random |

---

## 開発時の注意事項

- APIを変更したら `cocoro-console` / `cocoro-website` 両フロントへの影響を確認
- Decision Graph のパイプライン順序は**絶対に変えない**
- シンクロ率 92% 超えで学習停止（Divergence Ceiling）するため意図的な設計
- LLMプロバイダーは `LLM_PROVIDER=gemini` or `ollama` で切替可能
- 本番デプロイ時は `FORCE_HTTPS=true` に設定すること

---

## 更新履歴

| 日付 | 更新内容 |
|------|---------|
| 2026-03-08 | 初版作成 |
