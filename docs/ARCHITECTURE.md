# cocoro-core — Personality AI Operating System

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Layer 8: External Interface                             │
│  ┌──────────┐                                           │
│  │ FastAPI   │  POST /think  POST /decide  POST /chat   │
│  │  :8000    │  GET /memory  GET /identity  GET /health  │
│  └─────┬────┘                                           │
├────────┼────────────────────────────────────────────────┤
│ Layer 7: Agent Execution                                │
│  ┌─────▼────┐  ┌──────────────┐                        │
│  │Task      │  │Worker        │                        │
│  │Router    │→ │Manager       │→ [Dev/Sales/Marketing] │
│  └──────────┘  └──────────────┘                        │
├─────────────────────────────────────────────────────────┤
│ Layer 6: Memory                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐         │
│  │Short-Term│  │Long-Term │  │Vector Memory │         │
│  │ (Redis)  │  │ (Postgres)│  │ (Postgres)   │         │
│  └──────────┘  └──────────┘  └──────────────┘         │
├─────────────────────────────────────────────────────────┤
│ Layer 5: Personality                                    │
│  ┌────────┐ ┌───────┐ ┌────────┐ ┌─────────┐         │
│  │Identity│ │Values │ │Beliefs │ │History  │         │
│  │Engine  │ │System │ │System  │ │Tracker  │         │
│  └────┬───┘ └───┬───┘ └───┬────┘ └────┬────┘         │
│       └─────────┴─────────┴────────────┘               │
│                 Personality Engine                       │
│          (人格の一貫性を保証するコア)                     │
├─────────────────────────────────────────────────────────┤
│ Layer 4: AI Brain                                       │
│  ┌───────────┐  ┌─────────┐  ┌──────────────┐         │
│  │Reasoning  │  │Planner  │  │Decision      │         │
│  │Engine     │  │         │  │Graph         │         │
│  │(思考連鎖)  │  │(計画生成)│  │(判断木構築)   │         │
│  └───────────┘  └─────────┘  └──────────────┘         │
├─────────────────────────────────────────────────────────┤
│ Layer 3: Runtime  (Docker / Python 3.11)                │
│ Layer 2: OS       (Debian 13)                           │
│ Layer 1: Hardware (miniPC: N95 / 16GB / 512GB SSD)      │
└─────────────────────────────────────────────────────────┘
```

## Core Philosophy

**人格 = Identity + Memory + Values + Reasoning**

LLMは「道具」であり、人格OSの「声帯」に過ぎない。
人格の一貫性は、LLMの外側（Memory + Values + Decision Graph）で保証する。

## Data Flow

```
User Input
  │
  ▼
Reasoning Engine  ← Personality Engine (価値観・信念フィルタ)
  │                ← Memory Engine (過去の経験・判断)
  ▼
Decision Graph    ← Value System (判断基準の重み付け)
  │
  ▼
Response / Task Dispatch
  │
  ▼
Memory Storage    → Learning (経験として蓄積)
```
