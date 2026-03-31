#!/usr/bin/env python3
"""
Kitchen Intelligence Engine - CLI Interface
Comandos interativos para gerenciamento de cozinha
"""

import sys
import json
from datetime import datetime
from kitchen_engine import (
    atualizar_custos_receitas,
    criar_plano_producao,
    check_estoque_disponivel,
    registrar_producao_real,
    registrar_desperdicio,
    calcular_cmv_evento,
    sugerir_otimizacao,
    load_json,
    save_json
)


def print_menu():
    print("\n" + "="*60)
    print("🍳 KITCHEN INTELLIGENCE ENGINE - Menu Principal")
    print("="*60)
    print("\n1. 📊 Atualizar custos de receitas (integra com estoque)")
    print("2. 📝 Criar plano de produção para evento")
    print("3. 📦 Verificar disponibilidade de estoque")
    print("4. 🍽️  Registrar produção real executada")
    print("5. 🗑️  Registrar desperdício/post-evento")
    print("6. 💰 Calcular CMV de evento")
    print("7. 💡 Sugestões de otimização")
    print("8. 📈 Ver relatório de evento completo")
    print("0. ❌ Sair")
    print("="*60)


def cmd_atualizar_custos():
    print("\n🔄 Atualizando custos com base no inventário atual...")
    resultado = atualizar_custos_receitas()
    
    if "erro" in resultado:
        print(f"   ❌ Erro: {resultado['erro']}")
        return
    
    print(f"\n✅ {resultado['_meta']['receitas_calculadas']} receitas atualizadas")
    
    if resultado['analise_comparativa']['receita_mais_cara']:
        mais_cara = resultado['analise_comparativa']['receita_mais_cara']
        print(f"   💰 Mais cara: {mais_cara['nome']} (R$ {mais_cara['custo']:.2f}/porção)")
    
    if resultado['analise_comparativa']['receita_mais_barata']:
        mais_barata = resultado['analise_comparativa']['receita_mais_barata']
        print(f"   💵 Mais barata: {mais_barata['nome']} (R$ {mais_barata['custo']:.2f}/porção)")
    
    print(f"\n   📊 Custo médio por porção: R$ {resultado['analise_comparativa']['custo_medio_porcao']:.2f}")


def cmd_criar_plano():
    print("\n📝 NOVO PLANO DE PRODUÇÃO")
    print("-"*40)
    
    evento_id = input("ID do evento (ex: EVT001): ").strip()
    nome = input("Nome do evento: ").strip()
    data = input("Data do evento (YYYY-MM-DD): ").strip()
    convidados = int(input("Número de convidados: "))
    
    print("\nTipo de serviço:")
    print("  1. buffet_completo")
    print("  2. coquetel")
    print("  3. coffee_break")
    print("  4. jantar_servido")
    tipo_num = input("Escolha (1-4, default=1): ").strip() or "1"
    
    tipos = {"1": "buffet_completo", "2": "coquetel", "3": "coffee_break", "4": "jantar_servido"}
    tipo = tipos.get(tipo_num, "buffet_completo")
    
    resultado = criar_plano_producao(
        evento_id=evento_id,
        nome_evento=nome,
        data_evento=data,
        num_convidados=convidados,
        tipo_servico=tipo
    )
    
    print(f"\n✅ Plano criado: {resultado['evento_id']}")
    print(f"   Custo total estimado: R$ {resultado['totais_previstos']['custo_total_comida']:,.2f}")
    print(f"   Custo por pessoa: R$ {resultado['totais_previstos']['custo_por_pessoa']:.2f}")


def cmd_check_estoque():
    print("\n📦 VERIFICAÇÃO DE ESTOQUE")
    print("-"*40)
    
    evento_id = input("ID do evento: ").strip()
    
    resultado = check_estoque_disponivel(evento_id)
    
    if "erro" in resultado:
        print(f"   ❌ {resultado['erro']}")
        return
    
    print(f"\n   Status geral: {resultado['status_geral']}")
    print(f"   Ítens verificados: {resultado['items_verificados']}")
    
    if resultado['items_faltantes'] > 0:
        print(f"\n   ⚠️  {resultado['items_faltantes']} ITENS FALTANDO:")
        for item in resultado['compra_sugerida']:
            print(f"   • {item['nome']}: falta {abs(item['diferenca']):.3f} {item['unidade']}")
    else:
        print(f"\n   ✅ Estoque suficiente para produção!")


