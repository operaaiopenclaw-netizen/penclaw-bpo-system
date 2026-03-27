# event_profitability_agent.py - Orkestra Event Profitability Agent
# Avaliação de viabilidade e rentabilidade de eventos

import json
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class Decisao(Enum):
    APROVAR = "APROVAR"
    REVISAR = "REVISAR"
    RECUSAR = "RECUSAR"


@dataclass
class EventoInput:
    nome: str
    receita: float
    custos: Dict[str, float]
    participantes: int
    duracao_horas: int
    complexidade: str  # baixa, media, alta
    data: str


@dataclass
class AnaliseRentabilidade:
    evento: str
    decisao: Decisao
    margem_percentual: float
    margem_absoluta: float
    custo_por_pessoa: float
    receita_por_pessoa: float
    pontuacao_risco: int
    alertas: List[str]
    recomendacao: str


def calcular_complexidade_score(complexidade: str) -> int:
    """
    Pontuação baseada na complexidade operacional.
    """
    scores = {
        "baixa": 1,
        "media": 2,
        "média": 2,
        "alta": 3
    }
    return scores.get(complexidade.lower(), 2)


def calcular_custo_total(custos: Dict[str, float]) -> float:
    """Soma todos os custos do evento."""
    return sum(custos.values())


def analisar_rentabilidade(evento: EventoInput) -> AnaliseRentabilidade:
    """
    Análise completa de rentabilidade do evento.
    """
    custo_total = calcular_custo_total(evento.custos)
    margem_abs = evento.receita - custo_total
    margem_pct = (margem_abs / evento.receita * 100) if evento.receita > 0 else 0
    
    custo_por_pessoa = custo_total / evento.participantes if evento.participantes > 0 else 0
    receita_por_pessoa = evento.receita / evento.participantes if evento.participantes > 0 else 0
    
    complexidade_score = calcular_complexidade_score(evento.complexidade)
    
    alertas = []
    pontuacao_risco = 0
    
    # Critério 1: Margem mínima 30%
    if margem_pct < 0:
        alertas.append(f"🚨 PREJUÍZO: margem negativa ({margem_pct:.1f}%)")
        pontuacao_risco += 100
    elif margem_pct < 15:
        alertas.append(f"🔴 Margem crítica: {margem_pct:.1f}% (< 15%)")
        pontuacao_risco += 50
    elif margem_pct < 30:
        alertas.append(f"🟡 Margem abaixo do ideal: {margem_pct:.1f}% (< 30%)")
        pontuacao_risco += 25
    
    # Critério 2: Custo por pessoa
    # Benchmarks (ajustáveis conforme segmento)
    if custo_por_pessoa > 500:
        alertas.append(f"💰 Custo por pessoa elevado: R$ {custo_por_pessoa:.2f}")
        pontuacao_risco += 15
    
    # Critério 3: Complexidade operacional
    if complexidade_score >= 3:
        alertas.append(f"⚙️ Complexidade alta exige mais staff/gestão")
        pontuacao_risco += 20
    elif complexidade_score >= 2 and margem_pct < 35:
        alertas.append(f"⚙️ Complexidade média com margem apertada")
        pontuacao_risco += 10
    
    # Critério adicional: Receita por pessoa
    if receita_por_pessoa < custo_por_pessoa * 1.5:
        alertas.append(f"📉 Receita/pessoa insuficiente para cobrir risco operacional")
        pontuacao_risco += 15
    
    # Decisão final
    if pontuacao_risco >= 70 or margem_pct < 0:
        decisao = Decisao.RECUSAR
        recomendacao = "❌ NÃO ACEITAR: Riscos financeiros superam o retorno. Negociar aumento de preço ou reduzir escopo."
    elif pontuacao_risco >= 30 or margem_pct < 25:
        decisao = Decisao.REVISAR
        recomendacao = "⚠️ REVISAR: Viável com ajustes. Repassar custos ao cliente ou renegociar fornecedores antes de confirmar."
    else:
        decisao = Decisao.APROVAR
        recomendacao = "✅ APROVAR: Rentabilidade adequada. Proceder com contrato e planejamento operacional."
    
    return AnaliseRentabilidade(
        evento=evento.nome,
        decisao=decisao,
        margem_percentual=margem_pct,
        margem_absoluta=margem_abs,
        custo_por_pessoa=custo_por_pessoa,
        receita_por_pessoa=receita_por_pessoa,
        pontuacao_risco=pontuacao_risco,
        alertas=alertas,
        recomendacao=recomendacao
    )


