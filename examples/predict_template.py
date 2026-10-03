"""Template: run your own system on OraTriage Bench and write a results file.

Replace decide() with a call to your model, then:
  python3 examples/predict_template.py my-system
  python3 score.py results/my-system.jsonl
"""

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def decide(text):
    """Return at least {"route": ...}. Optional: area, severity (0-4), needs_human, security_risk, runbook_safe."""
    raise NotImplementedError("call your model here")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "my-system"
    out = []
    for line in (HERE / "data" / "oratriage-bench-v1.jsonl").read_text().splitlines():
        alert = json.loads(line)
        t0 = time.perf_counter()
        pred = decide(alert["text"])  # send ONLY the text: never the gold answers or rationale
        out.append({"id": alert["id"], **pred, "ms": round((time.perf_counter() - t0) * 1000, 1)})
    (HERE / "results" / f"{name}.jsonl").write_text("\n".join(json.dumps(o) for o in out) + "\n")
    print(f"wrote results/{name}.jsonl")
