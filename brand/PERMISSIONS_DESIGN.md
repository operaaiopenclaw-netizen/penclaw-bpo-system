# Hierarquia de Permissões · Proposta de Arquitetura

**Gap identificado:** o modelo atual tem 5 roles planos (`admin`, `manager`, `finance`, `operator`, `kitchen`) aplicados em escopo global. Isso NÃO cobre:

- Departamentos com cargos internos (ex.: Gerente de Vendas × Vendedor × SDR)
- Limitação por recurso (ex.: vendedor só vê seus próprios leads)
- Escopo geográfico ou por unidade (multi-filial)
- Operações proibidas mesmo para quem "vê" (ex.: operator vê OP mas não aprova)

Sim, você tinha pensado nisso e está correto — essa arquitetura não existe hoje.

---

## Modelo proposto (RBAC hierárquico + ABAC)

### 1. Novas entidades Prisma

```prisma
model Department {
  id          String   @id @default(uuid())
  tenantId    String
  slug        String   // 'sales', 'kitchen', 'finance', 'ops'
  name        String
  description String?
  createdAt   DateTime @default(now())

  positions   Position[]
  @@unique([tenantId, slug])
}

model Position {
  id           String  @id @default(uuid())
  departmentId String
  slug         String  // 'sales-manager', 'seller', 'sdr'
  name         String
  level        Int     // 1=top, 5=bottom (hierarquia)
  parentId     String? // position acima na cadeia

  department   Department @relation(fields:[departmentId], references:[id])
  parent       Position?  @relation("PositionParent", fields:[parentId], references:[id])
  children     Position[] @relation("PositionParent")

  permissions  PositionPermission[]
  members      UserPosition[]

  @@unique([departmentId, slug])
}

model Permission {
  id          String @id @default(uuid())
  resource    String // 'lead', 'proposal', 'invoice', 'op', 'user'
  action      String // 'read', 'create', 'update', 'delete', 'approve'
  scope       String // 'own', 'department', 'tenant', 'global'
  description String?

  @@unique([resource, action, scope])
}

model PositionPermission {
  id           String @id @default(uuid())
  positionId   String
  permissionId String
  position     Position   @relation(fields:[positionId], references:[id])
  permission   Permission @relation(fields:[permissionId], references:[id])

  @@unique([positionId, permissionId])
}

model UserPosition {
  id         String   @id @default(uuid())
  userId     String
  positionId String
  assignedAt DateTime @default(now())
  assignedBy String?

  user     User     @relation(fields:[userId], references:[id])
  position Position @relation(fields:[positionId], references:[id])

  @@unique([userId, positionId])
}
```

### 2. Convenção de permissões

Formato: `{resource}:{action}:{scope}`

| Resource | Actions | Scopes |
|---|---|---|
| `lead` | read, create, update, delete, assign | own, department, tenant |
| `proposal` | read, create, update, send, approve, discount | own, department, tenant |
| `invoice` | read, create, issue, void | own, department, tenant |
| `op` | read, create, update, approve, execute | own, department, tenant |
| `user` | read, create, update, deactivate | department, tenant |
| `report` | read, export | department, tenant |

`own` = apenas recursos onde o user é owner/criador
`department` = todos do mesmo departamento
`tenant` = tudo no tenant
`global` = apenas super-admins

### 3. Exemplo de configuração: departamento Vendas

```yaml
department: sales
positions:
  - slug: sales-director
    level: 1
    permissions:
      - lead:*:tenant
      - proposal:*:tenant
      - report:read:tenant
      - report:export:tenant
      - user:update:department

  - slug: sales-manager
    level: 2
    parent: sales-director
    permissions:
      - lead:*:department
      - proposal:read:department
      - proposal:approve:department   # aprova desconto >10%
      - proposal:create:own
      - report:read:department

  - slug: seller
    level: 3
    parent: sales-manager
    permissions:
      - lead:read:own
      - lead:update:own
      - lead:create:own
      - proposal:create:own
      - proposal:read:own
      - proposal:send:own
      - proposal:discount:own    # até 10% (limite configurável)

  - slug: sdr
    level: 4
    parent: sales-manager
    permissions:
      - lead:create:own
      - lead:read:own
      - lead:update:own
      # NÃO pode criar proposta — apenas qualifica
```

### 4. Seed de departamentos default (por tenant)

Ao criar novo tenant (novo cliente contratando Orkestra), sistema semeia:

- **Vendas**: director, manager, seller, sdr
- **Operações**: ops-director, ops-manager, coordinator, operator
- **Cozinha**: chef, sous-chef, line-cook, prep-cook
- **Financeiro**: cfo, controller, analyst, assistant
- **Administrativo**: admin, hr, assistant

Cliente pode customizar (adicionar/remover cargos, editar permissões) pela tela **Usuários → Departamentos**.

### 5. Enforcement no backend

Middleware Fastify `requirePermission(resource, action, scope)`:

```typescript
fastify.post('/leads', {
  preHandler: requirePermission('lead', 'create', 'own')
}, async (req, reply) => { ... });
```

Checa:
1. User tem permission `lead:create:own|department|tenant`?
2. Se `scope=own`, grava `ownerId = user.id` na criação.
3. Em `GET`, injeta filtros SQL baseados no scope.

### 6. UI Impact

- Tela nova: **Organograma** (admin) — drag-drop para reorganizar cargos
- Tela nova: **Permissões** (admin) — matriz resource×action por position
- NAV passa a filtrar por permissão (não mais `roles.includes(ME.role)`)
- Listas filtram automaticamente por scope (vendedor vê só seus leads)

### 7. Migração do estado atual

- Usuários existentes mantêm o `role` como "legacy role" (não some).
- Script de migração mapeia role→position default do primeiro departamento correspondente.
- Permissions antigas (hard-coded) continuam até cada endpoint ser migrado para `requirePermission()`.

---

## Escopo / Esforço

| Fase | Entrega | Tempo |
|---|---|---|
| 1 | Schema + seed + migração | 1 dia |
| 2 | Middleware + 5 endpoints migrados (leads, proposals, invoices, ops, users) | 2 dias |
| 3 | UI organograma + permissões | 2 dias |
| 4 | Migrar restantes endpoints + testes | 2 dias |
| 5 | Ajuste fino + documentação | 1 dia |

**Total: ~8 dias** para sistema completo hierárquico com UI.

---

## Recomendação

Esta é uma **reescrita arquitetural** — deve ser um marco próprio, não misturado com as 7 features novas que estão em construção. Proponho:

1. **Agora:** terminar as 7 features + deploy + logo D
2. **Próximo sprint:** este RBAC hierárquico como prioridade única
3. **Antes do primeiro cliente enterprise:** este sistema tem que estar pronto (enterprise vai pedir)

Se quiser acelerar, posso começar Fase 1+2 imediatamente em paralelo.
