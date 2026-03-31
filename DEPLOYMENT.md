# 🚀 Orkestra Finance Brain - Deployment Guide

## Quick Start

```bash
# 1. Clone
git clone <repo>
cd workspace-openclaw-bpo

# 2. Config
npm install
npx prisma migrate dev

# 3. Run
docker-compose up -d

# 4. Test
curl http://localhost:3333/health
```

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │───→│   Node.js   │───→│ PostgreSQL  │
│  (React/TUI)│    │   API       │    │   Database  │
└─────────────┘    └──────┬──────┘    └─────────────┘
                          │
                    ┌─────┴─────┐
                    │ Python    │
                    │ Engines   │
                    └───────────┘
```

## Services

| Service | Port | Image |
|---------|------|-------|
| API | 3333 | openclaw-api |
| Database | 5432 | postgres:15-alpine |
| Engines | - | openclaw-engines |
| Python Runtime | - | python:3.11-slim |

## Environment Variables

```bash
NODE_ENV=production
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/openclaw
PORT=3333
JWT_SECRET=your-secret-here
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Database not ready | Wait for healthcheck: `docker-compose ps` |
| Schema not applied | Run `npx prisma migrate deploy` |
| Engines fail | Check Python deps: `pip install -r requirements.txt` |
| Port 3333 busy | Change PORT in .env |

## Production Checklist

- [ ] Change all default passwords
- [ ] Set JWT_SECRET (min 32 chars)
- [ ] Configure SSL/TLS
- [ ] Set up monitoring (Sentry)
- [ ] Configure backups
- [ ] Enable rate limiting
