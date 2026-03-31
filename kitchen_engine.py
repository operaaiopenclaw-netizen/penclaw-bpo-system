#!/usr/bin/env python3
"""
Kitchen Intelligence Engine (KIE)
Sistema de gerenciamento de produção, custo e desperdício para eventos.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

DATA_DIR = Path(__file__).parent / "kitchen_data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


class TipoDesperdicio(Enum):
    SOBRA_APROVEITAVEL = "TIPO_A"      # Staff pode consumir
    SOBRA_DOACAO = "TIPO_B"             # Doação
    SOBRA_NAO_APROVEITAVEL = "TIPO_C"   # Descarte seguro
    ERRO_PREPARO = "TIPO_D"             # Perda total
    MATERIAL_ESTRAGADO = "TIPO_E"     # Perda total


@dataclass
class Ingrediente:
    codigo_inv: str
    nome: str
    quantidade_por_porcao: float
    unidade: str
    custo_unitario: float


def load_json(filename: str) -> Dict:
    """Carrega arquivo JSON do diretório kitchen_data."""
    filepath = DATA_DIR / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_json(filename: str, data: Dict):
    """Salva arquivo JSON no diretório kitchen_data."""
    filepath = DATA_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def atualizar_custos_receitas() -> Dict:
    """
    A. Cálculo automático de custo por receita
    Busca preços do inventory.json e atualiza recipe_costs.json
    """
    print("🔄 Atualizando custos das receitas...")
    
    inventory = load_json("inventory.json")
    recipes = load_json("recipes.json")
    
    if not inventory or not recipes:
        print("⚠️  Inventário ou receitas não encontrados")
        return {"erro": "Dados insuficientes", "custos_atualizados": 0}
    
    # Extrair preços do inventário
    precos = {}
    itens = inventory.get("inventory", [])
    for item in itens:
        codigo = item.get("codigo", "")
        preco_unit = item.get("preco_unitario", 0)
        if codigo:
            precos[codigo] = preco_unit
    
    recipes_calculadas = {}
    
    for receita_id, receita in recipes.get("receitas", {}).items():
        custo_total = 0
        ingredientes_atualizados = []
        falta_preco = []
        
        for ing in receita.get("ingredientes", []):
            codigo = ing.get("codigo_inv", "")
            qtd = ing.get("quantidade_por_porcao", 0)
            
            if codigo in precos:
                custo_ing = qtd * precos[codigo]
                custo_total += custo_ing
                ingredientes_atualizados.append({
                    **ing,
                    "custo_calculado": round(custo_ing, 2),
                    "preco_unitario_usado": precos[codigo]
                })
            else:
                falta_preco.append(codigo)
                ingredientes_atualizados.append(ing)
        
        rendimento = receita.get("rendimento_porca", 1)
        custo_por_porcao = custo_total / rendimento if rendimento > 0 else 0
        
        recipes_calculadas[receita_id] = {
            "nome": receita.get("nome"),
            "custo_por_porcao": round(custo_por_porcao, 2),
            "custo_total_receita": round(custo_total, 2),
            "base_calculo": {
                "data_custo": datetime.now().isoformat(),
                "fonte_preco": "inventory.json",
                "observacao": "Cálculo realizado em tempo real" if not falta_preco else f"Faltam preços: {falta_preco}"
            },
            "ingredientes_detalhados": ingredientes_atualizados,
            "alertas": [
                f"⚠️ Ingredientes sem preço: {falta_preco}" for falta_preco in ([falta_preco] if falta_preco else [])
            ]
        }
    
    # Calcular custo médio por pessoa
    custos_list = [r["custo_por_porcao"] for r in recipes_calculadas.values() if r["custo_por_porcao"] > 0]
    custo_medio = sum(custos_list) / len(custos_list) if custos_list else 0
    
    # Identificar mais cara e mais barata
    mais_cara = max(recipes_calculadas.items(), key=lambda x: x[1]["custo_por_porcao"]) if recipes_calculadas else None
    mais_barata = min(recipes_calculadas.items(), key=lambda x: x[1]["custo_por_porcao"]) if recipes_calculadas else None
    
    output = {
        "_meta": {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "receitas_calculadas": len(recipes_calculadas)
        },
        "calculo_logica": {
            "formula": "custo_por_porcao = SUM(quantidade_por_porcao * preco_unitario_estoque)",
            "atualizacao": "automática via kitchen_engine"
        },
        "receitas_calculadas": recipes_calculadas,
        "analise_comparativa": {
            "receita_mais_cara": {"id": mais_cara[0], "nome": mais_cara[1]["nome"], "custo": mais_cara[1]["custo_por_porcao"]} if mais_cara else None,
            "receita_mais_barata": {"id": mais_barata[0], "nome": mais_barata[1]["nome"], "custo": mais_barata[1]["custo_por_porcao"]} if mais_barata else None,
            "custo_medio_porcao": round(custo_medio, 2)
        }
    }
    
    save_json("recipe_costs.json", output)
    print(f"✅ Custos atualizados: {len(recipes_calculadas)} receitas")
    return output


def criar_plano_producao(
    evento_id: str,
    nome_evento: str,
    data_evento: str,
    num_convidados: int,
    tipo_servico: str = "buffet_completo",
    cardapio_ids: List[str] = None
) -> Dict:
    """
    B. Planejamento de produção por evento
    """
    print(f"📝 Criando plano de produção para: {nome_evento}")
    
    recipes = load_json("recipes.json")
    costs = load_json("recipe_costs.json")
    
    custos = costs.get("receitas_calculadas", {})
    fatores = {
        "buffet_completo": 1.15,
        "coquetel": 1.25,
        "coffee_break": 1.10,
        "jantar_servido": 1.05
    }
    
    fator = fatores.get(tipo_servico, 1.15)
    
    # Se não recebeu cardapio, usa default
    if not cardapio_ids:
        cardapio_ids = ["REC001", "REC002", "REC003", "REC004"]
    
    cardapio = {
        "entradas": [],
        "principal": [],
        "acompanhamentos": [],
        "finger_food": []
    }
    
    custo_total = 0
    
    for rec_id in cardapio_ids:
        receita = recipes.get("receitas", {}).get(rec_id, {})
        custo_rec = custos.get(rec_id, {}).get("custo_por_porcao", 0)
        
        porcoes = int(num_convidados * fator)
        valor = porcoes * custo_rec
        custo_total += valor
        
        item = {
            "receita_id": rec_id,
            "nome": receita.get("nome", "Desconhecido"),
            "porcoes_previstas": porcoes,
            "custo_estimado_porcao": custo_rec,
            "custo_total_estimado": round(valor, 2)
        }
        
        # Categorização simplificada
        categoria = receita.get("categoria", "")
        if categoria == "entrada":
            cardapio["entradas"].append(item)
        elif categoria == "principal":
            cardapio["principal"].append(item)
        elif categoria == "acompanhamento":
            cardapio["acompanhamentos"].append(item)
        elif categoria == "finger_food":
            cardapio["finger_food"].append(item)
    
    plano = {
        "evento_id": evento_id,
        "nome_evento": nome_evento,
        "data_evento": data_evento,
        "numero_convidados": num_convidados,
        "tipo_servico": tipo_servico,
        "fator_sobriga": fator,
        "status": "confirmado",
        "cardapio": cardapio,
        "totais_previstos": {
            "custo_total_comida": round(custo_total, 2),
            "custo_por_pessoa": round(custo_total / num_convidados, 2) if num_convidados else 0,
            "margem_inicial": None
        },
        "validacao": {
            "cobertura_check": True,
            "ingredientes_disponiveis": None,  # Virá da integração com estoque
            "equipe_suficiente": None
        },
        "created_at": datetime.now().isoformat()
    }
    
    # Carregar plano existente e adicionar novo
    planos = load_json("production_plan.json")
    if "eventos" not in planos:
        planos["eventos"] = {}
    planos["eventos"][evento_id] = plano
    planos["_meta"] = {
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "total_eventos": len(planos["eventos"])
    }
    
    save_json("production_plan.json", planos)
    print(f"✅ Plano criado: {evento_id}")
    print(f"   Custo estimado: R$ {custo_total:,.2f} | Por pessoa: R$ {plano['totais_previstos']['custo_por_pessoa']:.2f}")
    
    return plano


def check_estoque_disponivel(evento_id: str) -> Dict:
    """
    C. Integração com estoque
    Verifica se há ingredientes suficientes para o evento planejado
    """
    print(f"📦 Verificando estoque para evento: {evento_id}")
    
    plano = load_json("production_plan.json")
    inventory = load_json("inventory.json")
    recipes = load_json("recipes.json")
    
    evento = plano.get("eventos", {}).get(evento_id, {})
    if not evento:
        return {"erro": "Evento não encontrado", "status": "erro"}
    
    # Indexar estoque
    estoque = {}
    for item in inventory.get("inventory", []):
        estoque[item.get("codigo", "")] = {
            "quantidade": item.get("quantidade_atual", 0),
            "unidade": item.get("unidade", "kg"),
            "nome": item.get("nome", "")
        }
    
    # Calcular necessidades
    necessidades = {}
    
    for categoria, itens in evento.get("cardapio", {}).items():
        for item in itens:
            rec_id = item.get("receita_id")
            receita = recipes.get("receitas", {}).get(rec_id, {})
            porcoes = item.get("porcoes_previstas", 0)
            
            for ing in receita.get("ingredientes", []):
                codigo = ing.get("codigo_inv")
                qtd_por_porcao = ing.get("quantidade_por_porcao", 0)
                qtd_total = qtd_por_porcao * porcoes
                
                if codigo not in necessidades:
                    necessidades[codigo] = {
                        "nome": ing.get("nome"),
                        "quantidade_necessaria": 0,
                        "unidade": ing.get("unidade")
                    }
                necessidades[codigo]["quantidade_necessaria"] += qtd_total
    
    # Verificar disponibilidade
    verificacao = []
    faltantes = []
    
    for codigo, need in necessidades.items():
        estoque_item = estoque.get(codigo, {})
        disp = estoque_item.get("quantidade", 0)
        neces = need["quantidade_necessaria"]
        
        status = "ok" if disp >= neces else "faltando"
        
        item = {
            "codigo": codigo,
            "nome": need["nome"],
            "quantidade_necessaria": round(neces, 3),
            "quantidade_disponivel": disp,
            "diferenca": round(disp - neces, 3),
            "unidade": need["unidade"],
            "status": status
        }
        verificacao.append(item)
        
        if status == "faltando":
            faltantes.append(item)
    
    resultado = {
        "evento_id": evento_id,
        "status_geral": "ok" if not faltantes else "faltando_ingredientes",
        "items_verificados": len(verificacao),
        "items_faltantes": len(faltantes),
        "detalhamento": verificacao,
        "compra_sugerida": faltantes if faltantes else [],
        "timestamp": datetime.now().isoformat()
    }
    
    # Atualizar flag no plano
    plano["eventos"][evento_id]["validacao"]["ingredientes_disponiveis"] = (len(faltantes) == 0)
    save_json("production_plan.json", plano)
    
    print(f"   Status: {resultado['status_geral']}")
    if faltantes:
        print(f"   ⚠️  {len(faltantes)} itens faltando")
    else:
        print(f"   ✅ Estoque suficiente")
    
    return resultado


def registrar_producao_real(
    execucao_id: str,
    evento_id: str,
    receitas_executadas: List[Dict]
) -> Dict:
    """
    D. Registro de produção real
    """
    print(f"🍽️  Registrando produção: {execucao_id}")
    
    planos = load_json("production_plan.json")
    evento = planos.get("eventos", {}).get(evento_id, {})
    
    if not evento:
        return {"erro": "Evento não encontrado no plano"}
    
    custos = load_json("recipe_costs.json")
    custos_receitas = custos.get("receitas_calculadas", {})
    
    receitas_final = []
    custo_total = 0
    
    for rec in receitas_executadas:
        rec_id = rec.get("receita_id")
        producido = rec.get("porcoes_produzidas", 0)
        servido = rec.get("porcoes_servidas", 0)
        sobra = producido - servido
        
        custo_unit = custos_receitas.get(rec_id, {}).get("custo_por_porcao", 0)
        custo_real = producido * custo_unit
        custo_total += custo_real
        
        receitas_final.append({
            "receita_id": rec_id,
            "nome": rec.get("nome"),
            "porcoes_planejadas": rec.get("porcoes_planejadas"),
            "porcoes_produzidas": producido,
            "porcoes_servidas": servido,
            "porcoes_restantes": sobra,
            "custo_real": round(custo_real, 2),
            "status": "concluido"
        })
    
    num_convidados = evento.get("numero_convidados", 1)
    custo_previsto = evento.get("totais_previstos", {}).get("custo_total_comida", 0)
    
    execucao = {
        "execucao_id": execucao_id,
        "evento_id": evento_id,
        "nome_evento": evento.get("nome_evento"),
        "data_execucao": evento.get("data_evento"),
        "receitas_executadas": receitas_final,
        "totais": {
            "custo_total_real": round(custo_total, 2),
            "custo_por_pessoa_real": round(custo_total / num_convidados, 2),
            "variacao_custo_planejado": round(((custo_total - custo_previsto) / custo_previsto * 100), 2) if custo_previsto else 0
        },
        "timestamp_registro": datetime.now().isoformat()
    }
    
    execs = load_json("production_execution.json")
    if "execucoes" not in execs:
        execs["execucoes"] = {}
    execs["execucoes"][execucao_id] = execucao
    
    save_json("production_execution.json", execs)
    
    print(f"✅ Producao registrada: {execucao_id}")
    print(f"   Custo real: R$ {custo_total:,.2f} | Variação: {execucao['totais']['variacao_custo_planejado']:.1f}%")
    
    return execucao


def registrar_desperdicio(
    evento_id: str,
    itens_desperdicio: List[Dict],
    observacao_geral: str = ""
) -> Dict:
    """
    E. Cálculo de desperdício
    """
    print(f"🗑️  Registrando desperdício para evento: {evento_id}")
    
    execs = load_json("production_execution.json")
    custos = load_json("recipe_costs.json")
    
    custos_receitas = custos.get("receitas_calculadas", {})
    
    itens_final = []
    custo_total_perdido = 0
    custo_total_recuperado = 0
    
    for item in itens_desperdicio:
        rec_id = item.get("receita_id")
        quantidade = item.get("quantidade", 0)
        tipo = item.get("classificacao", "TIPO_C")
        
        custo_unit = custos_receitas.get(rec_id, {}).get("custo_por_porcao", 0)
        custo_perdido = quantidade * custo_unit
        
        # Valorização por tipo
        recuperacao = {
            "TIPO_A": 0.30,
            "TIPO_B": 0.10,
            "TIPO_C": 0.00,
            "TIPO_D": 0.00,
            "TIPO_E": 0.00
        }
        taxa_rec = recuperacao.get(tipo, 0)
        valor_recuperado = custo_perdido * taxa_rec
        
        custo_total_perdido += custo_perdido
        custo_total_recuperado += valor_recuperado
        
        itens_final.append({
            **item,
            "custo_perdido": round(custo_perdido, 2),
            "custo_recuperado": round(valor_recuperado, 2),
            "percentual_recuperacao": taxa_rec * 100
        })
    
    # Calcular percentual de desperdício
    # Buscar custo total do evento
    exec_evento = None
    for ex_id, ex in execs.get("execucoes", {}).items():
        if ex.get("evento_id") == evento_id:
            exec_evento = ex
            break
    
    custo_total_evento = exec_evento.get("totais", {}).get("custo_total_real", 0) if exec_evento else 0
    
    percentual_desperdicio = (custo_total_perdido / custo_total_evento * 100) if custo_total_evento else 0
    
    waste = load_json("waste_log.json")
    if "registros" not in waste:
        waste["registros"] = {}
    
    waste["registros"][evento_id] = {
        "evento_id": evento_id,
        "data_evento": exec_evento.get("data_execucao") if exec_evento else None,
        "itens_desperdiados": itens_final,
        "totais_desperdicio": {
            "custo_total_perdido": round(custo_total_perdido, 2),
            "custo_total_recuperado": round(custo_total_recuperado, 2),
            "custo_real_perdido": round(custo_total_perdido - custo_total_recuperado, 2),
            "percentual_desperdicio": round(percentual_desperdicio, 2),
            "benchmark": 5.0,
            "status": "dentro_benchmark" if percentual_desperdicio <= 5 else "atencao" if percentual_desperdicio <= 10 else "critico"
        },
        "observacao_geral": observacao_geral,
        "registrado_em": datetime.now().isoformat()
    }
    
    save_json("waste_log.json", waste)
    
    print(f"✅ Desperdício registrado")
    print(f"   Custo perdido: R$ {custo_total_perdido:,.2f} ({percentual_desperdicio:.1f}%)")
    
    return waste["registros"][evento_id]


def calcular_cmv_evento(evento_id: str) -> Dict:
    """
    F. CMV real por evento (Custo deMercadoria Vendida)
    """
    print(f"💰 Calculando CMV para evento: {evento_id}")
    
    plano = load_json("production_plan.json")
    execs = load_json("production_execution.json")
    waste = load_json("waste_log.json")
    
    evento = plano.get("eventos", {}).get(evento_id, {})
    
    # Buscar execução
    execucao = None
    for ex in execs.get("execucoes", {}).values():
        if ex.get("evento_id") == evento_id:
            execucao = ex
            break
    
    # Buscar desperdicio
    desperdicio = waste.get("registros", {}).get(evento_id, {})
    
    custo_real = execucao.get("totais", {}).get("custo_total_real", 0) if execucao else 0
    custo_planejado = evento.get("totais_previstos", {}).get("custo_total_comida", 0)
    custo_desperdicio = desperdicio.get("totais_desperdicio", {}).get("custo_total_perdido", 0)
    custo_recuperado = desperdicio.get("totais_desperdicio", {}).get("custo_total_recuperado", 0)
    
    num_convidados = evento.get("numero_convidados", 1)
    
    cmv = {
        "evento_id": evento_id,
        "nome_evento": evento.get("nome_evento"),
        "data_evento": evento.get("data_evento"),
        "numero_convidados": num_convidados,
        "custos": {
            "planejado": round(custo_planejado, 2),
            "real": round(custo_real, 2),
            "desperdicio": round(custo_desperdicio, 2),
            "recuperado": round(custo_recuperado, 2),
            "cmv_liquido": round(custo_real - custo_recuperado, 2),
            "variacao_percentual": round(((custo_real - custo_planejado) / custo_planejado * 100), 2) if custo_planejado else 0
        },
        "por_pessoa": {
            "custo_planejado": round(custo_planejado / num_convidados, 2),
            "custo_real": round(custo_real / num_convidados, 2),
            "custo_desperdicio": round(custo_desperdicio / num_convidados, 2),
            "cmv_liquido": round((custo_real - custo_recuperado) / num_convidados, 2)
        },
        "indicadores": {
            "eficiencia_percentual": round(100 - desperdicio.get("totais_desperdicio", {}).get("percentual_desperdicio", 0), 2),
            "status": "ok" if (custo_desperdicio / custo_real * 100 if custo_real else 0) <= 5 else "review"
        },
        "calculado_em": datetime.now().isoformat()
    }
    
    print(f"\n{'='*50}")
    print(f"📊 CMV EVENTO: {evento.get('nome_evento')}")
    print(f"{'='*50}")
    print(f"CMV Total: R$ {cmv['custos']['cmv_liquido']:,.2f}")
    print(f"Por Pessoa: R$ {cmv['por_pessoa']['cmv_liquido']:.2f}")
    print(f"Eficiência: {cmv['indicadores']['eficiencia_percentual']:.1f}%")
    print(f"Status: {cmv['indicadores']['status']}")
    
    return cmv


def sugerir_otimizacao(evento_id: str = None) -> List[Dict]:
    """
    Analisa dados e sugere otimizações
    """
    planos = load_json("production_plan.json")
    execs = load_json("production_execution.json")
    
    sugestoes = []
    
    # Verificar todos os eventos com dados de execução
    for ex_id, exc in execs.get("execucoes").items() if execs.get("execucoes") else []:
        ev_id = exc.get("evento_id")
        ev = planos.get("eventos", {}).get(ev_id, {})
        
        variacao = exc.get("totais", {}).get("variacao_custo_planejado", 0)
        
        if variacao > 10:
            sugestoes.append({
                "evento": ev.get("nome_evento"),
                "tipo": "custo_excedido",
                "mensagem": f"Custo real {variacao:.1f}% acima esperado",
                "acao": "Revisar precos de fornecedores ou fator de sobriga"
            })
    
    # Checar desperdícios
    waste = load_json("waste_log.json")
    for ev_id, wst in waste.get("registros", {}).items():
        if wst.get("totais_desperdicio", {}).get("status") == "critico":
            sugestoes.append({
                "evento": planos.get("eventos", {}).get(ev_id, {}).get("nome_evento"),
                "tipo": "desperdicio_critico",
                "mensagem": "Desperdício acima de 15%",
                "acao": "URGENTE: Revisar processos de preparo e armazenamento"
            })
    
    if sugestoes:
        print(f"\n💡 {len(sugestoes)} SUGESTÕES DE OTIMIZAÇÃO:")
        for s in sugestoes:
            print(f"   [{s['tipo']}] {s['mensagem']}")
            print(f"   → {s['acao']}")
    else:
        print("\n✅ Nenhuma otimização necessária no momento")
    
    return sugestoes


if __name__ == "__main__":
    # Testar o engine
    print("="*60)
    print("🍳 KITCHEN INTELLIGENCE ENGINE - Testes")
    print("="*60)
    
    # 1. Atualizar custos
    print("\n--- A. Cálculo de Custo por Receita ---")
    custos = atualizar_custos_receitas()
    
    # 2. Criar plano de evento
    print("\n--- B. Planejamento de Produção ---")
    plano = criar_plano_producao(
        evento_id="EVT001",
        nome_evento="Casamento Teste",
        data_evento="2026-04-15",
        num_convidados=120,
        tipo_servico="buffet_completo"
    )
    
    # 3. Check estoque
    print("\n--- C. Integração com Estoque ---")
    estoque = check_estoque_disponivel("EVT001")
    print(f"   Ítens verificados: {estoque['items_verificados']}")
    
    print("\n✅ Kitchen Intelligence Engine pronto!")
