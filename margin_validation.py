#!/usr/bin/env python3
"""
MARGIN VALIDATION
Reads DRE output and validates event margins against business thresholds.

Depends on:
  kitchen_data/dre_summary.json  (written by dre_engine.py)

Thresholds (configurable below):
  Gross margin >= 40%  → OK
  Gross margin  30-40% → WARNING
  Gross margin < 30%   → CRITICAL

  Net margin   >= 15%  → OK
  Net margin    5-15%  → WARNING
  Net margin   < 5%    → CRITICAL (or LOSS if negative)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "kitchen_data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

DRE_SUMMARY_FILE = DATA_DIR / "dre_summary.json"
REPORT_FILE = OUTPUT_DIR / "margin_report.json"

# Margin thresholds
GROSS_MARGIN_OK = 40.0       # >= this → OK
GROSS_MARGIN_WARN = 30.0     # >= this → WARNING  (below → CRITICAL)
NET_MARGIN_OK = 15.0
NET_MARGIN_WARN = 5.0


def load_dre_summary() -> Dict:
    if not DRE_SUMMARY_FILE.exists():
        raise FileNotFoundError(
            f"DRE summary not found at {DRE_SUMMARY_FILE}.\n"
            "Run dre_engine.py first."
        )
    with open(DRE_SUMMARY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def classify_gross_margin(margin: float) -> Tuple[str, str]:
    """Returns (status, note)."""
    if margin >= GROSS_MARGIN_OK:
        return "OK", "Margem bruta saudável"
    elif margin >= GROSS_MARGIN_WARN:
        return "WARNING", f"Margem bruta abaixo de {GROSS_MARGIN_OK}%"
    else:
        return "CRITICAL", f"Margem bruta abaixo de {GROSS_MARGIN_WARN}% — revisar CMV"


def classify_net_margin(margin: float) -> Tuple[str, str]:
    if margin < 0:
        return "LOSS", "Prejuízo líquido — evento destruiu valor"
    elif margin >= NET_MARGIN_OK:
        return "OK", "Margem líquida saudável"
    elif margin >= NET_MARGIN_WARN:
        return "WARNING", f"Margem líquida abaixo de {NET_MARGIN_OK}%"
    else:
        return "CRITICAL", f"Margem líquida abaixo de {NET_MARGIN_WARN}% — risco alto"


def validate_margins(dre_summary: Dict) -> List[Dict]:
    events = dre_summary.get("events_detail", [])
    results = []

    for evt in events:
        event_id = evt.get("event_id", "?")
        gross_margin = evt.get("gross_margin")
        net_margin = evt.get("net_margin")
        revenue = evt.get("revenue") or 0
        cmv = evt.get("cmv") or 0
        dre_status = evt.get("status", "")

        gross_status, gross_note = ("N/A", "Margem bruta ausente")
        net_status, net_note = ("N/A", "Margem líquida ausente")

        if gross_margin is not None:
            gross_status, gross_note = classify_gross_margin(gross_margin)
        if net_margin is not None:
            net_status, net_note = classify_net_margin(net_margin)

        # Overall event risk
        statuses = [gross_status, net_status]
        if "LOSS" in statuses or "CRITICAL" in statuses:
            overall = "CRITICAL"
        elif "WARNING" in statuses:
            overall = "WARNING"
        elif "N/A" in statuses:
            overall = "INCOMPLETE"
        else:
            overall = "OK"

        results.append({
            "event_id": event_id,
            "revenue": revenue,
            "cmv": cmv,
            "gross_margin_pct": gross_margin,
            "gross_margin_status": gross_status,
            "gross_margin_note": gross_note,
            "net_margin_pct": net_margin,
            "net_margin_status": net_status,
            "net_margin_note": net_note,
            "dre_status": dre_status,
            "overall": overall,
        })

    return results


def print_report(results: List[Dict], totals: Dict):
    status_icon = {
        "OK": "✅",
        "WARNING": "⚠️ ",
        "CRITICAL": "🚨",
        "LOSS": "🔴",
        "INCOMPLETE": "❓",
        "N/A": "—",
    }

    print("\n" + "=" * 80)
    print("MARGIN VALIDATION REPORT")
    print("=" * 80)
    print(
        f"\n{'EVENT':<12} {'REVENUE':>12} {'GROSS%':>8} {'GROSS':>9} "
        f"{'NET%':>7} {'NET':>9} {'OVERALL':>10}"
    )
    print("-" * 80)

    for r in results:
        gm = f"{r['gross_margin_pct']:.1f}%" if r["gross_margin_pct"] is not None else "N/A"
        nm = f"{r['net_margin_pct']:.1f}%"   if r["net_margin_pct"] is not None else "N/A"
        icon = status_icon.get(r["overall"], "?")
        print(
            f"{r['event_id']:<12} "
            f"R$ {r['revenue']:>10,.2f} "
            f"{gm:>7} {status_icon.get(r['gross_margin_status'], '?')} "
            f"{nm:>6} {status_icon.get(r['net_margin_status'], '?')} "
            f"  {icon} {r['overall']}"
        )

    print("-" * 80)

    total_rev = totals.get("revenue", 0)
    total_gross_pct = totals.get("gross_margin", 0)
    total_net_pct = totals.get("net_margin", 0)
    print(
        f"{'TOTAL':<12} R$ {total_rev:>10,.2f} "
        f"{total_gross_pct:.1f}%       "
        f"{total_net_pct:.1f}%"
    )

    # Issues
    issues = [r for r in results if r["overall"] in ("CRITICAL", "LOSS", "WARNING")]
    if issues:
        print(f"\n{'─' * 80}")
        print(f"ISSUES ({len(issues)}):")
        for r in issues:
            print(f"  [{r['overall']:8s}] {r['event_id']}")
            if r["gross_margin_status"] not in ("OK", "N/A"):
                print(f"           Gross: {r['gross_margin_note']}")
            if r["net_margin_status"] not in ("OK", "N/A"):
                print(f"           Net:   {r['net_margin_note']}")
    else:
        print("\n✅ All events within margin thresholds.")

    print("=" * 80)


def main():
    print("MARGIN VALIDATION — Orkestra Finance Brain")

    try:
        dre_summary = load_dre_summary()
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        return

    results = validate_margins(dre_summary)

    if not results:
        print("[ERROR] No event data found in dre_summary.json")
        return

    totals = dre_summary.get("totals", {})

    print_report(results, totals)

    # Save JSON report
    report = {
        "generated_at": datetime.now().isoformat(),
        "thresholds": {
            "gross_margin_ok": GROSS_MARGIN_OK,
            "gross_margin_warn": GROSS_MARGIN_WARN,
            "net_margin_ok": NET_MARGIN_OK,
            "net_margin_warn": NET_MARGIN_WARN,
        },
        "totals": totals,
        "events": results,
        "summary": {
            "ok": sum(1 for r in results if r["overall"] == "OK"),
            "warning": sum(1 for r in results if r["overall"] == "WARNING"),
            "critical": sum(1 for r in results if r["overall"] in ("CRITICAL", "LOSS")),
            "incomplete": sum(1 for r in results if r["overall"] == "INCOMPLETE"),
        },
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: output/margin_report.json")


if __name__ == "__main__":
    main()
