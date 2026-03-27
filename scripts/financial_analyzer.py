# financial_analyzer.py - Orkestra Financial Intelligence Agent
# Análise financeira operacional de eventos

import json
from typing import Dict, List, Any


def load_data(filepath: str) -> Dict:
    """Carrega dados do arquivo JSON."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_event(transactions: List[Dict]) -> Dict:
    """
    Calcula métricas financeiras para um conjunto de transações.
    """
    receita = sum(t["value"] for t in transactions if t["type"] == "income")
    custo = sum(t["value"] for t in transactions if t["type"] == "expense")
    
    # Cálculo da margem
    margem_abs = receita - custo
    margem_pct = (margem_abs / receita * 100) if receita > 0 else 0
    
    # Custo por categoria
    custo_por_categoria = {}
    for t in transactions:
        if t["type"] == "expense":
            cat = t.get("category", "outros")
            custo_por_categoria[cat] = custo_por_categoria.get(cat, 0) + t["value"]
    
    # Percentual de cada categoria sobre o custo total
    pct_por_categoria = {}
    for cat, val in custo_por_categoria.items():
        pct_por_categoria[cat] = (val / custo * 100) if custo > 0 else 0
    
    return {
        "receita": receita,
        "custo": custo,
        "margem_abs": margem_abs,
        "margem_pct": margem_pct,
        "custo_por_categoria": custo_por_categoria,
        "pct_por_categoria": pct_por_categoria
    }


def detect_alerts(analise: Dict) -> List[Dict]:
    """
    Detecta alertas baseado nos thresholds definidos.
    """
    alertas = []
    
    margem_pct = analise["margem_pct"]
    
    # Alerta crítico: margem < 0
    if margem_pct < 0:
        alertas.append({
            "nivel": "CRÍTICO",
            "tipo": "margem",
            "mensagem": f"🚨 PREJUÍZO: margem negativa ({margem_pct:.1f}%)",
            "acao": "Reavaliar viabilidade do evento ou renegociar contrato"
        })
    
    # Alerta atenção: margem < 30%
    elif margem_pct < 30:
        alertas.append({
            "nivel": "ATENÇÃO",
            "tipo": "margem",
            "mensagem": f"⚠️ Margem baixa: {margem_pct:.1f}% (< 30%)",
            "acao": "Buscar economias urgentes ou ajustar preço de venda"
        })
    
    # Alertas de categoria > 40%
    for cat, pct in analise["pct_por_categoria"].items():
        if pct > 40:
            alertas.append({
                "nivel": "CATEGORIA",
                "tipo": "concentracao",
                "mensagem": f"📊 '{cat}' representa {pct:.1f}% do custo total",
                "acao": "Revisar fornecedor e buscar alternativas"
            })
    
    return alertas


def generate_suggestions(alertas: List[Dict], analise: Dict) -> List[str]:
    """
    Gera sugestões práticas baseadas nos alertas detectados.
    """
    sugestoes = []
    
    for alerta in alertas:
        if alerta["nivel"] == "CRÍTICO":
            sugestoes.extend([
                "🔴 URGENTE: Revisar contrato com cliente",
                "🔴 URGENTE: Congelar novas despesas",
                "🔴 URGENTE: Negociar parcelamento com fornecedores"
            ])
        
        elif alerta["nivel"] == "ATENÇÃO":
            sugestoes.extend([
                "🟡 Reduzir escopo não essencial do evento",
                "🟡 Buscar 2ª cotação em fornecedores principais",
                "🟡 Considerar upgrade de pacote para próximo evento"
            ])
        
        elif alerta["tipo"] == "concentracao":
            cat = alerta["mensagem"].split("'")[1] if "'" in alerta["mensagem"] else "item"
            sugestoes.extend([
                f"🟡 Diversificar fornecedores de {cat}",
                f"🟡 Analisar mix: {cat} pode estar sobre-dimensionado"
            ])
    
    return sugestoes if sugestoes else ["✅ Nenhuma ação necessária - evento dentro dos parâmetros"]


def format_currency(value: float) -> str:
    """Formata valor para moeda brasileira (R$)."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def analyze_events(filepath: str) -> str:
    """
    Análise completa de eventos financeiros.
    Retorna output formatado conforme especificação.
    """
    data = load_data(filepath)
    transactions = data.get("transactions", [])
    
    # Agrupar por evento
    eventos = {}
    for t in transactions:
        evento = t.get("event", "Sem Evento")
        if evento not in eventos:
            eventos[evento] = []
        eventos[evento].append(t)
    
    output = []
    output.append("=" * 50)
    output.append("🎛️ ORKESTRA FINANCIAL INTELLIGENCE REPORT")
    output.append("=" * 50)
    
    for evento_nome, transacoes in eventos.items():
        # [1] ANÁLISE DO EVENTO
        analise = analyze_event(transacoes)
        
        output.append("\n[1] EVENTO")
        output.append(f"  📍 Nome: {evento_nome}")
        output.append(f"  💰 Receita: {format_currency(analise['receita'])}")
        output.append(f"  💸 Custo: {format_currency(analise['custo'])}")
        output.append(f"  📈 Margem Absoluta: {format_currency(analise['margem_abs'])}")
        output.append(f"  📊 Margem %: {analise['margem_pct']:.1f}%")
        
        # [2] ALERTAS
        alertas = detect_alerts(analise)
        output.append("\n[2] ALERTAS")
        if alertas:
            for alerta in alertas:
                output.append(f"  {alerta['mensagem']}")
                output.append(f"     → Ação: {alerta['acao']}")
        else:
            output.append("  ✅ Nenhum alerta - evento saudável")
        
        # [3] SUGESTÕES
        sugestoes = generate_suggestions(alertas, analise)
        output.append("\n[3] SUGESTÕES")
        for sug in sugestoes:
            output.append(f"  {sug}")
        
        output.append("\n" + "-" * 50)
    
    return "\n".join(output)


# Execução principal
if __name__ == "__main__":
    import sys
    
    filepath = sys.argv[1] if len(sys.argv) > 1 else "financial_log.json"
    
    try:
        report = analyze_events(filepath)
        print(report)
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {filepath}")
    except json.JSONDecodeError:
        print(f"❌ JSON inválido em: {filepath}")
    except Exception as e:
        print(f"❌ Erro na análise: {str(e)}")
