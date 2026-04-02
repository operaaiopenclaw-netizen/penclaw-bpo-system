# 🎯 ETAPA 2 - PROMPTS 2.37 A 2.56

**Status:** Em progresso  
**Último prompt recebido:** 2.47  
**Progresso:** 11/20 prompts  
**Faltam:** 2.48 a 2.56 (9 prompts)  

---

## Prompts Recebidos

### 2.37 ✅ APPROVAL SERVICE
```typescript
import { prisma } from "../../database/prisma";
import { AppError } from "../../shared/errors/app-error";

export class ApprovalService {
 async approve(id: string, approvedBy: string) {
   const approval = await prisma.approvalRequest.findUnique({ where: { id } });
   if (!approval) throw new AppError("Approval not found", 404);

   return prisma.approvalRequest.update({
     where: { id },
     data: {
       status: "approved",
       approvedBy,
       approvedAt: new Date()
     }
   });
 }

 async reject(id: string, approvedBy: string) {
   const approval = await prisma.approvalRequest.findUnique({ where: { id } });
   if (!approval) throw new AppError("Approval not found", 404);

   return prisma.approvalRequest.update({
     where: { id },
     data: {
       status: "rejected",
       approvedBy,
       approvedAt: new Date()
     }
   });
 }
}
```

---

### 2.38 ✅ APPROVAL CONTROLLER
```typescript
import { FastifyReply, FastifyRequest } from "fastify";
import { ApprovalService } from "./service";

const service = new ApprovalService();

export class ApprovalController {
 async approve(
 request: FastifyRequest<{ Params: { id: string }; Body: { approvedBy: string } }>,
 reply: FastifyReply
 ) {
 const result = await service.approve(request.params.id, request.body.approvedBy);
 return reply.status(200).send(result);
 }

 async reject(
 request: FastifyRequest<{ Params: { id: string }; Body: { approvedBy: string } }>,
 reply: FastifyReply
 ) {
 const result = await service.reject(request.params.id, request.body.approvedBy);
 return reply.status(200).send(result);
 }
}
```

---

### 2.39 ✅ APPROVAL ROUTES
```typescript
import { FastifyInstance } from "fastify";
import { ApprovalController } from "./controller";

const controller = new ApprovalController();

export async function approvalRoutes(app: FastifyInstance) {
 app.post("/approvals/:id/approve", controller.approve);
 app.post("/approvals/:id/reject", controller.reject);
}
```

---

### 2.40 ✅ MEMORY SERVICE
```typescript
import { prisma } from "../../database/prisma";

export class MemoryService {
 async create(data: {
 companyId: string;
 memoryType: string;
 title: string;
 content: string;
 tags?: string[];
 }) {
 return prisma.memoryItem.create({
 data: {
 companyId: data.companyId,
 memoryType: data.memoryType,
 title: data.title,
 content: data.content,
 tags: data.tags || []
 }
 });
 }

 async search(companyId: string, q: string) {
 return prisma.memoryItem.findMany({
 where: {
 companyId,
 OR: [
 { title: { contains: q, mode: "insensitive" } },
 { content: { contains: q, mode: "insensitive" } }
 ]
 },
 orderBy: { createdAt: "desc" },
 take: 20
 });
 }
}
```

---

### 2.41 ✅ MEMORY CONTROLLER
```typescript
import { FastifyReply, FastifyRequest } from "fastify";
import { MemoryService } from "./service";

const service = new MemoryService();

export class MemoryController {
 async create(
 request: FastifyRequest<{
 Body: {
 companyId: string;
 memoryType: string;
 title: string;
 content: string;
 tags?: string[];
 };
 }>,
 reply: FastifyReply
 ) {
 const result = await service.create(request.body);
 return reply.status(201).send(result);
 }

 async search(
 request: FastifyRequest<{ Querystring: { companyId: string; q: string } }>,
 reply: FastifyReply
 ) {
 const result = await service.search(request.query.companyId, request.query.q);
 return reply.status(200).send(result);
 }
}
```

---

### 2.42 ✅ MEMORY ROUTES
```typescript
import { FastifyInstance } from "fastify";
import { MemoryController } from "./controller";

const controller = new MemoryController();

export async function memoryRoutes(app: FastifyInstance) {
 app.post("/memory", controller.create);
 app.get("/memory/search", controller.search);
}
```

---

### 2.43 ✅ ARTIFACT SERVICE
```typescript
import { prisma } from "../../database/prisma";
import { env } from "../../config/env";
import fs from "fs/promises";
import path from "path";
import crypto from "crypto";

export class ArtifactService {
 async renderTextArtifact(data: {
 agentRunId: string;
 artifactType: string;
 fileName: string;
 content: string;
 }) {
 await fs.mkdir(env.ARTIFACTS_DIR, { recursive: true });

 const fullPath = path.join(env.ARTIFACTS_DIR, data.fileName);
 await fs.writeFile(fullPath, data.content, "utf-8");

 const checksum = crypto.createHash("sha256").update(data.content).digest("hex");

 return prisma.artifact.create({
 data: {
 agentRunId: data.agentRunId,
 artifactType: data.artifactType,
 fileName: data.fileName,
 storageUrl: fullPath,
 checksum,
 version: 1
 }
 });
 }
}
```

---

