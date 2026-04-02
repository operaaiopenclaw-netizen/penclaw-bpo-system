# AGENTS.md - Procedimento de Auto-Load Memory

**Atualizado:** 2026-04-01  
**Versão:** 1.0  
**Status:** ATIVO

---

## 1. AO INICIAR (Startup Sequence)

### 1.1 Escanear Diretório Base
```
~/.openclaw/workspace-openclaw-bpo/.openclaw/
```

### 1.2 Pastas Obrigatórias
- `financial/` - Dados financeiros
- `procurement/` - Compras e provisionamento
- `inventory/` - Controle de estoque
- `production/` - Eventos e produção
- `agents/` - Configurações de agentes

---

## 2. ARQUIVOS DE CARGA PRIORITÁRIA

### 2.1 Financial (Obrigatórios)
| Arquivo | Dados |
|---------|-------|
| `accounts_payable.json` | Contas a pagar |
| `accounts_receivable.json` | Contas a receber |
| `cashflow_projection.json` | Projeção de fluxo |
| `cash_position.json` | Posição de caixa |
| `resumo_executivo.md` | Análise consolidada |

### 2.2 Procurement
| Arquivo | Dados |
|---------|-------|
| `purchase_orders.json` | Ordens de compra |
| `suppliers.json` | Fornecedores |
| `contracts.json` | Contratos ativos |

### 2.3 Inventory
| Arquivo | Dados |
|---------|-------|
| `stock.json` | Estoque atual |
| `movements.json` | Movimentações |
| `alerts.json` | Alertas de estoque |

### 2.4 Production
| Arquivo | Dados |
|---------|-------|
| `events.json` | Eventos ativos |
| `deliverables.json` | Entregáveis |
| `crew.json` | Equipes |

---

## 3. RECONSTRUÇÃO DE ESTADO

### 3.1 Ordens de Carregamento
```
1. cash_position.json        → Posição atual
2. accounts_receivable.json  → Entradas
3. accounts_payable.json    → Saídas
4. cashflow_projection.json  → Projeções
5. *.json restantes          → Dados operacionais
```

### 3.2 Validações Obrigatórias
- ✅ Todos os JSONs são válidos?
- ✅ Datas estão coerentes?
- ✅ Saldos batem (recebidos - pagos = caixa)?
- ✅ Alertas críticos identificados?

### 3.3 Se Falhar
- Logar erro em `~/.openclaw/workspace-openclaw-bpo/.openclaw/errors/`
- Notificar: "Dados incompletos - validação necessária"
- NÃO operar com dados parciais

---

## 4. ATUALIZAÇÃO DE MEMORY.md

Após carregamento bem-sucedido:

```markdown
## Último Snapshot
- **Data:** YYYY-MM-DD HH:mm:ss
- **Fonte:** ~/.openclaw/workspace-openclaw-bpo/.openclaw/
- **Arquivos carregados:** [lista]
- **Status:** OK | ERRO | PARCIAL
- **Alertas:** [se houver]
```

---

## 5. REGRAS DE OURO

⚠️ **NUNCA INICIAR VAZIO**
- Se não houver dados, solicitar fonte antes de operar

⚠️ **SEMPRE CARREGAR DADOS EXISTENTES**
- Prioridade: arquivos mais recentes (timestamp)
- Fallback: último backup disponível

⚠️ **SEMPRE VALIDAR CONSISTÊNCIA**
- Cross-check: recebimentos vs pagamentos vs caixa
- Alertas automáticos para divergências > 5%

⚠️ **SEMPRE DOCUMENTAR**
- Atualizar MEMORY.md após cada carga
- Registrar erros e inconsistências

---

## 6. COMANDO DE CHECAGEM RÁPIDA

```bash
# Verificar estrutura completa:
ls -la ~/.openclaw/workspace-openclaw-bpo/.openclaw/*/

# Contar arquivos por categoria:
find ~/.openclaw/workspace-openclaw-bpo/.openclaw/ -name "*.json" | wc -l
```

---

🎛️ **Zero Início em Branco - 100% Dados Carregados**
