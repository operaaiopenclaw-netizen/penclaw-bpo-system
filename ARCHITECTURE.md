# 🎛️ Orkestra Finance Brain - System Architecture

## Overview

Complete financial and operational management system for event-based catering businesses.

## Stats

| Component | Count |
|-----------|-------|
| Engines | 18+
| API Endpoints | 12+ |
| Database Tables | 11 |
| Tools | 3+ |
| Total Files | 80+ |

## Core Layers

### 1. Frontend (TUI/Web)
```
React App → WebSocket/HTTP → API
```

### 2. Backend API (TypeScript/Fastify)
```
Routes → Services → Runtime → Database
```

### 3. Runtime Engine
```
Policy Check → Worker → Execution → Tools
```

### 4. Python Engines
```
Kitchen → Fixed Cost → DRE → Audit
```

### 4. Database Layer
```
PostgreSQL + Prisma ORM
```

## Data Flow

```
User Input → API → Runtime Core
                    │
                    ├─→ Policy Engine: R0-R5
                    │
                    ├─→ Memory Load
                    │
                    ├─→ Worker Service
                    │     ├─→ Tool Calls
                    │     └─→ Python Engines
                    │
                    ├─→ Quality Check
                    │
                    └─→ Response
```

## Policy Risk Levels

| Level | Code | Action |
|-------|------|--------|
| Read | R0 | Auto-execute |
| Safe Write | R1 | Auto-execute |
| External | R2 | Log required |
| Financial | R3 | Approval |
| Destructive | R4 | Blocked |

## Tool Registry

| Tool | Risco | Propósito |
|------|-------|-----------|
| event_analyzer | R0 | Event metrics |
| calculator | R0 | Math operations |
| recipe_cost | R1 | Recipe pricing |

## File Organization

```
src/
├── config/        # Environment, env vars
├── core/          # Policy engine  
├── db/            # Prisma client
├── runtime/       # Worker, execution
├── tools/         # Tool implementations
├── routes/        # API routes
├── types/         # TypeScript types
└── utils/         # Logger, errors

engines/           # Python modules
├── kitchen/
├── financial/
└── decision/

kitchen_data/      # Data storage
output/           # Generated files
pop_docs/         # Documentation
```

## Deployment

```bash
# Dev
npm run dev

# Production  
docker-compose up -d

# Migration
npx prisma migrate deploy
```
