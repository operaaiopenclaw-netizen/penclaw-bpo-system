#!/usr/bin/env python3
"""
EVENT INPUT
Manages actual consumption checklists per event.
Operators use this to record what was REALLY consumed during each event.

Usage (CLI):
  python3 event_input.py create EVT002
  python3 event_input.py record EVT002 CAR-001 26.0
  python3 event_input.py record EVT002 CER-001 45.0 --returned 1.5
  python3 event_input.py complete EVT002 --pax 140 --notes "Evento ótimo"
  python3 event_input.py status EVT002
  python3 event_input.py list

Once an event is 'completed', kitchen_control.py in auto/real mode will use
the recorded consumption instead of the template estimate.

Programmatic import:
  from event_input import create_checklist, record_item, complete_event
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "kitchen_data"
CATALOG_FILE = BASE_DIR / "catalog_products.json"
CONSUMPTION_FILE = DATA_DIR / "event_consumption_real.json"
EVENTS_CSV = DATA_DIR / "events_consolidated.csv"


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_catalog() -> Dict[str, Dict]:
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {p["id"]: p for p in data.get("products", [])}


def _load_consumption() -> Dict:
    if CONSUMPTION_FILE.exists():
        with open(CONSUMPTION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"_meta": {"version": "1.0"}, "events": {}}


def _save_consumption(data: Dict):
    with open(CONSUMPTION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_events_csv() -> Dict[str, Dict]:
    """Returns dict of event_id → event row from events_consolidated.csv."""
    import csv
    events = {}
    if EVENTS_CSV.exists():
        with open(EVENTS_CSV, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                events[row["event_id"]] = row
    return events


# ── core operations ───────────────────────────────────────────────────────────

def create_checklist(event_id: str) -> Dict:
    """
    Creates a blank checklist for the event.
    Pre-populates with the event metadata from events_consolidated.csv.
    """
    data = _load_consumption()
    events_csv = _load_events_csv()

    if event_id in data["events"]:
        existing = data["events"][event_id]
        print(f"[INFO] Checklist already exists for {event_id} — status: {existing['status']}")
        return existing

    event_meta = events_csv.get(event_id, {})

    checklist = {
        "event_id": event_id,
        "event_name": event_meta.get("client_name", ""),
        "date": event_meta.get("date_event", ""),
        "status": "planned",
        "pax_estimated": 0,
        "pax_actual": None,
        "recorded_by": "",
        "recorded_at": None,
        "notes": "",
        "consumption": [],
        "variance_notes": [],
    }

    data["events"][event_id] = checklist
    _save_consumption(data)
    print(f"[OK] Checklist created for {event_id} — status: planned")
    return checklist


def record_item(
    event_id: str,
    product_id: str,
    qty_used: float,
    qty_returned: float = 0.0,
    source: str = "medicao_real",
    responsible: str = "",
) -> Dict:
    """
    Records actual consumption of one product for an event.
    If the item already exists, updates it.
    """
    catalog = _load_catalog()
    product = catalog.get(product_id)
    if not product:
        print(f"[ERROR] Product '{product_id}' not in catalog")
        return {}

    data = _load_consumption()

    # Auto-create checklist if not exists
    if event_id not in data["events"]:
        create_checklist(event_id)
        data = _load_consumption()

    checklist = data["events"][event_id]

    if checklist["status"] == "completed":
        print(f"[WARN] Event {event_id} is already completed. Use --force to override.")
        return {}

    # Mark as in_progress
    if checklist["status"] == "planned":
        checklist["status"] = "in_progress"

    net = round(qty_used - qty_returned, 4)

    # Find existing entry for this product or create new
    existing = next((c for c in checklist["consumption"] if c["product_id"] == product_id), None)
    item = {
        "product_id": product_id,
        "product_name": product["name"],
        "qty_used": qty_used,
        "qty_returned": qty_returned,
        "net_consumption": net,
        "unit": product["unit"],
        "source": source,
    }

    if existing:
        idx = checklist["consumption"].index(existing)
        checklist["consumption"][idx] = item
        print(f"[OK] Updated {product['name']}: used={qty_used}, returned={qty_returned}, net={net} {product['unit']}")
    else:
        checklist["consumption"].append(item)
        print(f"[OK] Recorded {product['name']}: used={qty_used}, returned={qty_returned}, net={net} {product['unit']}")

    data["events"][event_id] = checklist
    _save_consumption(data)
    return item


def complete_event(
    event_id: str,
    pax_actual: Optional[int] = None,
    notes: str = "",
    recorded_by: str = "",
) -> Dict:
    """
    Marks event checklist as completed.
    After this, kitchen_control.py (auto/real mode) uses real data for this event.
    """
    data = _load_consumption()

    if event_id not in data["events"]:
        print(f"[ERROR] No checklist for {event_id}. Run: python3 event_input.py create {event_id}")
        return {}

    checklist = data["events"][event_id]
    count = len(checklist["consumption"])

    if count == 0:
        print(f"[WARN] {event_id}: no items recorded. Complete anyway? (checklist will be empty)")

    checklist["status"] = "completed"
    checklist["recorded_at"] = datetime.now().isoformat()
    checklist["notes"] = notes or checklist.get("notes", "")
    checklist["recorded_by"] = recorded_by

    if pax_actual is not None:
        checklist["pax_actual"] = pax_actual

    data["events"][event_id] = checklist
    _save_consumption(data)

    total_cost = _estimate_cost(checklist)
    print(f"[OK] {event_id} marked as COMPLETED")
    print(f"     Items recorded : {count}")
    print(f"     Pax actual     : {pax_actual or 'not set'}")
    print(f"     Estimated cost : R$ {total_cost:,.2f}")
    print(f"     kitchen_control.py will now use REAL data for this event")
    return checklist


def _estimate_cost(checklist: Dict) -> float:
    """Quick cost estimate from recorded items using catalog prices."""
    catalog = _load_catalog()
    total = 0.0
    for item in checklist.get("consumption", []):
        product = catalog.get(item["product_id"])
        if product:
            total += item["net_consumption"] * product["unit_cost"]
    return round(total, 2)


def show_status(event_id: str):
    """Prints checklist status for one event."""
    data = _load_consumption()

    if event_id not in data["events"]:
        print(f"[INFO] No checklist for {event_id}")
        return

    checklist = data["events"][event_id]
    catalog = _load_catalog()

    status_icon = {
        "planned": "📋",
        "in_progress": "⚙️ ",
        "completed": "✅",
    }

    print(f"\n{status_icon.get(checklist['status'], '?')} Event: {event_id} — {checklist.get('event_name', '')}")
    print(f"   Status   : {checklist['status']}")
    print(f"   Date     : {checklist.get('date', '')}")
    print(f"   Pax      : estimated={checklist.get('pax_estimated',0)}  actual={checklist.get('pax_actual','—')}")
    print(f"   Recorded : {checklist.get('recorded_by','—')} @ {checklist.get('recorded_at','—')}")

    items = checklist.get("consumption", [])
    if items:
        print(f"\n   {'PRODUCT':<35} {'NET QTY':>10} {'UNIT':<6} {'COST':>10}  SOURCE")
        print("   " + "-" * 72)
        total_cost = 0.0
        for item in items:
            product = catalog.get(item["product_id"], {})
            unit_cost = product.get("unit_cost", 0)
            line_cost = item["net_consumption"] * unit_cost
            total_cost += line_cost
            print(
                f"   {item['product_name'][:35]:<35} "
                f"{item['net_consumption']:>10.2f} "
                f"{item['unit']:<6} "
                f"R$ {line_cost:>7,.2f}  "
                f"{item.get('source','')}"
            )
        print("   " + "-" * 72)
        print(f"   {'TOTAL CMV (estimado)':>51} R$ {total_cost:>7,.2f}")
    else:
        print("   (sem itens registrados)")

    if checklist.get("notes"):
        print(f"\n   Notes: {checklist['notes']}")


def list_events():
    """Lists all events and their checklist status."""
    data = _load_consumption()
    events_csv = _load_events_csv()

    # Merge: events in CSV that don't have checklists yet
    all_ids = set(data["events"].keys()) | set(events_csv.keys())

    print("\n" + "=" * 65)
    print("EVENT CHECKLISTS")
    print("=" * 65)
    print(f"{'EVENT':<12} {'TYPE':<14} {'DATE':<12} {'STATUS':<14} {'ITEMS'}")
    print("-" * 65)

    for eid in sorted(all_ids):
        checklist = data["events"].get(eid, {})
        ev_csv = events_csv.get(eid, {})
        status = checklist.get("status", "no checklist")
        items = len(checklist.get("consumption", []))
        ev_type = ev_csv.get("event_type", checklist.get("event_type", ""))
        date = ev_csv.get("date_event", checklist.get("date", ""))

        icon = {"completed": "✅", "in_progress": "⚙️ ", "planned": "📋"}.get(status, "  ")
        print(f"{eid:<12} {ev_type:<14} {date:<12} {icon} {status:<11} {items} itens")

    print("=" * 65)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "create":
        if len(args) < 2:
            print("Usage: create <event_id>")
            return
        create_checklist(args[1])

    elif cmd == "record":
        if len(args) < 4:
            print("Usage: record <event_id> <product_id> <qty_used> [--returned QTY] [--source texto]")
            return
        event_id = args[1]
        product_id = args[2]
        qty_used = float(args[3])
        qty_returned = 0.0
        source = "medicao_real"
        for i, a in enumerate(args):
            if a == "--returned" and i + 1 < len(args):
                qty_returned = float(args[i + 1])
            if a == "--source" and i + 1 < len(args):
                source = args[i + 1]
        record_item(event_id, product_id, qty_used, qty_returned, source=source)

    elif cmd == "complete":
        if len(args) < 2:
            print("Usage: complete <event_id> [--pax N] [--notes 'texto'] [--by nome]")
            return
        event_id = args[1]
        pax = None
        notes = ""
        by = ""
        for i, a in enumerate(args):
            if a == "--pax" and i + 1 < len(args):
                pax = int(args[i + 1])
            if a == "--notes" and i + 1 < len(args):
                notes = args[i + 1]
            if a == "--by" and i + 1 < len(args):
                by = args[i + 1]
        complete_event(event_id, pax_actual=pax, notes=notes, recorded_by=by)

    elif cmd == "status":
        if len(args) < 2:
            print("Usage: status <event_id>")
            return
        show_status(args[1])

    elif cmd == "list":
        list_events()

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: create | record | complete | status | list")


if __name__ == "__main__":
    _cli()
