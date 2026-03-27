# data_extractor.py - Orkestra Data Extraction
# Extrai e estrutura dados das planilhas 2024 e 2025
# Usa N CTT como chave primária

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


def detect_file_type(filepath: str) -> str:
    """Detecta tipo de arquivo."""
    ext = Path(filepath).suffix.lower()
    if ext in ['.xlsx', '.xls']:
        return 'excel'
    elif ext == '.csv':
        return 'csv'
    return 'unknown'


def load_csv(filepath: str) -> List[Dict]:
    """Carrega CSV retornando lista de dicionários."""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(dict(row))
    return data


def load_excel(filepath: str) -> List[Dict]:
    """Carrega Excel usando pandas se disponível."""
    try:
        import pandas as pd
        df = pd.read_excel(filepath)
        return df.to_dict('records')
    except ImportError:
        print("⚠️  pandas não instalado. Use CSV ou instale: pip install pandas openpyxl")
        return []


def normalize_contract_id(value: Any) -> str:
    """
    Normaliza N CTT para string limpa.
    Remove espaços, converte para string uppercase.
    """
    if value is None:
        return ""
    return str(value).strip().upper().replace(" ", "")


def parse_revenue(value: Any) -> float:
    """
    Converte valor de receita para float.
    Remove R$, pontos de milhar, converte vírgula para ponto.
    """
    if value is None or value == "":
        return 0.0
    
    # Converter para string
    s = str(value)
    
    # Remover R$ e espaços
    s = s.replace("R$", "").replace(" ", "").replace("R", "")
    
    # Remover pontos de milhar e converter vírgula para ponto
    s = s.replace(".", "").replace(",", ".")
    
    try:
        return float(s)
    except:
        return 0.0


