# =============================================================
# Orkestra API — production image (Node 20, Alpine)
# Build: docker build -t orkestra/api:latest .
# Run:   docker run -p 3010:3010 --env-file .env orkestra/api:latest
# =============================================================

# ---- deps (all deps, used by build stage) ----
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat openssl
WORKDIR /app
COPY package*.json ./
COPY schema.prisma ./schema.prisma
RUN npm ci --include=dev

# ---- build (compile TS + generate Prisma client) ----
FROM node:20-alpine AS builder
RUN apk add --no-cache libc6-compat openssl
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npx prisma generate --schema=./schema.prisma
RUN npm run build

# ---- runner (production) ----
FROM node:20-alpine AS runner
RUN apk add --no-cache libc6-compat openssl curl
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3010

# Non-root runtime user
RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 apiuser

# Production-only node_modules (smaller image)
COPY package*.json ./
RUN npm ci --omit=dev && npm cache clean --force

# Copy build artifacts + Prisma assets the runtime needs
COPY --from=builder --chown=apiuser:nodejs /app/dist ./dist
COPY --from=builder --chown=apiuser:nodejs /app/node_modules/.prisma ./node_modules/.prisma
COPY --from=builder --chown=apiuser:nodejs /app/node_modules/@prisma ./node_modules/@prisma
COPY --from=builder --chown=apiuser:nodejs /app/schema.prisma ./schema.prisma
COPY --from=builder --chown=apiuser:nodejs /app/prisma ./prisma
COPY --from=builder --chown=apiuser:nodejs /app/dashboard ./dashboard
COPY --from=builder --chown=apiuser:nodejs /app/docs ./docs

USER apiuser
EXPOSE 3010

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:${PORT}/ready || exit 1

# Apply Prisma migrations before starting. `prisma` is in `dependencies`
# so it's present in the runtime image after `npm ci --omit=dev`.
CMD ["sh", "-c", "npx prisma migrate deploy --schema=./schema.prisma && node dist/server.js"]
