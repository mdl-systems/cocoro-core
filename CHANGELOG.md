# Changelog

すべての注目すべき変更はこのファイルに記載されます。  
フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠し、  
このプロジェクトは [Semantic Versioning](https://semver.org/lang/ja/) に従います。

---

## [1.0.0] - 2026-03-14

### Added

- Boot Wizard (40問人格設定)
- 6次元感情エンジン
- シンクロ率システム（余弦類似度）
- 10ツールFunction Calling
- 専門職エージェントロール（6種）
- ノード登録・発見API
- 音声転写・画面コンテキスト分析API
- Resendメール通知
- Cloudflare Tunnel対応
- セキュリティ強化（レート制限・IP Filter）
- 多言語対応（日本語・英語・中文）
- 131 APIエンドポイント
- 231テスト

### Details

#### Core Architecture
- **53 modules / 131 API endpoints / 24 DB tables / 231 tests**
- 11層アーキテクチャ（OS → Hardware → Infrastructure → Memory → Personality → Evolution → AI Brain → Agent → Organization → Governance → API Gateway → Dashboard）
- Decision Graph パイプライン（Memory → Value → Emotion → Decision）順序保証

#### Personality Engine
- 人格統合エンジン（Identity / Values / Emotion × 6次元 / Beliefs / Goals / Cognitive Profile）
- Boot Wizard：40問の初期設定ウィザード
- シンクロ率学習制御（< 70%: 加速1.5x / 70-85%: 通常1.0x / 85-92%: Creative Friction 0.3x / > 92%: Divergence Ceiling 停止）
- 人格クローン・バックアップ/復元エンジン
- マルチユーザー管理

#### Memory System
- 3層記憶システム（短期: Redis / 長期: PostgreSQL / ベクトル: pgvector）
- クロスセッション記憶検索 `memory_engine.build_context()`
- `/memory/search` `/memory/conversations` エンドポイント
- 自動メモリアーカイブ（24h サイクル）

#### AI Brain
- Function Calling 10ツール（search_memory / create_task / get_org_status / search_learnings / get_personality / get_current_time / web_search / add_schedule / list_schedules / list_recent_tasks）
- プラグインシステム（math / time / format / random）
- マルチモーダル対応（画像入力）
- LLMプロバイダー切替（`LLM_PROVIDER=gemini` or `ollama`）
- 自律思考エンジン（AutonomousThinker）

#### Emotion Engine
- 6次元感情モデル（happiness / sadness / anger / fear / trust / surprise）
- 感情自然減衰スケジューラ
- 感情→行動適応コンバーター（創造性 / リスク許容度 / 饒舌度 / 共感力）

#### Agent System
- 専門職エージェントロール（Dev / Sales / Marketing / Finance / Legal / HR）
- タスクルーター + Worker Manager（2並列）
- タスクキュー（Redis）+ イベントバス
- 組織管理・部署・エージェントレジストリ
- Webhook 通知（Discord/LINE 連携）
- メール通知エンジン（Resend / デイリーブリーフィング）

#### Node API
- ノード登録・発見 API（分散ノード管理）
- `/{node_id}/health` 死活確認エンドポイント

#### Voice & Multimodal
- 音声転写 API（Web Speech API 連携）
- 画面コンテキスト分析 API
- 感情→音声パラメータ変換

#### Security
- レート制限（slowapi）
- IP ホワイトリスト/ブラックリスト
- API キーローテーション（graceful period 24h）
- 監査ログ（governance_log テーブル）
- JWT + API Key デュアル認証
- ログイン試行制限・ロックアウト

#### Cloudflare Tunnel
- `scripts/setup-tunnel.sh`：自動セットアップスクリプト
- `infra/docker/docker-compose.prod.yml`：本番設定（FORCE_HTTPS=true, LOG_LEVEL=WARNING, リソース制限）
- `/health` に `tunnel_enabled` / `tunnel_url` / `local_url` フィールドを追加

#### Internationalization
- 多言語対応：日本語 / 英語 / 中文
- `/language/settings` API

#### Infrastructure
- FastAPI 0.109 + Nginx リバースプロキシ
- Docker Compose（開発 / 本番）
- 自動データベースマイグレーション
- JSON 構造化ログ（RotatingFileHandler / 50MB × 5世代）
- OpenAPI / Swagger UI（Bearer認証ボタン付き）
- `/health` ヘルスチェックエンドポイント（認証不要）

### Fixed

- `.env.example` インラインコメントによる `IP_WHITELIST` 全IPブロックバグ
- `/memory/stats` `/memory/archive` の `await` 抜け修正
- `nginx.conf` / `docker-compose.yml` に Nginx サービス追加

---

### Tech Stack

| Component | Version |
|-----------|---------|
| Python | 3.11 |
| FastAPI | 0.109 |
| PostgreSQL + pgvector | 16 |
| Redis | 7 |
| Google Gemini | 2.5 Flash Lite |
| Docker Compose | v2 |

---

## [0.x.x] — 開発フェーズ

開発中の Changelog は Git コミット履歴を参照してください。

---

[1.0.0]: https://github.com/mdl-systems/cocoro-core/releases/tag/v1.0.0