def cmd_registrar_producao():
    print("\n🍽️ REGISTRO DE PRODUÇÃO REAL")
    print("-"*40)
    
    execucao_id = input("ID da execução (ex: EXEC001): ").strip()
    evento_id = input("ID do evento vinculado: ").strip()
    
    plano = load_json("production_plan.json")
    evento = plano.get("eventos", {}).get(evento_id, {})
    
    if not evento:
        print("   ❌ Evento não encontrado no plano.")
        return
    
    print(f"\n   Evento: {evento.get('nome_evento')}")
    print("   Cardápio planejado:")
    
    for categoria, itens in evento.get("cardapio", {}).items():
        if itens:
            print(f"\n   [{categoria.upper()}]")
            for i, item in enumerate(itens):
                print(f"      {i+1}. {item['nome']} - {item['porcoes_previstas']} porções")
    
    print("\n   Registre a produção real (deixe em branco para usar planejado):")
    
    receitas_executadas = []
    for categoria, itens in evento.get("cardapio", {}).items():
        for item in itens:
            print(f"\n   > {item['nome']}")
            planejado = item.get("porcoes_previstas", 0)
            produzido = input(f"     Porções produzidas (planejado: {planejado}): ").strip()
            produzido = int(produzido) if produzido else planejado
            
            servido = input(f"     Porções servidas: ").strip()
            servido = int(servido) if servido else produzido
            
            receitas_executadas.append({
                "receita_id": item['receita_id'],
                "nome": item['nome'],
                "porcoes_planejadas": planejado,
                "porcoes_produzidas": produzido,
                "porcoes_servidas": servido
            })
    
    resultado = registrar_producao_real(execucao_id, evento_id, receitas_executadas)
    
    print(f"\n✅ Produção registrada!")
    print(f"   Custo total real: R$ {resultado['totais']['custo_total_real']:,.2f}")
    print(f"   Variação: {resultado['totais']['variacao_custo_planejado']:.1f}%")


def cmd_registrar_desperdicio():
    print("\n🗑️ REGISTRO DE DESPERDÍCIO")
    print("-"*40)
    
    evento_id = input("ID do evento: ").strip()
    
    execs = load_json("production_execution.json")
    execucao = None
    for ex in execs.get("execucoes", {}).values():
        if ex.get("evento_id") == evento_id:
            execucao = ex
            break
    
    if not execucao:
        print("   ❌ Nenhuma execução encontrada para este evento.")
        return
    
    print(f"\n   Evento: {execucao['nome_evento']}")
    print(f"   Custo total: R$ {execucao['totais']['custo_total_real']:,.2f}")
    
    itens = []
    
    print("\n   Registre as sobras:")
    for rec in execucao.get("receitas_executadas", []):
        sobras = rec.get("porcoes_restantes", 0)
        if sobras > 0:
            print(f"\n   > {rec['nome']}: {sobras} porções sobraram")
            
            print("   Classificação:")
            print("     A - Sobra aproveitável (staff)")
            print("     B - Sobra para doação")
            print("     C - Sobra não aproveitável")
            print("     D - Erro de preparo")
            print("     E - Material estragado")
            
            tipo = input("     Tipo (A-E, default=C): ").strip().upper() or "C"
            classificacao = f"TIPO_{tipo}"
            
            destino = input("     Destino final: ").strip() or "Descarte"
            
            itens.append({
                "receita_id": rec['receita_id'],
                "nome": rec['nome'],
                "quantidade": sobras,
                "classificacao": classificacao,
                "destino_final": destino
            })
    
    obs = input("\nObservações gerais: ").strip()
    
    resultado = registrar_desperdicio(evento_id, itens, obs)
    
    print(f"\n✅ Desperdício registrado!")
    print(f"   Custo perdido: R$ {resultado['totais_desperdicio']['custo_total_perdido']:,.2f}")
    print(f"   Percentual: {resultado['totais_desperdicio']['percentual_desperdicio']:.1f}%")
    print(f"   Status: {resultado['totais_desperdicio']['status']}")


def cmd_calcular_cmv():
    print("\n💰 CÁLCULO DE CMV (Custo de Mercadoria Vendida)")
    print("-"*40)
    
    evento_id = input("ID do evento: ").strip()
    
    cmv = calcular_cmv_evento(evento_id)
    
    print(f"\n{'='*50}")
    print(f"📊 RESULTADO CMV")
    print(f"{'='*50}")
    print(f"Evento: {cmv['nome_evento']}")
    print(f"Data: {cmv['data_evento']}")
    print(f"Convidados: {cmv['numero_convidados']}")
    print(f"\n--- CUSTOS ---")
    print(f"  Planejado:  R$ {cmv['custos']['planejado']:,.2f}")
    print(f"  Real:       R$ {cmv['custos']['real']:,.2f}")
    print(f"  Desperdício: R$ {cmv['custos']['desperdicio']:,.2f}")
    print(f"  ════════════════════════════")
    print(f"  CMV LÍQUIDO: R$ {cmv['custos']['cmv_liquido']:,.2f}")
    print(f"\n--- POR PESSOA ---")
    print(f"  Planejado:  R$ {cmv['por_pessoa']['custo_planejado']:.2f}")
    print(f"  Real:       R$ {cmv['por_pessoa']['custo_real']:.2f}")
    print(f"  CMV Líquido: R$ {cmv['por_pessoa']['cmv_liquido']:.2f}")
    print(f"\n--- EFICIÊNCIA ---")
    print(f"  Eficiência: {cmv['indicadores']['eficiencia_percentual']:.1f}%")
    print(f"  Status: {cmv['indicadores']['status']}")
    print(f"{'='*50}")


