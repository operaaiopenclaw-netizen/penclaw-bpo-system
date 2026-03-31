#!/usr/bin/env python3
"""
KITCHEN INTELLIGENCE ENGINE v2 - CONTROL LAYER
Camada de validação, rastreabilidade e conformidade

REGRAS FUNDAMENTAIS:
- NUNCA assumir dados inexistentes
- SEMPRE marcar trace_mode (direct | inferred | allocated)
- SEMPRE registrar inconsistências em errors.json
- Custo SEMPRE baseado em média ponderada do estoque
- Toda produção exige baixa em estoque
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

DATA_DIR = Path(__file__).parent / "kitchen_data"


def load_json(filename: str) -> Dict:
    filepath = DATA_DIR / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_json(filename: str, data: Dict):
    filepath = DATA_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_timestamp() -> str:
    return datetime.now().isoformat()


def log_error(error_type: str, severity: str, event_id: Optional[str], 
              description: str, source: str = "control_layer"):
    """Registra erro em errors.json"""
    errors = load_json("errors.json")
    
    if "errors" not in errors:
        errors["errors"] = []
    
    error_entry = {
        "timestamp": get_timestamp(),
        "type": error_type,
        "severity": severity,
        "event_id": event_id,
        "description": description,
        "source": source
    }
    
    errors["errors"].append(error_entry)
    errors["_meta"] = {
        "last_updated": get_timestamp(),
        "total_errors": len(errors["errors"])
    }
    
    save_json("errors.json", errors)
    
    emoji = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}
    print(f"{emoji.get(severity, '⚠️')} [{severity.upper()}] {error_type}: {description}")


def validate_recipe_structure(recipe_id: str, recipe: Dict) -> Tuple[bool, List[str]]:
    """
    2. Validar estrutura de receita OBRIGATÓRIA
    """
    errors = []
    
    # Verificar campos obrigatórios
    for field in ["name", "category", "yield", "ingredients"]:
        if field not in recipe and field not in ["yield", "rendimento"]:
            field_alt = "rendimento" if field == "yield" else field
            if field_alt not in recipe:
                errors.append(f"Campo obrigatório ausente: {field}")
    
    # Validar ingredientes
    ingredients = recipe.get("ingredients", recipe.get("ingredientes", []))
    if not ingredients:
        errors.append("ERRO CRÍTICO: Receita sem ingredientes")
    
    for idx, ing in enumerate(ingredients):
        # Aceitar item_id ou codigo_inv
        item_id = ing.get("item_id") or ing.get("codigo_inv") or ing.get("codigo")
        quantity = ing.get("quantity") or ing.get("quantidade_por_porcao") or ing.get("quantidade")
        unit = ing.get("unit") or ing.get("unidade")
        
        if not item_id:
            errors.append(f"Ingrediente {idx}: sem item_id/codigo")
        if quantity is None:
            errors.append(f"Ingrediente {idx}: sem quantidade")
        if not unit:
            errors.append(f"Ingrediente {idx}: sem unidade")
        
        # Verificar item existe no inventário
        if item_id:
            inventory = load_json("inventory.json")
            items = [i.get("codigo") for i in inventory.get("inventory", [])]
            if item_id not in items and items:  # Só checa se inventário tiver dados
                errors.append(f"Ingrediente {item_id}: não encontrado no inventário")
    
    is_critical = any("ERRO CRÍTICO" in e for e in errors)
    
    if errors:
        log_error(
            error_type="recipe_validation_failed",
            severity="high" if is_critical else "medium",
            event_id=None,
            description=f"Receita {recipe_id}: {'; '.join(errors[:3])}",
            source="validate_recipe_structure"
        )
    
    return not is_critical, errors


def validate_event_record(event_id: str, record: Dict, source: str = "control_layer") -> Dict:
    """
    1. Padronização obrigatória de dados
    """
    validated = record.copy()
    
    # Garantir event_id
    if "event_id" not in validated:
        if event_id:
            validated["event_id"] = event_id
        else:
            validated["event_id"] = f"ALLOC_{get_timestamp()}"
            validated["trace_mode"] = "allocated"
            log_error(
                error_type="missing_event_id",
                severity="high",
                event_id=validated["event_id"],
                description=f"Registro sem event_id - forçado trace_mode=allocated",
                source=source
            )
    
    # Garantir campos obrigatórios
    if "company" not in validated:
        validated["company"] = ""  # Sinalizar para preenchimento
        log_error(
            error_type="missing_company",
            severity="high",
            event_id=validated["event_id"],
            description="Campo 'company' obrigatório - não preenchido",
            source=source
        )
    
    if "timestamp" not in validated:
        validated["timestamp"] = get_timestamp()
    
    validated["source"] = source
    
    # Garantir trace_mode
    if "trace_mode" not in validated:
        validated["trace_mode"] = "direct"
    
    # Validar trace_mode
    if validated["trace_mode"] not in ["direct", "inferred", "allocated"]:
        log_error(
            error_type="invalid_trace_mode",
            severity="medium",
            event_id=validated["event_id"],
            description=f"trace_mode inválido: {validated.get('trace_mode')}",
            source=source
        )
    
    return validated


def calculate_weighted_average_cost(item_id: str) -> Tuple[Optional[float], str, float]:
    """
    3. COST ENGINE - Custo médio ponderado OBRIGATÓRIO
    
    Retorna: (custo, source, confidence_score)
    """
    inventory = load_json("inventory.json")
    
    for item in inventory.get("inventory", []):
        if item.get("codigo") == item_id:
            # Buscar histórico de preços ponderado
            historico = item.get("historico_entradas", [])
            if historico:
                total_valor = 0.0
                total_qtd = 0.0
                
                for entrada in historico:
                    qtd = entrada.get("quantidade", 0)
                    preco = entrada.get("preco_unitario", 0)
                    if qtd > 0 and preco > 0:
                        total_valor += qtd * preco
                        total_qtd += qtd
                
                if total_qtd > 0:
                    custo = total_valor / total_qtd
                    return round(costo, 2), "inventory_avg_weighted", 1.0
            
            # Sem histórico - usar preço unitário atual
            preco = item.get("preco_unitario", 0)
            if preco > 0:
                log_error(
                    error_type="cost_fallback",
                    severity="medium",
                    event_id=None,
                    description=f"Item {item_id}: usando preco atual (sem historico ponderado)",
                    source="calculate_weighted_average_cost"
                )
                return preco, "inventory_current_fallback", 0.7
            
            # Sem preço
            log_error(
                error_type="cost_missing",
                severity="high",
                event_id=None,
                description=f"Item {item_id}: sem preço definido no inventario",
                source="calculate_weighted_average_cost"
            )
            return None, "not_found", 0.0
    
    log_error(
        error_type="item_not_found",
        severity="high",
        event_id=None,
        description=f"Item {item_id}: não existe no inventario",
        source="calculate_weighted_average_cost"
    )
    return None, "not_found", 0.0


def check_estoque_baixa(event_id: str, production_id: str, items: List[Dict]) -> Tuple[bool, List[str], List[dict]]:
    """
    4. PRODUÇÃO → ESTOQUE - Verifica se há baixa automática
    Retorna: (ok, erros, baixas_sugeridas)
    """
    errors = []
    baixas = []
    
    # Verificar se existe baixa registrada para esta produção
    inventory = load_json("inventory.json")
    baixas_registradas = []  # TODO: implementar tracking de baixas
    
    for item in items:
        item_id = item.get("item_id") or item.get("codigo_inv")
        qtd = item.get("quantity") or item.get("quantidade")
        
        # Verificar disponibilidade
        inv_item = None
        for inv in inventory.get("inventory", []):
            if inv.get("codigo") == item_id:
                inv_item = inv
                break
        
        if not inv_item:
            errors.append(f"Item {item_id} não existe no estoque")
            continue
        
        qtd_atual = inv_item.get("quantidade_atual", 0)
        if qtd_atual < qtd:
            errors.append(f"Item {item_id}: estoque insuficiente ({qtd_atual:.3f} < {qtd:.3f})")
        
        # Registrar baixa sugerida
        baixas.append({
            "item_id": item_id,
            "quantidade_baixa": qtd,
            "quantidade_anterior": qtd_atual,
            "quantidade_nova": round(qtd_atual - qtd, 3),
            "production_id": production_id,
            "event_id": event_id,
            "timestamp": get_timestamp(),
            "trace_mode": "direct",
            "source": "check_estoque_baixa"
        })
    
    if errors:
        log_error(
            error_type="production_baixa_failed",
            severity="high",
            event_id=event_id,
            description=f"Producao {production_id}: {'; '.join(errors[:3])}",
            source="check_estoque_baixa"
        )
    
    return len(errors) == 0, errors, baixas


def calcular_consumo_real(event_id: str, production_data: Dict) -> List[Dict]:
    """
    5. CONSUMO REAL - Gera consumo baseado em produção_executada × ficha_técnica
    """
    consumos = []
    recipes = load_json("recipes.json")
    
    for receita_exec in production_data.get("receitas_executadas", []):
        rec_id = receita_exec.get("receita_id")
        porcoes_produzidas = receita_exec.get("porcoes_produzidas", 0)
        
        receita = recipes.get("receitas", {}).get(rec_id, {})
        if not receita:
            log_error(
                error_type="recipe_not_found_for_consumption",
                severity="high",
                event_id=event_id,
                description=f"Receita {rec_id} nao encontrada para calcular consumo",
                source="calcular_consumo_real"
            )
            continue
        
        # Calcular multiplicador baseado em rendimento
        rendimento = receita.get("rendimento_porca", 1)
        if rendimento == 0:
            rendimento = 1
        
        fator = porcoes_produzidas / rendimento
        
        ingredientes = receita.get("ingredientes", [])
        for ing in ingredientes:
            qtd_base = ing.get("quantidade_por_porcao", 0)
            qtd_real = qtd_base * fator
            
            if qtd_real > 0:
                consumos.append({
                    "event_id": event_id,
                    "recipe_id": rec_id,
                    "item_id": ing.get("codigo_inv"),
                    "item_name": ing.get("nome"),
                    "quantity_used": round(qtd_real, 4),
                    "unit": ing.get("unidade"),
                    "trace_mode": "direct",
                    "source": "calcular_consumo_real",
                    "timestamp": get_timestamp()
                })
    
    return consumos


def calcular_desperdicio(event_id: str, production_data: Dict) -> List[Dict]:
    """
    6. DESPERDÍCIO - Classificar sobras e perdas
    """
    desperdicios = []
    
    for receita in production_data.get("receitas_executadas", []):
        planejado = receita.get("porcoes_planejadas", 0)
        produzido = receita.get("porcoes_produzidas", 0)
        servido = receita.get("porcoes_servidas", 0)
        
        # Tipos de desperdício
        if produzido > planejado:
            # Sobreposição - operacional
            qtd = produzido - planejado
            desperdicios.append({
                "event_id": event_id,
                "recipe_id": receita.get("receita_id"),
                "tipo": "operacional",
                "subtipo": "sobreposicao",
                "quantidade": qtd,
                "descricao": f"Produzido {qtd} a mais que planejado"
            })
        
        if produzido < planejado:
            # Erro de estimativa
            qtd = planejado - produzido
            desperdicios.append({
                "event_id": event_id,
                "recipe_id": receita.get("receita_id"),
                "tipo": "estimativa",
                "subtipo": "subproducao",
                "quantidade": qtd,
                "descricao": f"Produzido {qtd} a menos que planejado"
            })
        
        # Sobra não servida
        sobra = produzido - servido
        if sobra > 0:
            desperdicios.append({
                "event_id": event_id,
                "recipe_id": receita.get("receita_id"),
                "tipo": "sobra",
                "subtipo": "nao_servido",
                "quantidade": sobra,
                "descricao": f"Sobra de {sobra} unidades não servidas"
            })
    
    # Salvar em waste_log
    waste = load_json("waste_log.json")
    if "registros" not in waste:
        waste["registros"] = {}
    
    if event_id not in waste["registros"]:
        waste["registros"][event_id] = {"consumo": [], "desperdicio": []}
    
    waste["registros"][event_id]["consumo"] = calcular_consumo_real(event_id, production_data)
    waste["registros"][event_id]["desperdicio"] = desperdicios
    waste["registros"][event_id]["timestamp"] = get_timestamp()
    
    save_json("waste_log.json", waste)
    
    return desperdicios


def calcular_cmv_evento_v2(event_id: str, company: str) -> Dict:
    """
    7. CMV POR EVENTO - Com confidence_score
    """
    waste = load_json("waste_log.json")
    cmv_data = {"event_id": event_id, "company": company, "items": []}
    
    cmv_total = 0.0
    confidence_scores = []
    
    event_waste = waste.get("registros", {}).get(event_id, {})
    consumos = event_waste.get("consumo", [])
    
    for consumo in consumos:
        item_id = consumo.get("item_id")
        qtd = consumo.get("quantity_used", 0)
        
        custo, source, confidence = calculate_weighted_average_cost(item_id)
        
        if custo and qtd:
            custo_total = custo * qtd
            cmv_total += custo_total
            
            cmv_data["items"].append({
                "item_id": item_id,
                "quantity": qtd,
                "cost_unit": custo,
                "cost_total": round(custo_total, 2),
                "cost_source": source,
                "confidence": confidence
            })
            
            confidence_scores.append(confidence)
    
    # Calcular confidence médio
    if confidence_scores:
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
    else:
        avg_confidence = 0.0
        log_error(
            error_type="cmv_no_data",
            severity="high",
            event_id=event_id,
            description="Nenhum dado de consumo encontrado para calcular CMV",
            source="calcular_cmv_evento_v2"
        )
    
    cmv_data["cmv_total"] = round(cmv_total, 2)
    cmv_data["cost_confidence_score"] = round(avg_confidence, 2)
    cmv_data["timestamp"] = get_timestamp()
    
    # Salvar
    cmv_log = load_json("cmv_log.json")
    if "eventos" not in cmv_log:
        cmv_log["eventos"] = {}
    
    cmv_log["eventos"][event_id] = cmv_data
    save_json("cmv_log.json", cmv_log)
    
    # 8. INTEGRAÇÃO FINANCIAL_CORE
    financial_entry = {
        "type": "cost",
        "category": "cmv",
        "event_id": event_id,
        "company": company,
        "amount": round(cmv_total, 2),
        "confidence": round(avg_confidence, 2),
        "timestamp": get_timestamp()
    }
    
    financial = load_json("financial_entries.json")
    if "entries" not in financial:
        financial["entries"] = []
    
    financial["entries"].append(financial_entry)
    save_json("financial_entries.json", financial)
    
    return cmv_data


def detect_inconsistencias() -> List[Dict]:
    """
    9. DETECÇÃO AUTOMÁTICA DE INCONSISTÊNCIAS
    """
    inconsistencias = []
    
    # Carregar todos os dados
    recipes = load_json("recipes.json")
    inventory = load_json("inventory.json")
    execs = load_json("production_execution.json")
    waste = load_json("waste_log.json")
    cmv = load_json("cmv_log.json")
    
    # Check 1: Produção sem estoque
    for ex_id, exc in execs.get("execucoes", {}).items():
        # TODO: implementar check de baixa
        pass
    
    # Check 2: Consumo sem receita
    for event_id, data in waste.get("registros", {}).items():
        consumos = data.get("consumo", [])
        for c in consumos:
            rec_id = c.get("recipe_id")
            if rec_id and rec_id not in recipes.get("receitas", {}):
                inconsistencias.append({
                    "type": "consumo_sem_receita",
                    "severity": "high",
                    "event_id": event_id,
                    "description": f"Consumo associa receita {rec_id} que nao existe"
                })
    
    # Check 3: Evento com receita mas sem CMV
    for event_id in waste.get("registros", {}).keys():
        if event_id not in cmv.get("eventos", {}):
            inconsistencias.append({
                "type": "evento_sem_cmv",
                "severity": "medium",
                "event_id": event_id,
                "description": "Evento tem dados de consumo mas nao tem CMV calculado"
            })
    
    # Check 4: CMV alto vs histórico
    # TODO: implementar comparativo com histórico
    
    # Registrar em errors.json
    for inc in inconsistencias:
        log_error(
            error_type=inc["type"],
            severity=inc["severity"],
            event_id=inc["event_id"],
            description=inc["description"],
            source="detect_inconsistencias"
        )
    
    return inconsistencias


def gerar_output_analitico() -> Dict:
    """
    10. OUTPUT ANALÍTICO
    """
    recipes = load_json("recipes.json")
    cmv = load_json("cmv_log.json")
    waste = load_json("waste_log.json")
    
    # Custo por receita
    custo_por_receita = []
    for rec_id, rec in recipes.get("receitas", {}).items():
        # Calcular custo atualizado
        custo, _, _ = calcular_custo_receita(rec_id, rec)
        custo_por_receita.append({
            "recipe_id": rec_id,
            "name": rec.get("nome", rec.get("name", "")),
            "cost": custo
        })
    
    # Custo por evento
    custo_por_evento = []
    for event_id, data in cmv.get("eventos", {}).items():
        custo_por_evento.append({
            "event_id": event_id,
            "cmv": data.get("cmv_total", 0),
            "confidence": data.get("cost_confidence_score", 0)
        })
    
    # Ranking de desperdício
    desperdicio_por_evento = []
    for event_id, data in waste.get("registros", {}).items():
        desp = data.get("desperdicio", [])
        total = sum(d.get("quantidade", 0) for d in desp)
        desperdicio_por_evento.append({
            "event_id": event_id,
            "total_desperdicio": total
        })
    
    # Ordenar
    custo_por_receita.sort(key=lambda x: x["cost"], reverse=True)
    desperdicio_por_evento.sort(key=lambda x: x["total_desperdicio"], reverse=True)
    
    analytics = {
        "generated_at": get_timestamp(),
        "recipes": {
            "mais_caras": custo_por_receita[:5]
        },
        "events": {
            "cmv_totals": custo_por_evento
        },
        "waste": {
            "maior_desperdicio": desperdicio_por_evento[:5]
        }
    }
    
    save_json("analytics.json", analytics)
    return analytics


def calcular_custo_receita(recipe_id: str, receita: Dict) -> Tuple[float, str, float]:
    """Calcula custo de uma receita"""
    total = 0.0
    min_confidence = 1.0
    
    ingredients = receita.get("ingredientes", [])
    rendimento = receita.get("rendimento_porca", 1)
    if rendimento == 0:
        rendimento = 1
    
    for ing in ingredients:
        item_id = ing.get("codigo_inv")
        qtd = ing.get("quantidade_por_porcao", 0)
        
        custo, source, confidence = calculate_weighted_average_cost(item_id)
        if custo:
            total += custo * qtd
            min_confidence = min(min_confidence, confidence)
        else:
            min_confidence = 0.0
    
    custo_porcao = total / rendimento
    return round(custo_porcao, 2), "calculated", min_confidence


def gerar_sugestoes() -> List[Dict]:
    """
    11. APRENDIZADO CONTROLADO
    Sugere sem alterar automaticamente
    """
    sugestoes = []
    
    # Analisar discrepâncias
    execs = load_json("production_execution.json")
    planos = load_json("production_plan.json")
    
    for ex_id, exc in execs.get("execucoes", {}).items():
        event_id = exc.get("evento_id")
        plano = planos.get("eventos", {}).get(event_id, {})
        
        for rec in exc.get("receitas_executadas", []):
            planejado = rec.get("porcoes_planejadas", 0)
            producido = rec.get("porcoes_produzidas", 0)
            
            if planejado > 0:
                diff_pct = abs(producido - planejado) / planejado * 100
                
                if diff_pct > 20:
                    sugestoes.append({
                        "tipo": "ajuste_ficha_tecnica",
                        "event_id": event_id,
                        "recipe_id": rec.get("receita_id"),
                        "situacao": f"{diff_pct:.1f}% de diferenca na producao",
                        "sugestao": f"Revisar quantidade de ingredientes na ficha tecnica"
                    })
    
    # Salvar
    decisions = load_json("decisions.json")
    if "sugestoes" not in decisions:
        decisions["sugestoes"] = []
    
    decisions["sugestoes"].extend(sugestoes)
    save_json("decisions.json", decisions)
    
    return sugestoes


# ===== FUNÇÃO PRINCIPAL DE VALIDAÇÃO =====

def validate_full_event(event_id: str, event_data: Dict, company: str) -> Dict:
    """
    VALIDAÇÃO COMPLETA - Executa todas as validações para um evento
    """
    result = {
        "event_id": event_id,
        "validation_status": "ok",
        "errors": [],
        "warnings": [],
        "cmv_calculated": None
    }
    
    # 1. Validar estrutura do registro
    validated_record = validate_event_record(event_id, event_data, company)
    
    # 2. Validar receitas do cardápio
    recipes = load_json("recipes.json")
    cardapio = event_data.get("cardapio", {})
    for categoria, itens in cardapio.items():
        for item in itens:
            rec_id = item.get("receita_id")
            rec = recipes.get("receitas", {}).get(rec_id, {})
            if rec:
                valid, errors = validate_recipe_structure(rec_id, rec)
                if errors:
                    result["warnings"].extend(errors)
                if not valid:
                    result["errors"].append(f"Receita {rec_id} estrutura invalida")
    
    # 3. Calcular CMV se tiver produção
    execs = load_json("production_execution.json")
    has_production = any(
        e.get("evento_id") == event_id 
        for e in execs.get("execucoes", {}).values()
    )
    
    if has_production:
        cmv = calcular_cmv_evento_v2(event_id, company)
        result["cmv_calculated"] = cmv
        
        if cmv.get("cost_confidence_score", 0) < 0.5:
            log_error(
                error_type="low_cmv_confidence",
                severity="medium",
                event_id=event_id,
                description=f"CMV com confianca baixa: {cmv.get('cost_confidence_score')}",
                source="validate_full_event"
            )
    
    # 4. Detectar inconsistências
    inconsistencias = detect_inconsistencias()
    result["inconsistencias_encontradas"] = len( inconsistencias)
    
    # Status final
    if result["errors"]:
        result["validation_status"] = "failed"
    elif result["warnings"]:
        result["validation_status"] = "warning"
    
    return result


if __name__ == "__main__":
    print("🎛️ Kitchen Intelligence Engine v2 - Control Layer")
    print("="*60)
    print("\nTestando validações...")
    
    # Executar detecção de inconsistências
    print("\n🔍 Detectando inconsistências...")
    incs = detect_inconsistencias()
    print(f"   {len(incs)} inconsistências encontradas")
    
    # Gerar analytics
    print("\n📊 Gerando análise...")
    analytics = gerar_output_analitico()
    print(f"   Analytics gerado: {len(analytics['recipes']['mais_caras'])} receitas")
    
    print("\n✅ Control Layer pronto!")
