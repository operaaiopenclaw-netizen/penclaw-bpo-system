#!/usr/bin/env python3
"""
KITCHEN CONTROL ENGINE
Calculates real CMV per event using the product catalog.

Pipeline:
  events_consolidated.csv + catalog_products.json
    → estimate pax per event
    → apply menu template per event type
    → calculate ingredient cost from catalog prices
    → write cmv_log.json  (consumed by dre_engine.py)
    → write production_execution.json  (consumed by financial_truth_audit.py)
"""

import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

BASE_DIR = Path(__file__).parent
CATALOG_FILE = BASE_DIR / "catalog_products.json"
DATA_DIR = BASE_DIR / "kitchen_data"
CMV_LOG_FILE = DATA_DIR / "cmv_log.json"
PRODUCTION_FILE = DATA_DIR / "production_execution.json"


# ---------------------------------------------------------------------------
# Menu templates — realistic churrasco/coquetel catering style
# Each item: (product_id, qty_per_pax)   → multiplied by total pax
# Staff entries are in hours-per-pax based on typical ratios
#
# Event-fixed items are in a separate list: (product_id, qty_total)
# ---------------------------------------------------------------------------
MENU_TEMPLATES: Dict[str, Dict] = {
    "casamento": {
        "avg_ticket": 185.0,
        "items_per_pax": [
            # Proteínas (kg per pax — will apply yield correction)
            ("CAR-001", 0.200),   # 200 g carne bovina
            ("FRG-001", 0.120),   # 120 g frango
            ("QUE-001", 1.0),     # 1 espeto queijo coalho   (un)
            # Acompanhamentos
            ("SAL-001", 3.0),     # 3 salgados               (un)
            ("PAO-001", 2.0),     # 2 pães de alho           (un)
            ("VEG-002", 1.0),     # 1 bruschetta veggie      (un)
            ("FRU-001", 0.060),   # 60 g mix de frutas       (kg)
            # Bebidas
            ("CER-001", 0.350),   # 350 ml cerveja           (lit)
            ("REF-001", 0.200),   # 200 ml refrigerante      (lit)
            ("AGU-001", 0.250),   # 250 ml água              (lit)
            ("ESP-001", 0.100),   # 100 ml espumante         (lit)
            ("GEL-001", 0.400),   # 400 g gelo               (kg)
            # Materiais descartáveis
            ("DIS-001", 3.0),     # 3 copos                  (un)
            ("DIS-002", 1.0),     # 1 prato                  (un)
            ("DIS-003", 1.0),     # 1 talher                 (un)
            # Staff: hours-per-pax (1 garçom/20pax×4h → 0.200h/pax)
            ("GAR-001", 0.200),   # garçom   35 R$/h
            ("BAR-001", 0.133),   # bartender 45 R$/h
            ("COP-001", 0.160),   # copeiro   30 R$/h
            ("CRD-001", 0.060),   # coordenador 80 R$/h
        ],
        "items_per_event": [
            ("EQU-001", 1.0),     # aluguel equipamentos R$2000
            ("LOG-001", 50.0),    # 50 km logística
        ],
    },

    "corporativo": {
        "avg_ticket": 100.0,
        "items_per_pax": [
            ("FRG-001", 0.150),
            ("LAZ-001", 0.120),   # lasanha bolonhesa  (kg)
            ("SAL-001", 2.0),
            ("VEG-002", 1.0),
            ("PAO-001", 1.0),
            ("CER-001", 0.200),
            ("REF-001", 0.250),
            ("AGU-001", 0.350),
            ("COF-001", 0.030),   # ~30 ml café
            ("GEL-001", 0.250),
            ("DIS-001", 2.0),
            ("DIS-002", 1.0),
            ("DIS-003", 1.0),
            ("GAR-001", 0.160),
            ("COP-001", 0.120),
            ("CRD-001", 0.050),
        ],
        "items_per_event": [
            ("EQU-001", 1.0),
            ("LOG-001", 30.0),
        ],
    },

    "aniversario": {
        "avg_ticket": 150.0,   # typical R$130-180/pax for birthday party
        "items_per_pax": [
            ("LEG-001", 0.180),   # linguiça toscana  (kg)
            ("FRG-001", 0.130),
            ("QUE-001", 1.0),
            ("SAL-001", 4.0),
            ("VEG-003", 2.0),     # empadinha palmito (un)
            ("PAO-001", 1.0),
            ("FRU-001", 0.050),
            ("CER-001", 0.350),
            ("REF-001", 0.200),
            ("AGU-001", 0.300),
            ("DRK-001", 0.5),     # 0.5 drinks caipirinha (un)
            ("GEL-001", 0.400),
            ("DIS-001", 3.0),
            ("DIS-002", 1.0),
            ("DIS-003", 1.0),
            ("GAR-001", 0.180),
            ("BAR-001", 0.100),
            ("COP-001", 0.150),
            ("CRD-001", 0.050),
        ],
        "items_per_event": [
            ("EQU-001", 0.6),    # partial equipment set (R$1200 vs R$2000 full)
            ("LOG-001", 30.0),
        ],
    },

    "festa": {
        "avg_ticket": 120.0,   # typical R$100-140/pax for a festa
        "items_per_pax": [
            ("LEG-001", 0.200),
            ("FRG-001", 0.150),
            ("SAL-001", 4.0),
            ("VEG-003", 1.0),
            ("PAO-001", 1.0),
            ("CER-001", 0.400),
            ("REF-001", 0.200),
            ("AGU-001", 0.300),
            ("GEL-001", 0.450),
            ("DIS-001", 3.0),
            ("DIS-002", 1.0),
            ("DIS-003", 1.0),
            ("GAR-001", 0.180),
            ("BAR-001", 0.100),
            ("COP-001", 0.130),
            ("CRD-001", 0.050),
        ],
        "items_per_event": [
            ("EQU-001", 0.4),    # minimal setup (R$800)
            ("LOG-001", 25.0),
        ],
    },

    "coquetel": {
        "avg_ticket": 90.0,
        "items_per_pax": [
            ("VEG-003", 3.0),
            ("SAL-001", 4.0),
            ("PAO-002", 2.0),     # mini sanduíches     (un)
            ("VEG-002", 2.0),
            ("FRU-001", 0.040),
            ("CER-001", 0.300),
            ("REF-001", 0.200),
            ("AGU-001", 0.200),
            ("DRK-001", 1.0),
            ("GEL-001", 0.300),
            ("DIS-001", 3.0),
            ("DIS-002", 1.0),
            ("DIS-003", 1.0),
            ("GAR-001", 0.150),
            ("BAR-001", 0.120),
            ("COP-001", 0.100),
            ("CRD-001", 0.040),
        ],
        "items_per_event": [
            ("EQU-001", 1.0),
            ("LOG-001", 30.0),
        ],
    },

    "coffee": {
        "avg_ticket": 60.0,
        "items_per_pax": [
            ("SAL-001", 3.0),
            ("VEG-003", 2.0),
            ("PAO-002", 1.0),
            ("FRU-001", 0.030),
            ("COF-001", 0.060),
            ("REF-001", 0.200),
            ("AGU-001", 0.150),
            ("DIS-001", 2.0),
            ("DIS-002", 1.0),
            ("COP-001", 0.100),
            ("CRD-001", 0.030),
        ],
        "items_per_event": [
            ("EQU-001", 1.0),
            ("LOG-001", 20.0),
        ],
    },
}