def parse_date(value: Any) -> str:
    """
    Normaliza data para formato ISO YYYY-MM-DD.
    Aceita múltiplos formatos.
    """
    if value is None or value == "":
        return ""
    
    s = str(value).strip()
    
    # Tentar diferentes formatos
    formats = [
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except:
            continue
    
    return s  # Retorna original se não conseguir parsear


def normalize_status(value: Any) -> str:
    """
    Normaliza status para categorias padronizadas.
    """
    if value is None:
        return "UNKNOWN"
    
    s = str(value).strip().upper()
    
    # Mapeamentos comuns
    status_map = {
        "CONFIRMADO": "CONFIRMED",
        "CONFIRM": "CONFIRMED",
        "APROVADO": "CONFIRMED",
        "CANCELADO": "CANCELLED",
        "CANCEL": "CANCELLED",
        "PENDENTE": "PENDING",
        "PEND": "PENDING",
        "PAGO": "PAID",
        "PAGAMENTO": "PAID",
        "EXECUTADO": "EXECUTED",
        "REALIZADO": "EXECUTED",
        "FINALIZADO": "COMPLETED",
    }
    
    # Buscar match parcial
    for key, val in status_map.items():
        if key in s:
            return val
    
    return s if s else "UNKNOWN"


def extract_contract_data(row: Dict, column_mapping: Dict[str, str]) -> Optional[Dict]:
    """
    Extrai dados estruturados de uma linha da planilha.
    
    column_mapping: mapeia nomes padronizados para nomes reais na planilha
    """
    # Buscar N CTT
    contract_id = None
    for key in ['n_ctt', 'nctt', 'nºctt', 'ctt', 'contrato', 'contract', 'número', 'numero', 'n']:
        if key in column_mapping:
            col_name = column_mapping[key]
            if col_name in row:
                contract_id = normalize_contract_id(row[col_name])
                break
    
    if not contract_id:
        return None
    
    # Extrair data
    date_value = ""
    for key in ['data', 'date', 'dt', 'data_evento', 'event_date']:
        if key in column_mapping:
            col_name = column_mapping[key]
            if col_name in row:
                date_value = parse_date(row[col_name])
                break
    
    # Extrair status
    status = "UNKNOWN"
    for key in ['status', 'situação', 'situacao', 'estado']:
        if key in column_mapping:
            col_name = column_mapping[key]
            if col_name in row:
                status = normalize_status(row[col_name])
                break
    
    # Extrair receitas
    revenue_locacao = 0.0
    for key in ['locacao', 'locação', 'aluguel', 'space', 'espaço', 'venue']:
        if key in column_mapping:
            col_name = column_mapping[key]
            if col_name in row:
                revenue_locacao = parse_revenue(row[col_name])
                break
    
    revenue_catering = 0.0
    for key in ['catering', 'buffet', 'comida', 'bebida', 'alimentação']:
        if key in column_mapping:
            col_name = column_mapping[key]
            if col_name in row:
                revenue_catering = parse_revenue(row[col_name])
                break
    
    # Se tiver receita total mas não locação/catering separado
    revenue_total = 0.0
    for key in ['total', 'receita', 'revenue', 'valor', 'valor_total']:
        if key in column_mapping:
            col_name = column_mapping[key]
            if col_name in row:
                revenue_total = parse_revenue(row[col_name])
                break
    
    # Calcular total se não fornecido
    if revenue_total == 0:
        revenue_total = revenue_locacao + revenue_catering
    
    return {
        "contract_id": contract_id,
        "date": date_value,
        "status": status,
        "revenue_locacao": revenue_locacao,
        "revenue_catering": revenue_catering,
        "revenue_total": revenue_total,
        "_raw": row  # Manter dados brutos para referência
    }


def detect_columns(rows: List[Dict]) -> Dict[str, str]:
    """
    Detecta automaticamente mapeamento de colunas baseado nos headers.
    """
    if not rows:
        return {}
    
    # Pegar primeira linha para analisar headers
    first_row = rows[0]
    headers = list(first_row.keys())
    
    column_mapping = {}
    
    # Normalizar headers para busca
    headers_lower = [h.lower().strip().replace(" ", "_") for h in headers]
    
    # Mapear N CTT
    for i, h in enumerate(headers_lower):
        if any(k in h for k in ['ctt', 'contrato', 'nº', 'n_', 'numero']):
            column_mapping['n_ctt'] = headers[i]
            break
    
    # Mapear Data
    for i, h in enumerate(headers_lower):
        if any(k in h for k in ['data', 'date', 'dt']):
            column_mapping['data'] = headers[i]
            break
    
    # Mapear Status
    for i, h in enumerate(headers_lower):
        if any(k in h for k in ['status', 'situa', 'situação']):
            column_mapping['status'] = headers[i]
            break
    
    # Mapear Locação
    for i, h in enumerate(headers_lower):
        if any(k in h for k in ['locação', 'locacao', 'aluguel', 'espaço', 'espaco']):
            column_mapping['locacao'] = headers[i]
            break
    
    # Mapear Catering
    for i, h in enumerate(headers_lower):
        if any(k in h for k in ['catering', 'buffet', 'comida', 'alimentação']):
            column_mapping['catering'] = headers[i]
            break
    
    # Mapear Total
    for i, h in enumerate(headers_lower):
        if any(k in h for k in ['total', 'valor_total', 'receita_total']):
            column_mapping['total'] = headers[i]
            break
    
    return column_mapping


def classify_contract(contract: Dict) -> str:
    """
    Classifica tipo de contrato.
    """
    has_locacao = contract["revenue_locacao"] > 0
    has_catering = contract["revenue_catering"] > 0
    
    if has_locacao and has_catering:
        return "LOCACAO_E_CATERING"
    elif has_locacao:
        return "APENAS_LOCACAO"
    elif has_catering:
        return "APENAS_CATERING"
    else:
        return "SEM_RECEITA"


def process_file(filepath: str, year: str) -> Dict[str, Any]:
    """
    Processa arquivo e gera dataset estruturado.
    """
    print(f"\n📂 Processando: {filepath}")
    
    # Detectar tipo
    file_type = detect_file_type(filepath)
    
    # Carregar dados
    if file_type == 'excel':
        raw_data = load_excel(filepath)
    elif file_type == 'csv':
        raw_data = load_csv(filepath)
    else:
        print(f"❌ Tipo de arquivo não suportado: {file_type}")
        return {}
    
    if not raw_data:
        print("❌ Nenhum dado carregado")
        return {}
    
    print(f"   ✅ {len(raw_data)} registros carregados")
    
    # Detectar colunas
    column_mapping = detect_columns(raw_data)
    print(f"   🔍 Colunas detectadas: {list(column_mapping.values())}")
    
    # Extrair dados estruturados
    contracts = []
    cancelled = []
    only_locacao = []
    only_catering = []
    
    for row in raw_data:
        contract = extract_contract_data(row, column_mapping)
        
        if contract:
            contract_type = classify_contract(contract)
            contract["contract_type"] = contract_type
            
            # Categorizar
            if contract["status"] == "CANCELLED":
                cancelled.append(contract)
            elif contract_type == "APENAS_LOCACAO":
                only_locacao.append(contract)
            elif contract_type == "APENAS_CATERING":
                only_catering.append(contract)
            
            contracts.append(contract)
    
    # Estatísticas
    total_revenue = sum(c["revenue_total"] for c in contracts)
    event_count = len([c for c in contracts if c["status"] not in ["CANCELLED", "PENDING"]])
    avg_ticket = total_revenue / event_count if event_count > 0 else 0
    
    # Validações de qualidade
    print("\n🔍 Executando validações de qualidade...")
    validation_issues = validate_data(contracts)
    print_validation_report(validation_issues, len(contracts))
    
    result = {
        "metadata": {
            "source_file": filepath,
            "year": year,
            "processed_at": datetime.now().isoformat(),
            "total_records": len(raw_data),
            "valid_contracts": len(contracts),
        },
        "summary": {
            "total_contracts": len(contracts),
            "total_events": event_count,
            "cancelled": len(cancelled),
            "only_locacao": len(only_locacao),
            "only_catering": len(only_catering),
            "locacao_e_catering": len([c for c in contracts if c["contract_type"] == "LOCACAO_E_CATERING"]),
            "total_revenue": round(total_revenue, 2),
            "avg_ticket": round(avg_ticket, 2)
        },
        "validation": {
            "duplicates_count": len(validation_issues["duplicates"]),
            "null_values_count": len(validation_issues["null_values"]),
            "inconsistencies_count": len(validation_issues["inconsistencies"]),
            "warnings_count": len(validation_issues["warnings"]),
            "issues": validation_issues
        },
        "contracts": contracts,
        "by_category": {
            "cancelled": cancelled,
            "only_locacao": only_locacao,
            "only_catering": only_catering
        }
    }
    
    return result


# ============================================
# VALIDAÇÕES DE QUALIDADE
# ============================================

def validate_data(contracts: List[Dict]) -> Dict:
    """
    Executa validações de qualidade nos dados extraídos.
    
    Checa:
    - Duplicados (N CTT repetido)
    - Valores nulos (campos vazios)
    - Inconsistências (valores negativos, datas inválidas)
    """
    issues = {
        "duplicates": [],
        "null_values": [],
        "inconsistencies": [],
        "warnings": []
    }
    
    # Checar duplicados
    seen_ids = {}
    for contract in contracts:
        cid = contract.get("contract_id", "")
        if cid:
            if cid in seen_ids:
                issues["duplicates"].append({
                    "contract_id": cid,
                    "first_occurrence": seen_ids[cid],
                    "duplicate_index": contracts.index(contract)
                })
            else:
                seen_ids[cid] = contracts.index(contract)
    
    # Checar valores nulos e inconsistências
    for i, contract in enumerate(contracts):
        contract_issues = []
        
        # N CTT nulo
        if not contract.get("contract_id"):
            contract_issues.append("contract_id: NULL")
        
        # Data nula ou inválida
        date = contract.get("date", "")
        if not date:
            contract_issues.append("date: NULL")
        elif len(date) != 10 or "-" not in date:
            contract_issues.append(f"date: INVALID_FORMAT ({date})")
        
        # Status nulo
        if not contract.get("status") or contract.get("status") == "UNKNOWN":
            contract_issues.append("status: NULL_OR_UNKNOWN")
        
        # Receitas negativas
        if contract.get("revenue_locacao", 0) < 0:
            contract_issues.append(f"revenue_locacao: NEGATIVE ({contract['revenue_locacao']})")
        
        if contract.get("revenue_catering", 0) < 0:
            contract_issues.append(f"revenue_catering: NEGATIVE ({contract['revenue_catering']})")
        
        if contract.get("revenue_total", 0) < 0:
            contract_issues.append(f"revenue_total: NEGATIVE ({contract['revenue_total']})")
        
        # Inconsistência: total diferente da soma
        loc = contract.get("revenue_locacao", 0)
        cat = contract.get("revenue_catering", 0)
        total = contract.get("revenue_total", 0)
        
        if total > 0 and abs(total - (loc + cat)) > 0.01:
            if loc > 0 or cat > 0:  # Só reportar se tiver valores individuais
                issues["inconsistencies"].append({
                    "contract_id": contract.get("contract_id", "UNKNOWN"),
                    "index": i,
                    "issue": "REVENUE_MISMATCH",
                    "locacao": loc,
                    "catering": cat,
                    "calculated_total": loc + cat,
                    "stated_total": total,
                    "difference": total - (loc + cat)
                })
        
        # Alertas (não críticos)
        # Contrato com receita zero
        if total == 0 and contract.get("status") != "CANCELLED":
            issues["warnings"].append({
                "contract_id": contract.get("contract_id", "UNKNOWN"),
                "index": i,
                "warning": "ZERO_REVENUE_NOT_CANCELLED",
                "message": "Contrato não cancelado com receita zero"
            })
        
        # Contrato cancelado com receita positiva
        if contract.get("status") == "CANCELLED" and total > 0:
            issues["warnings"].append({
                "contract_id": contract.get("contract_id", "UNKNOWN"),
                "index": i,
                "warning": "CANCELLED_WITH_REVENUE",
                "message": f"Contrato cancelado com receita R$ {total:,.2f}"
            })
        
        # Data futura para contratos executados
        try:
            if contract.get("date") and contract.get("status") in ["EXECUTED", "COMPLETED", "PAID"]:
                from datetime import datetime
                event_date = datetime.strptime(contract["date"], "%Y-%m-%d")
                if event_date > datetime.now():
                    issues["inconsistencies"].append({
                        "contract_id": contract.get("contract_id", "UNKNOWN"),
                        "index": i,
                        "issue": "FUTURE_DATE_FOR_COMPLETED_EVENT",
                        "date": contract["date"],
                        "status": contract["status"]
                    })
        except:
            pass
        
        if contract_issues:
            issues["null_values"].append({
                "contract_id": contract.get("contract_id", "UNKNOWN"),
                "index": i,
                "issues": contract_issues
            })
    
    return issues


def print_validation_report(issues: Dict, total_contracts: int):
    """
    Imprime relatório de validação.
    """
    print("\n🔍 RELATÓRIO DE VALIDAÇÃO")
    print("=" * 60)
    
    # Duplicados
    if issues["duplicates"]:
        print(f"\n❌ DUPLICADOS: {len(issues['duplicates'])}")
        for dup in issues["duplicates"][:10]:  # Mostrar primeiros 10
            print(f"   - N CTT {dup['contract_id']} (linha {dup['duplicate_index']})")
        if len(issues["duplicates"]) > 10:
            print(f"   ... e mais {len(issues['duplicates']) - 10} duplicados")
    else:
        print(f"\n✅ DUPLICADOS: 0")
    
    # Valores nulos
    if issues["null_values"]:
        print(f"\n⚠️  VALORES NULOS/INVÁLIDOS: {len(issues['null_values'])} contratos")
        for item in issues["null_values"][:5]:
            print(f"   - {item['contract_id']}: {', '.join(item['issues'])}")
        if len(issues["null_values"]) > 5:
            print(f"   ... e mais {len(issues['null_values']) - 5} contratos")
    else:
        print(f"\n✅ VALORES NULOS: 0")
    
    # Inconsistências
    if issues["inconsistencies"]:
        print(f"\n🔴 INCONSISTÊNCIAS: {len(issues['inconsistencies'])}")
        for inc in issues["inconsistencies"][:5]:
            print(f"   - {inc['contract_id']}: {inc['issue']}")
            if inc['issue'] == "REVENUE_MISMATCH":
                print(f"     Locação: R$ {inc['locacao']:,.2f} + Catering: R$ {inc['catering']:,.2f} = R$ {inc['calculated_total']:,.2f}")
                print(f"     Mas total informado: R$ {inc['stated_total']:,.2f}")
                print(f"     Diferença: R$ {inc['difference']:,.2f}")
        if len(issues["inconsistencies"]) > 5:
            print(f"   ... e mais {len(issues['inconsistencies']) - 5} inconsistências")
    else:
        print(f"\n✅ INCONSISTÊNCIAS: 0")
    
    # Warnings
    if issues["warnings"]:
        print(f"\n⚠️  ALERTAS: {len(issues['warnings'])}")
        for warn in issues["warnings"][:5]:
            print(f"   - {warn['contract_id']}: {warn['warning']}")
        if len(issues["warnings"]) > 5:
            print(f"   ... e mais {len(issues['warnings']) - 5} alertas")
    
    # Resumo
    total_issues = len(issues["duplicates"]) + len(issues["null_values"]) + len(issues["inconsistencies"])
    print("\n" + "-" * 60)
    print(f"📊 TOTAL DE PROBLEMAS: {total_issues}")
    print(f"📊 CONTRATOS VÁLIDOS: {total_contracts - len(issues['null_values'])}")
    print(f"📊 TAXA DE QUALIDADE: {((total_contracts - len(issues['null_values'])) / total_contracts * 100):.1f}%")
    print("=" * 60)


def save_dataset(data: Dict, output_path: str):
    """Salva dataset em JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"   💾 Salvo: {output_path}")


# ============================================
# MAIN
# ============================================

def extract_data(year: str, filepath: str, output_dir: str = "data"):
    """
    Extrai dados de um arquivo para o ano especificado.
    
    Args:
        year: "2024" ou "2025"
        filepath: caminho para arquivo .csv ou .xlsx
        output_dir: diretório de saída
    """
    # Criar diretório
    Path(output_dir).mkdir(exist_ok=True)
    
    # Processar
    dataset = process_file(filepath, year)
    
    if dataset:
        output_path = f"{output_dir}/event_dataset_{year}.json"
        save_dataset(dataset, output_path)
        
        # Print resumo
        summary = dataset['summary']
        print(f"\n📊 RESUMO {year}:")
        print("-" * 40)
        print(f"   💰 Total receita: R$ {summary['total_revenue']:,.2f}")
        print(f"   🎯 Número de eventos: {summary['total_events']}")
        print(f"   📈 Ticket médio: R$ {summary['avg_ticket']:,.2f}")
        print("-" * 40)
        print(f"   Total contratos: {summary['total_contracts']}")
        print(f"   Cancelados: {summary['cancelled']}")
        print(f"   Apenas locação: {summary['only_locacao']}")
        print(f"   Apenas catering: {summary['only_catering']}")
        print(f"   Locação + Catering: {summary['locacao_e_catering']}")
    
    return dataset


if __name__ == "__main__":
    import sys
    
    # Verificar argumentos
    if len(sys.argv) < 3:
        print("Uso: python data_extractor.py <ano> <arquivo>")
        print("Exemplo: python data_extractor.py 2025 dados_2025.xlsx")
        print("\nOu configure manualmente abaixo:")
        
        # Modo manual - editar aqui
        # extract_data("2024", "caminho/para/planilha_2024.xlsx")
        # extract_data("2025", "caminho/para/planilha_2025.xlsx")
        sys.exit(1)
    
    year = sys.argv[1]
    filepath = sys.argv[2]
    
    extract_data(year, filepath)
