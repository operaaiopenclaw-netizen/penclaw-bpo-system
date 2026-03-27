#!/usr/bin/env python3
# cli.py - Orkestra Command Line Interface
# Interface de linha de comando para operar o sistema

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add orkestra to path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "agents"))

try:
    from evaluator_simple import evaluate_event, evaluate_event_detailed
except ImportError:
    # Fallback
    def evaluate_event(event):
        margin = event.get("margin", 0)
        if margin < 0: return "REJECT"
        if margin < 0.3: return "REVIEW"
        return "APPROVE"
    
    def evaluate_event_detailed(event):
        margin = event.get("margin", 0)
        return {
            "decision": evaluate_event(event),
            "rationale": f"Margem: {margin:.1%}",
            "recommendations": []
        }


def print_header():
    """Print header Orkestra."""
    print("\n" + "=" * 60)
    print("🎛️  ORKESTRA - Sistema de Gestão de Eventos")
    print("=" * 60)


def print_footer():
    """Print footer."""
    print("=" * 60)


def cmd_status():
    """Mostra status do sistema."""
    print_header()
    print("\n📊 STATUS DO SISTEMA")
    print("-" * 40)
    
    # Contar arquivos de memória
    mem_dir = Path("memory")
    if mem_dir.exists():
        decisions = len(json.loads((mem_dir / "decisions.json").read_text()).get("decisions", [])) if (mem_dir / "decisions.json").exists() else 0
        errors = len(json.loads((mem_dir / "errors.json").read_text()).get("errors", [])) if (mem_dir / "errors.json").exists() else 0
        perf = len(json.loads((mem_dir / "performance.json").read_text()).get("records", [])) if (mem_dir / "performance.json").exists() else 0
        
        print(f"   🧠 Decisões registradas: {decisions}")
        print(f"   ⚠️  Erros registrados: {errors}")
        print(f"   📈 Registros de performance: {perf}")
    else:
        print("   ⚠️  Memória não inicializada")
    
    print("\n   🚀 Módulos disponíveis:")
    print("      ✅ Análise Financeira")
    print("      ✅ Avaliação de Viabilidade")
    print("      ✅ Learning Engine")
    print("      ✅ Procurement Intelligence")
    
    print_footer()