# Fallback template for unrecognised event types
MENU_TEMPLATES["default"] = MENU_TEMPLATES["festa"]


def load_catalog() -> Dict[str, Dict]:
    """Returns {product_id: product_dict} from catalog_products.json."""
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {p["id"]: p for p in data["products"]}


def load_events() -> List[Dict]:
    """Loads events_consolidated.csv as list of dicts."""
    events_file = DATA_DIR / "events_consolidated.csv"
    if not events_file.exists():
        print(f"[ERROR] {events_file} not found")
        return []
    with open(events_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def estimate_pax(revenue: float, event_type: str) -> int:
    """Estimates number of guests from revenue and event type."""
    template_key = _resolve_template_key(event_type)
    avg_ticket = MENU_TEMPLATES[template_key]["avg_ticket"]
    pax = max(1, round(revenue / avg_ticket))
    return pax


def _resolve_template_key(event_type: str) -> str:
    """Maps raw event_type string to a template key."""
    mapping = {
        "casamento": "casamento",
        "wedding": "casamento",
        "corporativo": "corporativo",
        "corporate": "corporativo",
        "aniversario": "aniversario",
        "aniversário": "aniversario",
        "birthday": "aniversario",
        "festa": "festa",
        "party": "festa",
        "coquetel": "coquetel",
        "cocktail": "coquetel",
        "coffee": "coffee",
        "coffee break": "coffee",
    }
    key = event_type.lower().strip()
    return mapping.get(key, "default")


def effective_unit_cost(product: Dict) -> float:
    """
    Returns cost per usable unit.

    For food items sold by kg with yield < 1 (waste factor), the purchase cost
    must be grossed up: you need to buy more than you serve.
    Example: CAR-001 yield=0.85 → buy 1 kg to get 0.85 kg usable.
    cost_per_usable_kg = unit_cost / yield_per_unit

    For items where yield > 1 (e.g. coffee: 1 lit → 20 cups), the yield is
    a conversion factor and the unit cost is already the base-unit price.
    We leave those alone.
    """
    unit = product.get("unit", "")
    yield_v = product.get("yield_per_unit", 1.0)

    # Apply waste correction only for kg-unit food/beverage items with yield < 1
    if unit == "kg" and 0 < yield_v < 1.0:
        return product["unit_cost"] / yield_v

    return product["unit_cost"]


def calculate_event_cmv(
    event_id: str,
    event_type: str,
    revenue: float,
    catalog: Dict[str, Dict],
) -> Tuple[float, float, List[Dict]]:
    """
    Calculates CMV for a single event.

    Returns:
        (cmv_total, confidence_score, breakdown_list)
    """
    template_key = _resolve_template_key(event_type)
    template = MENU_TEMPLATES[template_key]

    pax = estimate_pax(revenue, event_type)
    breakdown = []
    cmv_total = 0.0
    missing_products = []

    # Per-pax items
    for product_id, qty_per_pax in template["items_per_pax"]:
        product = catalog.get(product_id)
        if not product:
            missing_products.append(product_id)
            continue

        total_qty = qty_per_pax * pax
        cost = total_qty * effective_unit_cost(product)
        cmv_total += cost

        breakdown.append({
            "product_id": product_id,
            "name": product["name"],
            "category": product["category"],
            "qty_per_pax": qty_per_pax,
            "total_qty": round(total_qty, 3),
            "unit": product["unit"],
            "unit_cost": product["unit_cost"],
            "line_cost": round(cost, 2),
        })

    # Fixed-per-event items
    for product_id, qty_total in template["items_per_event"]:
        product = catalog.get(product_id)
        if not product:
            missing_products.append(product_id)
            continue

        cost = qty_total * product["unit_cost"]
        cmv_total += cost

        breakdown.append({
            "product_id": product_id,
            "name": product["name"],
            "category": product["category"],
            "qty_per_pax": None,
            "total_qty": qty_total,
            "unit": product["unit"],
            "unit_cost": product["unit_cost"],
            "line_cost": round(cost, 2),
            "per_event": True,
        })

    if missing_products:
        print(f"  [WARN] {event_id}: products not in catalog: {missing_products}")

    # Confidence: lower if many products are missing
    total_items = len(template["items_per_pax"]) + len(template["items_per_event"])
    found_items = total_items - len(missing_products)
    confidence = round(found_items / total_items, 2) if total_items else 0.0

    return round(cmv_total, 2), confidence, breakdown, pax




def build_production_execution(
    events: List[Dict],
    cmv_log: Dict,
) -> Dict:
    """
    Builds a minimal production_execution.json so financial_truth_audit.py
    can load produção and venda data.

    We approximate: porcoes_produzidas ≈ pax, porcoes_servidas ≈ pax × 0.93 (7% sobra).
    """
    execucoes = {}
    waste_factor = 0.07

    for event in events:
        event_id = event.get("event_id")
        event_data = cmv_log["eventos"].get(event_id)
        if not event_data:
            continue

        pax = event_data["estimated_pax"]
        event_type = event.get("event_type", "")

        exec_id = f"EXEC-{event_id}"
        porcoes_produzidas = pax
        porcoes_servidas = math.floor(pax * (1 - waste_factor))

        execucoes[exec_id] = {
            "evento_id": event_id,
            "nome_evento": f"{event_type.capitalize()} {event_id}",
            "data_execucao": event.get("date_event", ""),
            "receitas_executadas": [
                {
                    "receita_id": "MENU-GERAL",
                    "nome": f"Menu {event_type}",
                    "porcoes_produzidas": porcoes_produzidas,
                    "porcoes_servidas": porcoes_servidas,
                    "porcoes_restantes": porcoes_produzidas - porcoes_servidas,
                    "custo_real": event_data["cmv_total"],
                    "status": "concluido",
                }
            ],
            "totais": {
                "custo_total_real": event_data["cmv_total"],
                "custo_por_pessoa_real": round(
                    event_data["cmv_total"] / pax, 2
                ) if pax else 0,
            },
            "timestamp_registro": datetime.now().isoformat(),
        }

    return {
        "_meta": {
            "version": "1.0",
            "generated_by": "kitchen_control.py",
            "generated_at": datetime.now().isoformat(),
        },
        "execucoes": execucoes,
        "metricas_acumuladas": {},
    }


CONSUMPTION_FILE = DATA_DIR / "event_consumption_real.json"


# ── real-data path ─────────────────────────────────────────────────────────

def load_real_consumption() -> Dict[str, Dict]:
    """Loads completed event checklists from event_consumption_real.json."""
    if not CONSUMPTION_FILE.exists():
        return {}
    with open(CONSUMPTION_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("events", {})


def calculate_event_cmv_real(
    event_id: str,
    real_events: Dict[str, Dict],
    catalog: Dict[str, Dict],
) -> Tuple[float, float, List[Dict], int]:
    """
    Calculates CMV from real consumption records (event_consumption_real.json).
    Only usable when event status == 'completed'.

    Returns: (cmv_total, confidence, breakdown, pax_actual)
    """
    event_data = real_events.get(event_id, {})
    items = event_data.get("consumption", [])

    if not items:
        return 0.0, 0.0, [], 0

    breakdown = []
    cmv_total = 0.0

    for item in items:
        pid = item["product_id"]
        product = catalog.get(pid)
        if not product:
            continue

        net_qty = float(item.get("net_consumption", item["qty_used"]))
        cost = net_qty * product["unit_cost"]
        cmv_total += cost

        breakdown.append({
            "product_id": pid,
            "name": product["name"],
            "category": product["category"],
            "total_qty": net_qty,
            "unit": product["unit"],
            "unit_cost": product["unit_cost"],
            "line_cost": round(cost, 2),
            "source": "real",
        })

    pax = int(event_data.get("pax_actual") or event_data.get("pax_estimated") or 0)
    return round(cmv_total, 2), 0.95, breakdown, pax


def calculate_event_cmv_hybrid(
    event_id: str,
    event_type: str,
    revenue: float,
    catalog: Dict[str, Dict],
    real_events: Dict[str, Dict],
) -> Tuple[float, float, List[Dict], int]:
    """
    AUTO mode: real data for tracked products, estimated for everything else.

    For each product in the menu template:
      - If product has a real consumption entry → use real qty × catalog price
      - Else → use estimated qty (pax × template qty) × catalog price
    Products in the real checklist that are NOT in the template are also included.

    Returns: (cmv_total, confidence, breakdown, pax)
    """
    template_key = _resolve_template_key(event_type)
    template = MENU_TEMPLATES[template_key]
    pax_estimated = estimate_pax(revenue, event_type)

    real_event = real_events.get(event_id, {})
    is_complete = real_event.get("status") == "completed"
    pax_actual = real_event.get("pax_actual") or pax_estimated

    # Index real consumption by product_id
    real_by_product: Dict[str, Dict] = {}
    if is_complete:
        for item in real_event.get("consumption", []):
            real_by_product[item["product_id"]] = item

    breakdown = []
    cmv_total = 0.0
    template_ids: List[str] = []

    # --- template items ---
    all_template_items = [
        (pid, qty, False) for pid, qty in template["items_per_pax"]
    ] + [
        (pid, qty, True) for pid, qty in template["items_per_event"]
    ]

    for product_id, qty_template, is_fixed in all_template_items:
        template_ids.append(product_id)
        product = catalog.get(product_id)
        if not product:
            continue

        if product_id in real_by_product:
            # Use real data
            net_qty = float(real_by_product[product_id].get("net_consumption", 0))
            cost = net_qty * product["unit_cost"]
            source = "real"
        else:
            # Use estimate
            if is_fixed:
                total_qty = qty_template
            else:
                total_qty = qty_template * pax_estimated
            cost = total_qty * effective_unit_cost(product)
            net_qty = total_qty
            source = "estimated"

        cmv_total += cost
        breakdown.append({
            "product_id": product_id,
            "name": product["name"],
            "category": product["category"],
            "total_qty": round(net_qty, 3),
            "unit": product["unit"],
            "unit_cost": product["unit_cost"],
            "line_cost": round(cost, 2),
            "source": source,
        })

    # --- real items NOT in template ---
    for pid, item in real_by_product.items():
        if pid in template_ids:
            continue
        product = catalog.get(pid)
        if not product:
            continue
        net_qty = float(item.get("net_consumption", 0))
        cost = net_qty * product["unit_cost"]
        cmv_total += cost
        breakdown.append({
            "product_id": pid,
            "name": product["name"],
            "category": product["category"],
            "total_qty": net_qty,
            "unit": product["unit"],
            "unit_cost": product["unit_cost"],
            "line_cost": round(cost, 2),
            "source": "real_extra",
        })

    # Confidence: fraction of template items covered by real data
    real_count = sum(1 for b in breakdown if b["source"] == "real")
    confidence = round(real_count / len(breakdown), 2) if breakdown else 0.0

    return round(cmv_total, 2), confidence, breakdown, int(pax_actual)


# ── updated build_cmv_log with mode support ────────────────────────────────

def build_cmv_log(
    events: List[Dict],
    catalog: Dict[str, Dict],
    mode: str = "auto",
) -> Dict:
    """
    Builds the full cmv_log.json.

    mode:
      'estimated' — always use menu template estimates (original behaviour)
      'real'      — only use events with completed real checklists; skip others
      'auto'      — use real where available, estimated for the rest (default)
    """
    real_events = load_real_consumption() if mode != "estimated" else {}

    result = {
        "_meta": {
            "version": "2.0",
            "generated_by": "kitchen_control.py",
            "generated_at": datetime.now().isoformat(),
            "mode": mode,
            "description": "CMV por evento — modo: " + mode,
        },
        "eventos": {},
    }

    for event in events:
        event_id = event.get("event_id")
        event_type = event.get("event_type", "default")
        company = event.get("company", "")

        revenue_raw = event.get("revenue_total", "0")
        try:
            revenue = float(revenue_raw) if revenue_raw else 0.0
        except ValueError:
            print(f"  [ERROR] {event_id}: invalid revenue '{revenue_raw}' — skipping")
            continue

        if revenue <= 0:
            print(f"  [WARN] {event_id}: zero revenue — skipping")
            continue

        real_data = real_events.get(event_id, {})
        has_real = real_data.get("status") == "completed"

        if mode == "real" and not has_real:
            print(f"  SKIP   {event_id:10s} | no completed checklist (--mode real)")
            continue

        if mode == "estimated" or not has_real:
            cmv_total, confidence, breakdown, pax = calculate_event_cmv(
                event_id, event_type, revenue, catalog
            )
            data_source = "estimated"
        elif mode == "real":
            cmv_total, confidence, breakdown, pax = calculate_event_cmv_real(
                event_id, real_events, catalog
            )
            data_source = "real"
        else:  # auto
            cmv_total, confidence, breakdown, pax = calculate_event_cmv_hybrid(
                event_id, event_type, revenue, catalog, real_events
            )
            real_count = sum(1 for b in breakdown if b.get("source") == "real")
            data_source = f"hybrid ({real_count}/{len(breakdown)} real)"

        cmv_pct = round((cmv_total / revenue) * 100, 1) if revenue > 0 else None

        result["eventos"][event_id] = {
            "event_id": event_id,
            "company": company,
            "event_type": event_type,
            "revenue": revenue,
            "estimated_pax": pax,
            "cmv_total": cmv_total,
            "cmv_pct_revenue": cmv_pct,
            "cost_confidence_score": confidence,
            "data_source": data_source,
            "breakdown": breakdown,
            "calculated_at": datetime.now().isoformat(),
        }

        src_tag = f"[{data_source}]" if data_source != "estimated" else ""
        print(
            f"  {event_id:10s} | {event_type:12s} | {pax:4d} pax "
            f"| CMV R$ {cmv_total:>10,.2f} ({cmv_pct:.1f}%) {src_tag}"
        )

    return result


# ── unchanged helpers ──────────────────────────────────────────────────────

def save_json(path: Path, data: Dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  -> saved: {path.relative_to(BASE_DIR)}")


def main():
    import sys
    mode = "auto"
    for i, a in enumerate(sys.argv[1:], 1):
        if a == "--mode" and i < len(sys.argv) - 1:
            mode = sys.argv[i + 1]
        elif a.startswith("--mode="):
            mode = a.split("=", 1)[1]

    valid_modes = ("auto", "real", "estimated")
    if mode not in valid_modes:
        print(f"[ERROR] Invalid mode '{mode}'. Choose from: {', '.join(valid_modes)}")
        return

    print("=" * 60)
    print(f"KITCHEN CONTROL ENGINE — mode: {mode}")
    print("=" * 60)

    if not CATALOG_FILE.exists():
        print(f"[FATAL] catalog_products.json not found at {CATALOG_FILE}")
        return
    catalog = load_catalog()
    print(f"\nCatalog loaded: {len(catalog)} products")

    events = load_events()
    if not events:
        print("[FATAL] No events found in events_consolidated.csv")
        return
    print(f"Events loaded: {len(events)} events")

    if mode != "estimated":
        real_events = load_real_consumption()
        completed = sum(1 for v in real_events.values() if v.get("status") == "completed")
        print(f"Real data: {completed} completed event(s) in event_consumption_real.json\n")
    else:
        print()

    print("Calculating CMV per event:")
    print("-" * 60)
    cmv_log = build_cmv_log(events, catalog, mode=mode)

    save_json(CMV_LOG_FILE, cmv_log)

    prod_exec = build_production_execution(events, cmv_log)
    save_json(PRODUCTION_FILE, prod_exec)

    total_revenue = sum(e["revenue"] for e in cmv_log["eventos"].values())
    total_cmv = sum(e["cmv_total"] for e in cmv_log["eventos"].values())
    avg_cmv_pct = (total_cmv / total_revenue * 100) if total_revenue else 0

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Mode             : {mode}")
    print(f"  Events processed : {len(cmv_log['eventos'])}")
    print(f"  Total revenue    : R$ {total_revenue:>12,.2f}")
    print(f"  Total CMV        : R$ {total_cmv:>12,.2f}")
    print(f"  CMV / Revenue    : {avg_cmv_pct:.1f}%")
    print(f"  Gross margin     : {100 - avg_cmv_pct:.1f}%")
    print("\n[OK] kitchen_control done — cmv_log.json ready for dre_engine.py")


if __name__ == "__main__":
    main()
