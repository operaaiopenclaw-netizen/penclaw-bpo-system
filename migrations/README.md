# Migrations Orkestra — PostgreSQL

## Estrutura

```
migrations/
├── README.md                     # Este arquivo
├── migrate.sh                    # Script CLI
├── V001__baseline.sql           # Schema inicial (todas as tabelas)
├── V002__seed_data.sql          # Dados iniciais (roles, permissions, tenants)
└── V003__advanced_triggers.sql  # Functions avançadas + views
```

## Convenções

- **V###__descriptive_name.sql** — schema fixo
- Sem rollback — logs são imutáveis
- Particionamento automático nas tabelas de log

## Uso

```bash
# Verificar status
./migrations/migrate.sh status

# Aplicar todas as migrations pendentes
./migrations/migrate.sh up

# Inserir dados iniciais
./migrations/migrate