# procurement_agent.py - Orkestra Procurement Intelligence Agent
# Geração inteligente de ordens de compra

import json
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Evento:
    nome: str
    data: str
    participantes: int
    consumo_por_pessoa: Dict[str, float]


@dataclass
class ItemCompra:
    item: str
    categoria: str
    necessario: float
    estoque: float
    comprar: float
    unidade: str
    fornecedor_sugerido: str


def load_events(filepath: str) -> List[Dict]:
    """Carrega eventos futuros."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("eventos_futuros", [])
    except FileNotFoundError:
        return []


def load_consumption(filepath: str) -> Dict[str, Dict]:
    """Carrega padrões de consumo por categoria."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Dados padrão fallback
        return {
            "protein": {"carne_kg_por_pessoa": 0.3, "frango_kg_por_pessoa": 0.2},
            "beverages": {"cerveja_un_por_pessoa": 3, "refrigerante_l_por_pessoa": 0.5},
            "supplies": {"prato_un_por_pessoa": 1.2, "copo_un_por_pessoa": 2},
            "ambiance": {"vela_un_por_mesa": 2, "arranjo_un_por_mesa": 1}
        }


def load_stock(filepath: str) -> Dict[str, float]:
    """Carrega estoque atual."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("estoque", {})
    except FileNotFoundError:
        return {}


def calcular_necessidade_evento(evento: Dict, consumo_padrao: Dict) -> Dict[str, float]:
    """
    Calcula necessidade total para um evento.
    """
    participantes = evento.get("participantes", 0)
    necessidade = {}
    
    for categoria, itens in consumo_padrao.items():
        for item, taxa in itens.items():
            key = f"{categoria}:{item}"
            necessidade[key] = participantes * taxa
    
    return necessidade


def consolidar_demanda_semanal(eventos: List[Dict], consumo_padrao: Dict) -> Dict[str, Dict]:
    """
    Consolida demanda dos próximos 7 dias.
    """
    hoje = datetime.now()
    semana_futura = hoje + timedelta(days=7)
    
    necessidade_consolidada = {}
    eventos_na_semana = []
    
    for evento in eventos:
        data_evento = datetime.strptime(evento.get("data", "2026-01-01"), "%Y-%m-%d")
        
        if hoje <= data_evento <= semana_futura:
            eventos_na_semana.append(evento)
            nec_evento = calcular_necessidade_evento(evento, consumo_padrao)
            
            for item, qtd in nec_evento.items():
                if item not in necessidade_consolidada:
                    necessidade_consolidada[item] = {"total": 0, "eventos": []}
                necessidade_consolidada[item]["total"] += qtd
                necessidade_consolidada[item]["eventos"].append(evento.get("nome", "Sem nome"))
    
    return necessidade_consolidada, eventos_na_semana


def calcular_compras(necessidade: Dict, estoque: Dict, margem_seguranca: float = 0.2) -> List[ItemCompra]:
    """
    Calcula quantidade a comprar com margem de segurança.
    """
    itens_compra = []
    
    mapeamento_unidades = {
        "kg": "kg",
        "un": "unidades",
        "l": "litros",
        "cx": "caixas",
        "ml": "mililitros"
    }
    
    mapeamento_fornecedores = {
        "protein": "Carnes do Brasil",
        "beverages": "Bebidas Premium SP",
        "supplies": "Descartáveis Rio",
        "ambiance": "Flores & Cia",
        "infrastructure": "Estruturas Silva"
    }
    
    for item_key, data in necessidade.items():
        categoria, item_nome = item_key.split(":", 1)
        necessario = data["total"]
        
        # Adicionar margem de segurança
        necessario_com_margem = necessario * (1 + margem_seguranca)
        
        # Verificar estoque
        estoque_atual = estoque.get(item_key, 0)
        
        # Calcular quantidade a comprar (nunca negativo)
        comprar = max(0, necessario_com_margem - estoque_atual)
        
        # Determinar unidade
        unidade = "un"
        for u in ["kg", "l", "cx", "ml"]:
            if u in item_nome:
                unidade = u
                break
        
        item = ItemCompra(
            item=item_nome,
            categoria=categoria,
            necessario=round(necessario_com_margem, 2),
            estoque=round(estoque_atual, 2),
            comprar=round(comprar, 2),
            unidade=mapeamento_unidades.get(unidade, "un"),
            fornecedor_sugerido=mapeamento_fornecedores.get(categoria, "Fornecedor Geral")
        )
        
        itens_compra.append(item)
    
    # Ordenar por categoria
    itens_compra.sort(key=lambda x: x.categoria)
    
    return itens_compra


def gerar_report_compras(itens: List[ItemCompra], eventos: List[Dict]) -> str:
    """
    Gera relatório formatado de compras.
    """
    output = []
    output.append("=" * 70)
    output.append("🎛️ ORKESTRA PROCUREMENT INTELLIGENCE REPORT")
    output.append("=" * 70)
    output.append(f"📅 Período: Próximos 7 dias")
    output.append(f"📊 Eventos na semana: {len(eventos)}")
    output.append("")
    
    for ev in eventos:
        output.append(f"   • {ev.get('nome', 'N/A')} - {ev.get('data', 'N/A')} ({ev.get('participantes', 0)} pessoas)")
    
    output.append("")
    output.append("-" * 70)
    output.append("[COMPRAS SUGERIDAS]")
    output.append("-" * 70)
    output.append(f"{'Categoria':<15} {'Item':<25} {'Necessário':<12} {'Estoque':<10} {'Comprar':<10}")
    output.append("-" * 70)
    
    total_por_categoria = {}
    
    for item in itens:
        if item.comprar > 0:  # Só mostrar itens que precisam ser comprados
            output.append(
                f"{item.categoria:<15} {item.item:<25} "
                f"{item.necessario:>8.1f} {item.unidade:<3} "
                f"{item.estoque:>6.1f} {item.unidade:<2} "
                f"{item.comprar:>6.1f} {item.unidade:<2}"
            )
            
            total_por_categoria[item.categoria] = total_por_categoria.get(item.categoria, 0) + item.comprar
    
    output.append("-" * 70)
    
    # Resumo por categoria
    output.append("")
    output.append("[RESUMO POR CATEGORIA]")
    for cat, total in sorted(total_por_categoria.items()):
        output.append(f"  📦 {cat}: {total:.1f} unidades/volumes")
    
    # Alertas de ruptura
    rupturas = [i for i in itens if i.necessario > 0 and i.comprar <= 0 and i.estoque < i.necessario]
    if rupturas:
        output.append("")
        output.append("🚨 ALERTAS DE RUPTURA:")
        for item in rupturas:
            output.append(f"   ⚠️ {item.item}: estoque ({item.estoque}) < necessário ({item.necessario})")
    
    # Sugestões de fornecedores
    output.append("")
    output.append("[FORNECEDORES SUGERIDOS]")
    fornecedores = set(i.fornecedor_sugerido for i in itens if i.comprar > 0)
    for forn in fornecedores:
        output.append(f"  📞 {forn}")
    
    output.append("")
    output.append("=" * 70)
    output.append("✅ Margem de segurança: 20% aplicada em todos os itens")
    output.append("✅ Critério: Zero ruptura - compras baseadas em demanda real + stock")
    
    return "\n".join(output)


def generate_procurement_plan(
    events_file: str = "eventos_futuros.json",
    consumption_file: str = "consumption_patterns.json",
    stock_file: str = "estoque.json"
) -> str:
    """
    Pipeline completo de Procurement Intelligence.
    """
    # Carregar dados
    eventos = load_events(events_file)
    consumo_padrao = load_consumption(consumption_file)
    estoque = load_stock(stock_file)
    
    # Processar
    necessidade, eventos_semana = consolidar_demanda_semanal(eventos, consumo_padrao)
    itens_compra = calcular_compras(necessidade, estoque, margem_seguranca=0.2)
    
    # Gerar relatório
    return gerar_report_compras(itens_compra, eventos_semana)


# Execução principal
if __name__ == "__main__":
    import sys
    
    events_file = sys.argv[1] if len(sys.argv) > 1 else "eventos_futuros.json"
    consumption_file = sys.argv[2] if len(sys.argv) > 2 else "consumption_patterns.json"
    stock_file = sys.argv[3] if len(sys.argv) > 3 else "estoque.json"
    
    try:
        report = generate_procurement_plan(events_file, consumption_file, stock_file)
        print(report)
    except Exception as e:
        print(f"❌ Erro na geração do plano de compras: {str(e)}")