def format_currency(value: float) -> str:
    """Formata valor para moeda brasileira (R$)."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_report_avaliacao(analise: AnaliseRentabilidade) -> str:
    """
    Gera relatório formatado da avaliação.
    """
    output = []
    
    # Header
    output.append("=" * 60)
    output.append("🎛️ ORKESTRA EVENT PROFITABILITY ANALYSIS")
    output.append("=" * 60)
    
    # Evento
    output.append(f"\n📍 Evento: {analise.evento}")
    
    # Decisão em destaque
    output.append("")
    simbolo = "✅" if analise.decisao == Decisao.APROVAR else "⚠️" if analise.decisao == Decisao.REVISAR else "❌"
    output.append(f"[DECISÃO] {simbolo} {analise.decisao.value}")
    output.append("-" * 40)
    
    # Métricas principais
    output.append("\n[INDICADORES FINANCEIROS]")
    output.append(f"  💰 Margem Absoluta: {format_currency(analise.margem_absoluta)}")
    output.append(f"  📊 Margem Percentual: {analise.margem_percentual:.1f}%")
    status_margem = "🟢" if analise.margem_percentual >= 30 else "🟡" if analise.margem_percentual >= 15 else "🔴"
    output.append(f"     {status_margem} Meta: ≥ 30%")
    
    output.append(f"\n  👥 Custo por Pessoa: {format_currency(analise.custo_por_pessoa)}")
    output.append(f"  💵 Receita por Pessoa: {format_currency(analise.receita_por_pessoa)}")
    
    # Alertas
    if analise.alertas:
        output.append("\n[ALERTAS IDENTIFICADOS]")
        for alerta in analise.alertas:
            output.append(f"  {alerta}")
    else:
        output.append("\n[ALERTAS] ✅ Nenhum alerta - evento dentro dos parâmetros")
    
    # Score de risco
    risco_emoji = "🔴" if analise.pontuacao_risco >= 70 else "🟡" if analise.pontuacao_risco >= 30 else "🟢"
    output.append(f"\n[PONTUAÇÃO DE RISCO] {risco_emoji} {analise.pontuacao_risco}/100")
    if analise.pontuacao_risco >= 70:
        output.append("     Nível: ALTO - Decisão automática de recusa")
    elif analise.pontuacao_risco >= 30:
        output.append("     Nível: MODERADO - Requer ajustes")
    else:
        output.append("     Nível: BAIXO - Dentro do perfil aceitável")
    
    # Recomendação
    output.append("\n[RECOMENDAÇÃO]")
    output.append(f"  {analise.recomendacao}")
    
    output.append("\n" + "=" * 60)
    
    return "\n".join(output)


def avaliar_evento_from_json(filepath: str) -> str:
    """
    Avalia evento a partir de arquivo JSON.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return f"❌ Arquivo não encontrado: {filepath}"
    except json.JSONDecodeError:
        return f"❌ JSON inválido em: {filepath}"
    
    evento_input = EventoInput(
        nome=data.get("nome", "Sem nome"),
        receita=float(data.get("receita", 0)),
        custos=data.get("custos", {}),
        participantes=int(data.get("participantes", 0)),
        duracao_horas=int(data.get("duracao_horas", 0)),
        complexidade=data.get("complexidade", "media"),
        data=data.get("data", "")
    )
    
    analise = analisar_rentabilidade(evento_input)
    return gerar_report_avaliacao(analise)


# Exemplo de uso e teste
if __name__ == "__main__":
    import sys
    
    # Se passar arquivo, usa ele; senão, roda exemplo
    if len(sys.argv) > 1:
        print(avaliar_evento_from_json(sys.argv[1]))
    else:
        # Exemplo de teste
        exemplo = EventoInput(
            nome="Confraternização Empresa XYZ",
            receita=150000,
            custos={
                "proteina": 45000,
                "bebidas": 30000,
                "staff": 25000,
                "ambiance": 15000,
                "infraestrutura": 10000
            },
            participantes=200,
            duracao_horas=6,
            complexidade="media",
            data="2026-04-15"
        )
        
        analise = analisar_rentabilidade(exemplo)
        print(gerar_report_avaliacao(analise))
