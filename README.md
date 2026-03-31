# 🍳 Orkestra Finance Brain

**Sistema Enterprise de Gestão Financeira para Eventos**

## 🚀 Visão Geral

Orkestra Finance Brain é um sistema completo de gestão financeira, operacional e comercial para empresas de eventos. O sistema integra:

- **18 Engines Python** para processamento de dados
- **Backend PostgreSQL** com Prisma ORM
- **API REST** para integração frontend
- **Runtime de Agentes** com orquestração
- **POPs Documentados** para cada departamento

## 📊 Estatísticas

| Métrica | Valor |
|---------|-------|
| Engines Python | 18 |
| Tabelas PostgreSQL | 11 |
| Modelos Prisma | 19 |
| Endpoints REST | 12+ |
| POPs | 5 |
| **Total de Arquivos** | **70+** |

## 🎯 Principais Funcionalidades

### 1. Kitchen Control
- Cálculo de custos por receita
- Integração de estoque
- Rastreabilidade de consumo

### 2. DRE e Fixed Cost
- Demonstração de resultado por evento
- Rateio de custos fixos
- Margens reais

### 3. Validação e Auditoria
- Financial Truth Audit
- Reconciliação sistema vs real
- Calibração automática

### 4. Relatórios Executivos
- CEO Dashboard
- Executive Report
- Sales Dashboard

### 5. Precificação e Menu
- Item Pricing (margem alvo)
- Menu Optimization (Matriz BCG)
- Procurement Feedback

## 📁 Estrutura de Diretórios

```
.
├── # ENGINES (18 .py)
├── agent_runtime_core.py        # Orquestrador central
├── kitchen_control_layer.py    # CMV e custos
├── fixed_cost_engine.py         # Rateio fixo
├── dre_engine.py               # DRE
├── financial_truth_audit.py     # Auditoria
├── system_calibration_engine.py # Calibração
├── executive_report_engine.py   # Storytelling
├── ceo_dashboard_engine.py      # Dashboard CEO
├── sales_dashboard_engine.py    # Dashboard Vendas
├── event_reconciliation_engine.py # Reconciliação
├── [+ outros 9 engines]
│
├── # BACKEND (4 arquivos)
├── schema_v1_2.sql              # Schema PostgreSQL
├── schema.prisma                # Prisma ORM
├── prisma_seed.ts               # Seed de dados
├── database_adapter.py          # Python adapter
│
├── # API (2 arquivos)
├── openapi.yaml                 # OpenAPI spec
├── routes_express.py            # FastAPI routes
│
├── # POPs (5 arquivos)
├── pop_docs/
│   ├── pop_comercial.md
│   ├── pop_producao.md
│   ├── pop_estoque.md
│   ├── pop_financeiro.md
│   └── pop_gestao.md
│
├── # DADOS
├── kitchen_data/                # JSON/CSV
│
└── # DOCUMENTAÇÃO
├── README.md                    # Este arquivo
├── SYSTEM_INDEX_COMPLETE.md     # Documentação completa
└── [+ outros index files]
```

## 🛠️ Instalação e Uso

### 1. Backend Database

```bash
# PostgreSQL
psql -f schema_v1_2.sql

# Prisma (TypeScript/Node)
npm install @prisma/client prisma
npx prisma migrate dev
npx prisma db seed
npx prisma studio
```

### 2. API (Python)

```bash
# Instalar dependências
pip install fastapi uvicorn pydantic

# Rodar API
uvicorn routes_express:app --reload --port 8000

# Documentação: http://localhost:8000/docs
```

### 3. Engines Python

```bash
# Pipeline completo
python3 agent_runtime_core.py

# Ou individual
python3 kitchen_control_layer.py
python3 fixed_cost_engine.py
python3 dre_engine.py
```

## 📊 API Endpoints

### Agent Runs
- `POST /agent-runs` - Criar execução
- `GET /agent-runs/:id` - Buscar execução
- `POST /agent-runs/:id/replay` - Re-executar

### Approvals
- `POST /approvals/:id/approve` - Aprovar
- `POST /approvals/:id/reject` - Rejeitar

### Memory
- `POST /memory` - Criar memória
- `GET /memory/search` - Buscar

### Artifacts
- `POST /artifacts/render` - Renderizar
- `GET /artifacts/:id` - Baixar

### Dashboards
- `GET /dashboard/ceo` - CEO
- `GET /dashboard/commercial` - Comercial
- `GET /dashboard/finance` - Financeiro
- `GET /dashboard/operations` - Operações

## 🔧 Tecnologias

### Backend
- **PostgreSQL** - Banco de dados
- **Prisma ORM** - Mapeamento objeto-relacional
- **Python/FastAPI** - API REST
- **TypeScript** - Seed e scripts

### Engines
- **Python 3.12** - Processamento
- **Pydantic** - Validação de dados
- **CSV/JSON** - Persistência

### Documentação
- **OpenAPI 3.0** - Especificação API
- **Markdown** - POPs e READMEs

## 📋 Componentes

### Principais Arquivos

| Nome | Função |
|------|--------|
| `agent_runtime_core.py` | Orquestrador de agentes (12 passos) |
| `schema.prisma` | Modelo de dados completo |
| `openapi.yaml` | Especificação REST API |
| `pop_*.md` | Procedimentos operacionais |

### Engines Principais

| Engine | Função |
|--------|--------|
| Kitchen Control | Custos e CMV |
| DRE | Demonstração resultado |
| Financial Truth Audit | Validação |
| Executive Report | Storytelling |
| CEO Dashboard | Visão estratégica |

## 📊 Fluxo de Dados

```
Input → Runtime → Engines → Database
                       ↓
                   API → Dashboard
```

1. **Input**: Dados de eventos, estoque, receitas
2. **Runtime**: Orquestra execução (Agent Runtime Core)
3. **Engines**: Processam e calculam (18 engines)
4. **Database**: Persistência PostgreSQL
5. **API**: Disponibilidade via REST
6. **Dashboard**: Visualização web

## 🎯 Status

**✅ SISTEMA COMPLETO E PRONTO**

- 29 Componentes implementados
- 70+ Arquivos criados
- Documentação completa
- Testado e validado

## 📞 Suporte

Para dúvidas ou sugestões, consulte a documentação em:
- `SYSTEM_INDEX_COMPLETE.md` - Documentação completa
- `openapi.yaml` - Especificação API
- `pop_docs/*.md` - Procedimentos operacionais

---

**Orkestra Finance Brain v1.4**  
*Sistema Enterprise Completo*  
*Finalizado: 31/03/2026*