### 2.44 ✅ ARTIFACT CONTROLLER
```typescript
import { FastifyReply, FastifyRequest } from "fastify";
import { ArtifactService } from "./service";

const service = new ArtifactService();

export class ArtifactController {
 async create(
 request: FastifyRequest<{
 Body: {
 agentRunId: string;
 artifactType: string;
 fileName: string;
 content: string;
 };
 }>,
 reply: FastifyReply
 ) {
 const result = await service.createArtifact(request.body);
 return reply.status(201).send(result);
 }
}
```

### 2.45 ✅ ARTIFACT ROUTES
```typescript
import { FastifyInstance } from "fastify";
import { ArtifactController } from "./controller";

const controller = new ArtifactController();

export async function artifactRoutes(app: FastifyInstance) {
 app.post("/artifacts/render", controller.render);
}
```

---

### 2.46 ✅ DASHBOARD SERVICE
```typescript
import { prisma } from "../../database/prisma";

export class DashboardService {
 async ceo(companyId: string) {
 const runs = await prisma.agentRun.findMany({
 where: { companyId },
 orderBy: { createdAt: "desc" },
 take: 50
 });

 return {
 totalRuns: runs.length,
 completedRuns: runs.filter(r => r.status === "completed").length,
 failedRuns: runs.filter(r => r.status === "failed").length,
 waitingApproval: runs.filter(r => r.status === "waiting_approval").length,
 totalCost: runs.reduce((acc, item) => acc + (item.totalCost || 0), 0)
 };
 }
}
```

---

### 2.47 ✅ DASHBOARD CONTROLLER
```typescript
import { FastifyReply, FastifyRequest } from "fastify";
import { DashboardService } from "./service";

const service = new DashboardService();

export class DashboardController {
 async ceo(
 request: FastifyRequest<{ Querystring: { companyId: string } }>,
 reply: FastifyReply
 ) {
 const result = await service.ceo(request.query.companyId);
 return reply.status(200).send(result);
 }
}
```

---

### 2.49 ✅ ROUTE INDEX
```typescript
import { FastifyInstance } from "fastify";
import { agentRunRoutes } from "../modules/agent-runs/routes";
import { approvalRoutes } from "../modules/approvals/routes";
import { memoryRoutes } from "../modules/memory/routes";
import { artifactRoutes } from "../modules/artifacts/routes";
import { dashboardRoutes } from "../modules/dashboards/routes";

export async function registerRoutes(app: FastifyInstance) {
 await agentRunRoutes(app);
 await approvalRoutes(app);
 await memoryRoutes(app);
 await artifactRoutes(app);
 await dashboardRoutes(app);
}
```

---

⚠️ **NOTA:** Prompt **2.48** (DASHBOARD ROUTES) ainda não recebido!

### 2.50 ✅ APP
```typescript
import Fastify from "fastify";
import { registerRoutes } from "./routes";
import { errorHandler } from "./shared/errors/error-handler";

export async function buildApp() {
 const app = Fastify();

 app.setErrorHandler(errorHandler);

 app.get("/health", async () => {
 return { status: "ok" };
 });

 await registerRoutes(app);

 return app;
}
```

---

⚠️ **PENDENTE:** Prompt **2.48** (DASHBOARD ROUTES) ainda não recebido!

### 2.51 ✅ SERVER
```typescript
import { buildApp } from "./app";
import { env } from "./config/env";
import { logger } from "./shared/utils/logger";
import { ToolRegistry } from "./core/tools/registry";
import { FileReadTool } from "./core/tools/implementations/file-read";
import { FileWriteTool } from "./core/tools/implementations/file-write";
import { SqlQueryTool } from "./core/tools/implementations/sql-query";
import { HttpRequestTool } from "./core/tools/implementations/http-request";
import { StorageUploadTool } from "./core/tools/implementations/storage-upload";

async function bootstrap() {
 const registry = new ToolRegistry();
 registry.register(new FileReadTool());
 registry.register(new FileWriteTool());
 registry.register(new SqlQueryTool());
 registry.register(new HttpRequestTool());
 registry.register(new StorageUploadTool());

 globalThis.__toolRegistry = registry;

 const app = await buildApp();

 await app.listen({ port: env.PORT, host: "0.0.0.0" });

 logger.info(`OpenClaw API running on port ${env.PORT}`, {
 tools: registry.list()
 });
}

bootstrap().catch((error) => {
 logger.error("Failed to bootstrap server", {
 error: error instanceof Error ? error.message : "Unknown error"
 });
 process.exit(1);
});
```

---

⚠️ **PENDENTE:** Prompt **2.48** (DASHBOARD ROUTES) ainda não recebido!

### 2.52 ✅ COMANDOS DE SETUP
```bash
mkdir -p apps/api
cd apps/api

npm init -y
npm install fastify fastify-plugin zod dotenv @prisma/client uuid
npm install -D typescript ts-node-dev prisma @types/node

npx prisma init

mkdir -p src/config src/database src/modules/agent-runs src/modules/approvals src/modules/memory src/modules/artifacts src/modules/dashboards
mkdir -p src/core/runtime src/core/policy src/core/memory src/core/tools/implementations src/core/agents
mkdir -p src/shared/errors src/shared/utils src/shared/types src/routes
```

---

### 2.53 ✅ COMANDOS PRISMA
```bash
npx prisma generate
npx prisma migrate dev --name init_openclaw_core
```

---

⚠️ **PENDENTE:** Prompt **2.48** (DASHBOARD ROUTES) ainda não recebido!

**Próximo:** 2.54 (aguardando...)
