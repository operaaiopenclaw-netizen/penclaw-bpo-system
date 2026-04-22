#!/usr/bin/env python3
"""
INVENTORY MANAGER
Manages stock entries, movements, and balance calculation.

All data lives in kitchen_data/ and is linked to catalog_products.json.

Usage (CLI):
  python3 inventory_manager.py purchase CAR-001 50 85.00 --supplier SUP-001 --nfe NF-001
  python3 inventory_manager.py balance
  python3 inventory_manager.py balance CAR-001
  python3 inventory_manager.py movements CAR-001
  python3 inventory_manager.py loss CAR-001 2.5 --reason quebra
  python3 inventory_manager.py adjust CAR-001 3.0 --reason contagem_fisica
  python3 inventory_manager.py recalculate

Programmatic import:
  from inventory_manager import record_purchase, record_consumption, get_balance
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "kitchen_data"
CATALOG_FILE = BASE_DIR / "catalog_products.json"
ENTRIES_FILE = DATA_DIR / "inventory_entries.json"
MOVEMENTS_FILE = DATA_DIR / "inventory_movements.json"
BALANCE_FILE = DATA_DIR / "inventory_balance.json"


# ── helpers ──────────────────────────────────────────────────────────────────

def _load(path: Path) -> Dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(path: Path, data: Dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_catalog() -> Dict[str, Dict]:
    data = _load(CATALOG_FILE)
    return {p["id"]: p for p in data.get("products", [])}


def _next_id(prefix: str, existing: List[str]) -> str:
    """Generate next sequential ID: MOV-001 → MOV-002 etc."""
    nums = []
    for e in existing:
        parts = e.split("-")
        if len(parts) >= 2 and parts[0] == prefix.split("-")[0]:
            try:
                nums.append(int(parts[-1]))
            except ValueError:
                pass
    nxt = max(nums, default=0) + 1
    return f"{prefix}{nxt:03d}"


def _load_movements() -> List[Dict]:
    data = _load(MOVEMENTS_FILE)
    return data.get("movements", [])


def _save_movements(movements: List[Dict]):
    data = _load(MOVEMENTS_FILE)
    if "_meta" not in data:
        data["_meta"] = {"version": "1.0", "description": "Registro de movimentos de estoque"}
    data["movements"] = movements
    _save(MOVEMENTS_FILE, data)


# ── core: balance ─────────────────────────────────────────────────────────────

def recalculate_balance() -> Dict[str, Dict]:
    """
    Rebuilds inventory_balance.json from all movements.

    Rule:
      entrada  → +qty
      retorno  → +qty   (goods returned to stock after event)
      ajuste   → +qty   (can be negative if qty stored as negative)
      saida    → qty as stored (should be negative already)
      perda    → qty as stored (should be negative already)
    """
    catalog = _load_catalog()
    movements = _load_movements()

    balances: Dict[str, Dict] = {}

    for m in movements:
        pid = m.get("product_id")
        if not pid:
            continue

        qty = float(m.get("quantity", 0))
        unit_cost = float(m.get("unit_cost", 0))

        if pid not in balances:
            product = catalog.get(pid, {})
            balances[pid] = {
                "product_id": pid,
                "product_name": product.get("name", m.get("product_name", pid)),
                "category": product.get("category", ""),
                "unit": product.get("unit", m.get("unit", "")),
                "balance_qty": 0.0,
                "total_purchased": 0.0,
                "total_consumed": 0.0,
                "last_unit_cost": 0.0,
                "movements_count": 0,
            }

        b = balances[pid]
        b["balance_qty"] = round(b["balance_qty"] + qty, 4)
        b["movements_count"] += 1

        if m.get("type") == "entrada":
            b["total_purchased"] = round(b["total_purchased"] + qty, 4)
            b["last_unit_cost"] = unit_cost
        elif m.get("type") in ("saida", "perda"):
            b["total_consumed"] = round(b["total_consumed"] + abs(qty), 4)

    # Compute stock value
    for b in balances.values():
        b["stock_value"] = round(max(b["balance_qty"], 0) * b["last_unit_cost"], 2)
        b["calculated_at"] = datetime.now().isoformat()

    output = {
        "_meta": {
            "version": "1.0",
            "calculated_at": datetime.now().isoformat(),
            "total_products": len(balances),
            "total_stock_value": round(sum(b["stock_value"] for b in balances.values()), 2),
        },
        "balances": balances,
    }

    _save(BALANCE_FILE, output)
    return balances


def get_balance(product_id: Optional[str] = None) -> Dict:
    """Returns current balance. Recalculates from movements first."""
    balances = recalculate_balance()
    if product_id:
        return balances.get(product_id, {})
    return balances


# ── core: write operations ────────────────────────────────────────────────────

def record_purchase(
    product_id: str,
    quantity: float,
    unit_cost: float,
    supplier_id: str = "",
    nfe: str = "",
    date: str = None,
    notes: str = "",
) -> Dict:
    """
    Records a stock entry (purchase).
    Adds to inventory_entries.json and inventory_movements.json.
    Returns the created movement.
    """
    catalog = _load_catalog()
    product = catalog.get(product_id)
    if not product:
        raise ValueError(f"Product '{product_id}' not found in catalog")

    today = date or datetime.now().strftime("%Y-%m-%d")

    # ── entry record ──
    entries_data = _load(ENTRIES_FILE)
    entries = entries_data.get("entries", [])
    entry_ids = [e["entry_id"] for e in entries]
    short_date = today.replace("-", "")
    seq = len([e for e in entry_ids if e.startswith(f"PUR-{short_date}")]) + 1
    entry_id = f"PUR-{short_date}-{seq:03d}"

    entry = {
        "entry_id": entry_id,
        "date": today,
        "supplier_id": supplier_id,
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": quantity,
        "unit": product["unit"],
        "unit_cost": unit_cost,
        "total_cost": round(quantity * unit_cost, 2),
        "nfe": nfe,
        "status": "received",
        "notes": notes,
        "recorded_at": datetime.now().isoformat(),
    }
    entries.append(entry)
    entries_data["entries"] = entries
    _save(ENTRIES_FILE, entries_data)

    # ── movement record ──
    movements = _load_movements()
    mov_id = _next_id("MOV-", [m["movement_id"] for m in movements])
    movement = {
        "movement_id": mov_id,
        "date": today,
        "type": "entrada",
        "source": "compra",
        "event_id": None,
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": quantity,
        "unit": product["unit"],
        "unit_cost": unit_cost,
        "reference": entry_id,
        "responsible": "Almoxarife",
        "notes": nfe,
    }
    movements.append(movement)
    _save_movements(movements)

    recalculate_balance()
    print(f"[OK] Entrada: {quantity} {product['unit']} de {product['name']} @ R$ {unit_cost:.2f} = R$ {quantity*unit_cost:.2f}")
    return movement


def record_consumption(
    event_id: str,
    product_id: str,
    qty_used: float,
    qty_returned: float = 0.0,
    unit_cost: Optional[float] = None,
    date: str = None,
    responsible: str = "",
) -> Dict:
    """
    Records event consumption as two movements: saida + optional retorno.
    Returns net consumption movement.
    """
    catalog = _load_catalog()
    product = catalog.get(product_id)
    if not product:
        raise ValueError(f"Product '{product_id}' not found in catalog")

    if unit_cost is None:
        unit_cost = product["unit_cost"]

    today = date or datetime.now().strftime("%Y-%m-%d")
    movements = _load_movements()
    existing_ids = [m["movement_id"] for m in movements]

    # saida movement
    mov_id = _next_id("MOV-", existing_ids)
    saida = {
        "movement_id": mov_id,
        "date": today,
        "type": "saida",
        "source": "consumo_evento",
        "event_id": event_id,
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": -abs(qty_used),
        "unit": product["unit"],
        "unit_cost": unit_cost,
        "reference": event_id,
        "responsible": responsible or "Evento",
        "notes": f"Consumo evento {event_id}",
    }
    movements.append(saida)
    existing_ids.append(mov_id)

    # retorno movement (if any)
    if qty_returned > 0:
        ret_id = _next_id("MOV-", existing_ids)
        retorno = {
            "movement_id": ret_id,
            "date": today,
            "type": "retorno",
            "source": "sobra_evento",
            "event_id": event_id,
            "product_id": product_id,
            "product_name": product["name"],
            "quantity": abs(qty_returned),
            "unit": product["unit"],
            "unit_cost": unit_cost,
            "reference": event_id,
            "responsible": responsible or "Evento",
            "notes": f"Retorno sobra {event_id}",
        }
        movements.append(retorno)

    _save_movements(movements)
    recalculate_balance()

    net = qty_used - qty_returned
    print(f"[OK] Consumo {event_id}: {product['name']} {net} {product['unit']} (usado {qty_used} - retorno {qty_returned})")
    return saida


def record_loss(
    product_id: str,
    quantity: float,
    reason: str = "",
    date: str = None,
) -> Dict:
    """Records a stock loss (breakage, spoilage, etc.)."""
    catalog = _load_catalog()
    product = catalog.get(product_id)
    if not product:
        raise ValueError(f"Product '{product_id}' not found in catalog")

    today = date or datetime.now().strftime("%Y-%m-%d")
    movements = _load_movements()
    mov_id = _next_id("MOV-", [m["movement_id"] for m in movements])

    loss = {
        "movement_id": mov_id,
        "date": today,
        "type": "perda",
        "source": reason or "sem_motivo",
        "event_id": None,
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": -abs(quantity),
        "unit": product["unit"],
        "unit_cost": product["unit_cost"],
        "reference": None,
        "responsible": "Almoxarife",
        "notes": reason,
    }
    movements.append(loss)
    _save_movements(movements)
    recalculate_balance()

    print(f"[OK] Perda registrada: {quantity} {product['unit']} de {product['name']} — {reason}")
    return loss


def record_adjustment(
    product_id: str,
    quantity: float,   # positive = found more; negative = found less
    reason: str = "contagem_fisica",
    date: str = None,
) -> Dict:
    """Records a stock adjustment after physical count."""
    catalog = _load_catalog()
    product = catalog.get(product_id)
    if not product:
        raise ValueError(f"Product '{product_id}' not found in catalog")

    today = date or datetime.now().strftime("%Y-%m-%d")
    movements = _load_movements()
    mov_id = _next_id("MOV-", [m["movement_id"] for m in movements])

    adj = {
        "movement_id": mov_id,
        "date": today,
        "type": "ajuste",
        "source": reason,
        "event_id": None,
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": quantity,
        "unit": product["unit"],
        "unit_cost": product["unit_cost"],
        "reference": None,
        "responsible": "Controle Estoque",
        "notes": reason,
    }
    movements.append(adj)
    _save_movements(movements)
    recalculate_balance()

    sign = "+" if quantity >= 0 else ""
    print(f"[OK] Ajuste: {sign}{quantity} {product['unit']} de {product['name']} — {reason}")
    return adj


# ── display ───────────────────────────────────────────────────────────────────

def show_balance(product_id: Optional[str] = None):
    """Prints current stock balance."""
    balances = recalculate_balance()

    if product_id:
        b = balances.get(product_id)
        if not b:
            print(f"[WARN] {product_id} não encontrado no estoque")
            return
        items = [b]
    else:
        items = sorted(balances.values(), key=lambda x: x["category"])

    print("\n" + "=" * 70)
    print("BALANÇO DE ESTOQUE")
    print("=" * 70)
    print(f"{'PRODUTO':<30} {'QTD':>8} {'UNIT':<6} {'VLR ESTOQUE':>12}")
    print("-" * 70)

    for b in items:
        qty = b["balance_qty"]
        flag = " ⚠️" if qty <= 0 else ""
        print(
            f"{b['product_name'][:30]:<30} "
            f"{qty:>8.2f} "
            f"{b['unit']:<6} "
            f"R$ {b['stock_value']:>9,.2f}"
            f"{flag}"
        )

    if not product_id:
        meta = _load(BALANCE_FILE).get("_meta", {})
        total = meta.get("total_stock_value", 0)
        print("-" * 70)
        print(f"{'TOTAL':>46} R$ {total:>9,.2f}")
    print("=" * 70)


def show_movements(product_id: str):
    """Prints all movements for a product."""
    movements = [m for m in _load_movements() if m.get("product_id") == product_id]
    if not movements:
        print(f"Nenhum movimento para {product_id}")
        return

    print(f"\nMovimentos — {product_id}")
    print("-" * 70)
    for m in movements:
        sign = "+" if m["quantity"] >= 0 else ""
        print(
            f"  {m['date']}  {m['movement_id']:10s}  "
            f"{m['type']:8s}  {sign}{m['quantity']:>8.2f} {m['unit']}  "
            f"{m.get('event_id') or m.get('source','')}"
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "purchase":
        if len(args) < 4:
            print("Usage: purchase <product_id> <qty> <unit_cost> [--supplier SUP] [--nfe NFE]")
            return
        product_id = args[1]
        qty = float(args[2])
        cost = float(args[3])
        supplier = ""
        nfe = ""
        for i, a in enumerate(args):
            if a == "--supplier" and i + 1 < len(args):
                supplier = args[i + 1]
            if a == "--nfe" and i + 1 < len(args):
                nfe = args[i + 1]
        record_purchase(product_id, qty, cost, supplier_id=supplier, nfe=nfe)

    elif cmd == "balance":
        pid = args[1] if len(args) > 1 else None
        show_balance(pid)

    elif cmd == "movements":
        if len(args) < 2:
            print("Usage: movements <product_id>")
            return
        show_movements(args[1])

    elif cmd == "loss":
        if len(args) < 3:
            print("Usage: loss <product_id> <qty> [--reason texto]")
            return
        reason = ""
        for i, a in enumerate(args):
            if a == "--reason" and i + 1 < len(args):
                reason = args[i + 1]
        record_loss(args[1], float(args[2]), reason=reason)

    elif cmd == "adjust":
        if len(args) < 3:
            print("Usage: adjust <product_id> <qty> [--reason texto]")
            return
        reason = "contagem_fisica"
        for i, a in enumerate(args):
            if a == "--reason" and i + 1 < len(args):
                reason = args[i + 1]
        record_adjustment(args[1], float(args[2]), reason=reason)

    elif cmd == "recalculate":
        balances = recalculate_balance()
        print(f"[OK] Balanço recalculado — {len(balances)} produtos")
        show_balance()

    else:
        print(f"Comando desconhecido: {cmd}")
        print("Comandos: purchase | balance | movements | loss | adjust | recalculate")


if __name__ == "__main__":
    _cli()