def cmd_analyze(data_file: str = None):
    """Executa análise financeira."""
    print_header()
    print("\n📊 ANÁLISE FINANCEIRA")
    print("-" * 40)
    
    filepath = data_file or "financial_log.json"
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        transactions = data.get("transactions", [])
        print(f"   ✅ {len(transactions)} transações carregadas")
        
        # Analisar por evento
        events = {}
        for t in transactions:
            event = t.get("event", "unknown")
            if event not in events:
                events[event] = {"income": 0, "expense": 0}
            
            if t.get("type") == "income":
                events[event]["income"] += t.get("value", 0)
            else:
                events[event]["expense"] += t.get("value", 0)
        
        print(f"\n   📍 {len(events)} eventos identificados:\n")
        
        for name, values in events.items():
            income = values["income"]
            expense = values["expense"]
            margin = (income - expense) / income if income > 0 else 0
            
            print(f"   🎯 {name}")
            print(f"      💰 Receita: R$ {income:,.0f}")
            print(f"      💸 Custo: R$ {expense:,.0f}")
            print(f"      📈 Margem: {margin*100:.1f}%")
            print()
        
    except FileNotFoundError:
        print(f"   ❌ Arquivo não encontrado: {filepath}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print_footer()


def cmd_evaluate(event_name: str = None, revenue: float = None, cost: float = None):
    """Avalia viabilidade de um evento."""
    print_header()
    print("\n🎯 AVALIAÇÃO DE VIABILIDADE")
    print("-" * 40)
    
    # Se não recebeu dados, perguntar
    if event_name is None:
        print("   Digite os dados do evento:\n")
        try:
            event_name = input("   Nome do evento: ")
            revenue = float(input("   Receita esperada (R$): ").replace(",", "").replace(".", ""))
            cost = float(input("   Custo estimado (R$): ").replace(",", "").replace(".", ""))
        except (ValueError, KeyboardInterrupt):
            print("\n   ❌ Entrada cancelada")
            return
    
    margin = (revenue - cost) / revenue if revenue > 0 else 0
    
    event = {
        "name": event_name,
        "revenue": revenue,
        "cost": cost,
        "margin": margin
    }
    
    decision = evaluate_event(event)
    detailed = evaluate_event_detailed(event)
    
    print(f"\n   📍 Evento: {event_name}")
    print(f"   💰 Receita: R$ {revenue:,.0f}")
    print(f"   💸 Custo: R$ {cost:,.0f}")
    print(f"   📊 Margem: {margin*100:.1f}%")
    
    icon = "✅" if decision == "APPROVE" else "⚠️" if decision == "REVIEW" else "❌"
    print(f"\n   {icon} DECISÃO: {decision}")
    print(f"   💭 {detailed['rationale']}")
    
    if detailed.get("recommendations"):
        print(f"\n   📋 Sugestões:")
        for rec in detailed['recommendations'][:3]:
            print(f"      - {rec}")
    
    print_footer()


def cmd_learning():
    """Executa Learning Engine."""
    print_header()
    print("\n🧠 LEARNING ENGINE")
    print("-" * 40)
    
    try:
        import subprocess
        result = subprocess.run(
            ["python3", "orkestra/engine/learning_engine.py"],
            capture_output=False,
            text=True
        )
        if result.returncode != 0:
            print(f"   ⚠️  Learning Engine retornou código {result.returncode}")
    except Exception as e:
        print(f"   ❌ Erro ao executar Learning Engine: {e}")
    
    print_footer()


def cmd_pipeline():
    """Executa pipeline completo."""
    print_header()
    print("\n🚀 EXECUTANDO PIPELINE COMPLETO")
    print("-" * 40)
    
    try:
        import subprocess
        result = subprocess.run(
            ["python3", "orkestra/engine/orchestrator.py"],
            capture_output=False,
            text=True
        )
        if result.returncode != 0:
            print(f"   ⚠️  Pipeline retornou código {result.returncode}")
    except Exception as e:
        print(f"   ❌ Erro ao executar pipeline: {e}")
    
    print_footer()


def cmd_help():
    """Mostra ajuda."""
    print("""
🎛️  ORKESTRA CLI - Comandos disponíveis:

  status          Mostra status do sistema
  analyze         Análise financeira dos dados
  evaluate        Avalia viabilidade de evento
  learning        Executa Learning Engine
  pipeline        Executa pipeline completo
  help            Mostra esta ajuda

Exemplos:
  python orkestra/cli.py status
  python orkestra/cli.py analyze
  python orkestra/cli.py evaluate
  python orkestra/cli.py pipeline
    """)


def main():
    """Entry point principal."""
    parser = argparse.ArgumentParser(
        description="Orkestra - Sistema de Gestão de Eventos",
        prog="orkestra"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")
    
    # Status
    subparsers.add_parser("status", help="Mostra status do sistema")
    
    # Analyze
    analyze_parser = subparsers.add_parser("analyze", help="Análise financeira")
    analyze_parser.add_argument("--file", "-f", help="Arquivo de dados JSON")
    
    # Evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Avalia viabilidade de evento")
    
    # Learning
    subparsers.add_parser("learning", help="Executa Learning Engine")
    
    # Pipeline
    subparsers.add_parser("pipeline", help="Executa pipeline completo")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        cmd_help()
        return
    
    commands = {
        "status": cmd_status,
        "analyze": lambda: cmd_analyze(args.file),
        "evaluate": cmd_evaluate,
        "learning": cmd_learning,
        "pipeline": cmd_pipeline,
        "help": cmd_help
    }
    
    if args.command in commands:
        commands[args.command]()
    else:
        print(f"❌ Comando desconhecido: {args.command}")


if __name__ == "__main__":
    main()