def cmd_sugestoes():
    print("\n💡 ANÁLISE DE OTIMIZAÇÃO")
    print("-"*40)
    
    sugestoes = sugerir_otimizacao()
    
    if not sugestoes:
        print("\n   ✅ Nenhuma otimização necessária!")
        print("      Todos os eventos estão performando dentro dos parâmetros.")


def cmd_relatorio_completo():
    print("\n📈 RELATÓRIO COMPLETO DE EVENTO")
    print("-"*40)
    
    evento_id = input("ID do evento: ").strip()
    
    plano = load_json("production_plan.json")
    execs = load_json("production_execution.json")
    waste = load_json("waste_log.json")
    
    ev_plano = plano.get("eventos", {}).get(evento_id, {})
    
    exec_evento = None
    for ex in execs.get("execucoes", {}).values():
        if ex.get("evento_id") == evento_id:
            exec_evento = ex
            break
    
    waste_evento = waste.get("registros", {}).get(evento_id, {})
    
    if not ev_plano:
        print("   ❌ Evento não encontrado.")
        return
    
    print(f"\n{'='*60}")
    print(f"📋 RELATÓRIO: {ev_plano.get('nome_evento', 'Desconhecido')}")
    print(f"{'='*60}")
    print(f"ID: {evento_id}")
    print(f"Data: {ev_plano.get('data_evento')}")
    print(f"Convidados: {ev_plano.get('numero_convidados')}")
    print(f"Tipo: {ev_plano.get('tipo_servico')}")
    
    print(f"\n📝 PLANEJAMENTO:")
    print(f"   Custo estimado: R$ {ev_plano.get('totais_previstos', {}).get('custo_total_comida', 0):,.2f}")
    print(f"   Por pessoa: R$ {ev_plano.get('totais_previstos', {}).get('custo_por_pessoa', 0):,.2f}")
    
    if exec_evento:
        print(f"\n🍽️ EXECUÇÃO:")
        print(f"   Custo real: R$ {exec_evento['totais']['custo_total_real']:,.2f}")
        print(f"   Por pessoa: R$ {exec_evento['totais']['custo_por_pessoa_real']:,.2f}")
        print(f"   Variação: {exec_evento['totais']['variacao_custo_planejado']:.1f}%")
    else:
        print("\n🍽️ EXECUÇÃO: Não registrada")
    
    if waste_evento:
        print(f"\n🗑️ DESPERDÍCIO:")
        print(f"   Custo perdido: R$ {waste_evento['totais_desperdicio']['custo_total_perdido']:,.2f}")
        print(f"   Percentual: {waste_evento['totais_desperdicio']['percentual_desperdicio']:.1f}%")
        print(f"   Status: {waste_evento['totais_desperdicio']['status']}")
    else:
        print("\n🗑️ DESPERDÍCIO: Não registrado")
    
    print(f"\n{'='*60}")


def main():
    print("\n" + "🍳 " * 20)
    print("  KITCHEN INTELLIGENCE ENGINE (KIE)")
    print("  Sistema de Gestão de Produção e Custo")
    print("🍳 " * 20)
    
    while True:
        print_menu()
        cmd = input("\nEscolha: ").strip()
        
        if cmd == "1":
            cmd_atualizar_custos()
        elif cmd == "2":
            cmd_criar_plano()
        elif cmd == "3":
            cmd_check_estoque()
        elif cmd == "4":
            cmd_registrar_producao()
        elif cmd == "5":
            cmd_registrar_desperdicio()
        elif cmd == "6":
            cmd_calcular_cmv()
        elif cmd == "7":
            cmd_sugestoes()
        elif cmd == "8":
            cmd_relatorio_completo()
        elif cmd == "0" or cmd.lower() == "sair":
            print("\n✅ Até logo!")
            break
        else:
            print("\n❌ Opção inválida.")


if __name__ == "__main__":
    main()
