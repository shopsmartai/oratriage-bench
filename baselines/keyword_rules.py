"""Keyword-rules baseline for OraTriage Bench: hand-written regex weights, no learning.

Usage: python3 baselines/keyword_rules.py   ->  results/keyword-rules.jsonl
Standard library only.
"""

import json
import math
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
POLICY = {"sec": 0.6, "conf": 0.45, "fix": 0.6, "hum": 0.6, "sev": 3.5}

sig = lambda x: 1 / (1 + math.exp(-x))


def lin(text, bias, rules):
    return bias + sum(w for pat, w in rules if re.search(pat, text, re.I))


YESNO = {
    "needs_human": (-1.2, [(r"\bprod\b", 1.0), (r"unable to login|cannot login|users? unable", 2.2), (r"all users", 1.6), (r"failed", 0.8),
                           (r"deadlock|ora-00060", 1.2), (r"unable to extend|ora-0165[34]", 1.6), (r"blocking|sessions waiting", 1.4),
                           (r"stopped|\bdown\b|refused", 1.0), (r"\d{3,} (requests|notifications)", 0.8), (r"0 active|not running", 1.0),
                           (r"sysadmin|dba role|grant", 1.2), (r"informational|completed successfully|cleared|restarted automatically", -2.8),
                           (r"\b(dev|test)\b", -1.4), (r"no users reported", -1.2)]),
    "security_risk": (-3, [(r"failed login|brute", 3.4), (r"unknown ip", 2.0), (r"grant|dba role|privilege", 3.0), (r"sysadmin", 1.0),
                           (r"audit", 0.8), (r"password", 1.5)]),
    "runbook_safe": (-0.6, [(r"autoextend off|unable to extend", 1.4), (r"mailer.*(stopped|refused)|smtp", 1.3), (r"pending", 0.8),
                            (r"restart", 0.6), (r"disk usage|filesystem", 0.4), (r"failed login|grant|dba role|security", -3.0),
                            (r"cutover|adop|ad-\d", -2.2), (r"deadlock", -0.8), (r"blocking", -0.4), (r"0 active|not running", -1.2),
                            (r"something is wrong", -1.5)]),
}
CHOICE = {
    "concurrent_manager": [(r"concurrent", 2), (r"standard manager|\bicm\b|fndlibr", 2), (r"pending", 1.2)],
    "tablespace": [(r"tablespace", 2.5), (r"unable to extend|ora-0165[34]", 2), (r"datafile|autoextend", 1)],
    "locking": [(r"lock|blocking", 2.2), (r"deadlock|ora-00060", 2.6), (r"sessions waiting|enq:", 1.2)],
    "workflow": [(r"workflow|mailer", 2.6), (r"notification", 1), (r"smtp|imap", 1)],
    "patching": [(r"adop|cutover|fs_clone|patch", 2.6), (r"ad-\d", 1.2)],
    "security": [(r"failed login|unknown ip", 2.6), (r"grant|dba role|privilege|audit", 2.4), (r"password", 1.5)],
    "performance": [(r"slow|cpu|elapsed|response time", 2.6), (r"awr|full table scan", 1.6)],
    "maintenance": [(r"informational|completed successfully|gather schema statistics|cleared", 3)],
}
SEV = (-1.6, [(r"\bprod\b", 0.9), (r"unable to login|users? unable|cutover failed", 3.0), (r"all users", 1.8), (r"unknown ip|failed login", 1.6),
              (r"dba role", 1.8), (r"unable to extend", 1.6), (r"deadlock", 1.0), (r"sessions waiting", 1.4), (r"stopped|refused", 0.8),
              (r"pending", 0.8), (r"0 active|not running", 1.2), (r"slow|high cpu", 0.6), (r"full table scan", 0.8), (r"\b9\d%", 0.8),
              (r"informational|completed successfully|cleared", -3), (r"\b(dev|test)\b", -1.2), (r"no users reported", -0.8)])




def predict(text):
    yes = {k: sig(lin(text, b, r)) for k, (b, r) in YESNO.items()}
    logits = {k: lin(text, 0, r) for k, r in CHOICE.items()}
    logits["unclear"] = 0.8
    m = max(logits.values())
    ex = {k: math.exp(v - m) for k, v in logits.items()}
    z = sum(ex.values())
    area = max(CHOICE, key=lambda k: ex[k])
    conf = max(ex.values()) / z
    sev = 4 * sig(lin(text, *SEV))  # 0-4
    p = POLICY
    if yes["security_risk"] >= p["sec"]: route = "security"
    elif conf < p["conf"]: route = "llm"
    elif yes["runbook_safe"] >= p["fix"]: route = "autofix"
    elif yes["needs_human"] >= p["hum"] and sev + 1 >= p["sev"]: route = "page"
    elif sev + 1 < 2: route = "log"
    else: route = "ticket"
    return {"route": route, "area": area, "severity": round(sev, 2), **{k: round(v, 4) for k, v in yes.items()}}


if __name__ == "__main__":
    gold = [json.loads(l) for l in (HERE / "data" / "oratriage-bench-v1.jsonl").read_text().splitlines() if l.strip()]
    out = []
    for g in gold:
        t0 = time.perf_counter()
        p = predict(g["text"])
        out.append({"id": g["id"], **p, "ms": round((time.perf_counter() - t0) * 1000, 3)})
    (HERE / "results" / "keyword-rules.jsonl").write_text("\n".join(json.dumps(o) for o in out) + "\n")
    (HERE / "results" / "keyword-rules.meta.json").write_text(json.dumps({
        "engine": "Keyword rules (baseline)", "cost_per_1k_usd": 0.0, "data_leaves_company": False,
        "notes": "Regex weights written by hand; no training data."}, indent=2))
    print(f"wrote {len(out)} predictions to results/keyword-rules.jsonl")
