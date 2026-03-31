# 🚀 Backend Node.js - Openclaw API

## 📁 Estrutura

```
src/
├── config/
│   └── env.ts          # Configurações com Zod validation
├── routes/
│   ├── index.ts        # Barrel exports
│   ├── agent-runs.ts   # /agent-runs
│   ├── approvals.ts    # /approvals/:id/approve|reject
│   ├── memory.ts       # /memory
│   ├── artifacts.ts    # /artifacts
│   └── dashboard.ts    # /dashboard/*
├── utils/
│   ├── logger.ts       # Pino + JSON
│   ├── app-error.ts    # Error classes
│   └── error-handler.ts # Fastify error handler
├── db.ts               # Prisma client
└── server.ts           # Entry point
```

## 🛠️ Setup

```bash
npm install
npx prisma migrate dev      # Setup DB
npm run dev                 # Start server
```

## 📊 Endpoints

| Method | Endpoint | Descrição |
|--------|----------|-----------|
| POST | /agent-runs | Criar execução |
| GET | /agent-runs/:id | Buscar execução |
| POST | /agent-runs/:id/replay | Re-executar |
| POST | /approvals/:id/approve | Aprovar |
| POST | /approvals/:id/reject | Rejeitar |
| POST | /memory | Criar memória |
| GET | /memory/search | Buscar memória |
| POST | /artifacts/render | Renderizar artefato |
| GET | /artifacts/:id | Baixar artefato |
| GET | /dashboard/ceo | Dashboard CEO |
| GET | /dashboard/commercial | Comercial |
| GET | /dashboard/finance | Financeiro |
| GET | /dashboard/operations | Operações |
| GET | /health | Health check |
| GET | /docs | Swagger UI |

## 🏃 Comandos

```bash
npm run dev          # Dev com hot-reload
npm run build        # Compilar
npm start            # Produção
npm run lint         # ESLint
npm run format       # Prettier
```

## 📦 Tech Stack

- **Fastify** - Web framework
- **Prisma** - ORM
- **Zod** - Validation
- **Pino** - Logging
- **TypeScript** - Types

## 🌐 Acesso

- API: http://localhost:3333
- Docs: http://localhost:3333/docs
