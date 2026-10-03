"""Score predictions against the OraTriage Bench gold answers.

Predictions: JSON Lines, one object per alert:
  {"id": "B001", "route": "page", "area": "concurrent_manager", "severity": 3,
   "needs_human": 0.91, "security_risk": 0.02, "runbook_safe": 0.10, "ms": 64}
Only "id" and "route" are required. Probabilities may be 0-1 floats or booleans.
Severity is on the 0-4 scale (0 Info ... 4 Critical).

Usage:
  python3 score.py results/my_model.jsonl
  python3 score.py --all          # score every file in results/ and rewrite LEADERBOARD.md
Standard library only.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
GOLD = HERE / "data" / "oratriage-bench-v1.jsonl"
ROUTES = {"security", "page", "autofix", "ticket", "log", "llm"}
URGENT, QUIET = {"page", "security"}, {"log", "ticket"}


def load(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def as_bool(v):
    return v >= 0.5 if isinstance(v, (int, float)) and not isinstance(v, bool) else bool(v)


def score(pred_path):
    gold = {g["id"]: g for g in load(GOLD)}
    preds = {p["id"]: p for p in load(pred_path) if p.get("route") in ROUTES}
    meta = json.loads((Path(pred_path).with_suffix(".meta.json")).read_text()) if Path(pred_path).with_suffix(".meta.json").exists() else {}
    ids = [i for i in gold if i in preds]
    n = len(ids)
    if not n:
        sys.exit(f"{pred_path}: no valid predictions")
    m = {"engine": meta.get("engine", Path(pred_path).stem), "n": n, "coverage": n / len(gold)}
    m["route_acc"] = sum(preds[i]["route"] == gold[i]["gold"]["route"] for i in ids) / n
    urgent = [i for i in ids if gold[i]["gold"]["route"] in URGENT]
    m["missed_urgent"] = sum(preds[i]["route"] in QUIET for i in urgent) / len(urgent) if urgent else None
    quiet = [i for i in ids if gold[i]["gold"]["route"] == "log"]
    m["false_pages"] = sum(preds[i]["route"] in URGENT for i in quiet) / len(quiet) if quiet else None
    for k in ("needs_human", "security_risk", "runbook_safe"):
        have = [i for i in ids if k in preds[i]]
        m[k] = sum(as_bool(preds[i][k]) == gold[i]["gold"][k] for i in have) / len(have) if have else None
    have = [i for i in ids if "area" in preds[i]]
    m["area_acc"] = sum(preds[i]["area"] == gold[i]["gold"]["area"] for i in have) / len(have) if have else None
    have = [i for i in ids if "severity" in preds[i]]
    m["severity_mae"] = sum(abs(float(preds[i]["severity"]) - gold[i]["gold"]["severity"]) for i in have) / len(have) if have else None
    for sl in ("ebs_apps", "db_tier", "security_noise", "hard"):
        grp = [i for i in ids if gold[i]["slice"] == sl]
        m[f"route_{sl}"] = sum(preds[i]["route"] == gold[i]["gold"]["route"] for i in grp) / len(grp) if grp else None
    ms = sorted(preds[i]["ms"] for i in ids if "ms" in preds[i])
    m["p50_ms"] = ms[len(ms) // 2] if ms else None
    m.update({k: meta.get(k) for k in ("cost_per_1k_usd", "data_leaves_company", "notes")})
    return m


def pct(x):
    return "–" if x is None else f"{x * 100:.1f}%"


def leaderboard(rows):
    L = ["# OraTriage Bench v1: leaderboard\n",
         "295 Oracle EBS / Database alerts, gold answers reviewed by an Oracle Apps DBA. "
         "Sorted by route accuracy. Partial runs (coverage < 100%) are listed but not ranked.\n",
         "| Engine | Coverage | Route acc. | Missed urgent ↓ | False pages ↓ | Needs DBA | Security | Area | Sev. err ↓ | p50 ms | $ / 1k | Data leaves? |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    full = sorted([r for r in rows if r["coverage"] == 1], key=lambda r: -r["route_acc"])
    part = [r for r in rows if r["coverage"] < 1]
    for r in full + part:
        num = lambda v, fmt: "–" if v is None else fmt.format(v)
        leaves = "–" if r["data_leaves_company"] is None else ("yes" if r["data_leaves_company"] else "no")
        name = r["engine"] + ("" if r["coverage"] == 1 else " (partial)")
        L.append(" | ".join([
            f"| {name}", pct(r["coverage"]), f"**{pct(r['route_acc'])}**", pct(r["missed_urgent"]), pct(r["false_pages"]),
            pct(r["needs_human"]), pct(r["security_risk"]), pct(r["area_acc"]), num(r["severity_mae"], "{:.2f}"),
            num(r["p50_ms"], "{:.0f}"), num(r["cost_per_1k_usd"], "${:.2f}"), leaves]) + " |")
    L += ["\n**Missed urgent**: alerts that needed a page or a security escalation but were routed to log or ticket. "
          "**False pages**: routine alerts (gold: log) that would have woken someone up.\n",
          "## Route accuracy by slice\n", "| Engine | EBS apps | DB tier | Security vs noise | Hard cases |", "|---|---|---|---|---|"]
    for r in full + part:
        L.append(f"| {r['engine']} | {pct(r['route_ebs_apps'])} | {pct(r['route_db_tier'])} | {pct(r['route_security_noise'])} | {pct(r['route_hard'])} |")
    notes = [f"- **{r['engine']}**: {r['notes']}" for r in full + part if r.get("notes")]
    if notes:
        L += ["\n## Notes\n"] + notes
    (HERE / "LEADERBOARD.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions", nargs="?")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.all:
        rows = [score(p) for p in sorted((HERE / "results").glob("*.jsonl"))]
        leaderboard(rows)
        print((HERE / "LEADERBOARD.md").read_text())
    elif a.predictions:
        print(json.dumps(score(a.predictions), indent=2))
    else:
        ap.print_help()
