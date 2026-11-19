#!/usr/bin/env python3
"""Runs the controlled V1 vs V2 experiment from the terminal (no request time limit) and writes the raw data.

Defaults follow the article's protocol: sizes 10/100/500/1500, 30 measured runs + 5 warm-up per cell.
Outputs (in --out, default scripts/.run/experimento): corridas.csv, calentamiento.csv, condiciones.csv,
comparaciones.csv and experimento.json.

    .venv/bin/python scripts/run_experiment.py --sizes 10 100 500 --replicates 30 --work-factor 1
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("EXPERIMENT_MAX_SECONDS", "86400")

from api.config import settings  # noqa: E402
from api.services.experiment_service import ExperimentService  # noqa: E402


def write_csv(path: Path, rows: list[dict]) -> None:
    if rows:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", type=int, nargs="+", default=[10, 100, 500, 1500])
    ap.add_argument("--replicates", type=int, default=30)
    ap.add_argument("--warmup", type=int, default=5)
    ap.add_argument("--work-factor", type=int, default=1, help="intensidad fija de V1")
    ap.add_argument("--catalog-size", type=int, default=200)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--threshold", type=float, default=20.0)
    ap.add_argument("--bootstrap-reps", type=int, default=10_000)
    ap.add_argument("--out", type=Path, default=ROOT / "scripts" / ".run" / "experimento")
    a = ap.parse_args()

    result = ExperimentService(settings).run(
        sizes=a.sizes, replicates=a.replicates, warmup=a.warmup, work_factor=a.work_factor, catalog_size=a.catalog_size,
        seed=a.seed, alpha=a.alpha, threshold=a.threshold, bootstrap_reps=a.bootstrap_reps)
    a.out.mkdir(parents=True, exist_ok=True)
    write_csv(a.out / "corridas.csv", result["runs"])
    write_csv(a.out / "calentamiento.csv", result["warmup"])
    write_csv(a.out / "condiciones.csv", result["cells"])
    write_csv(a.out / "comparaciones.csv", result["comparisons"])
    (a.out / "experimento.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{'lineas':>7} {'med V1':>9} {'med V2':>9} {'p95 V1':>9} {'p95 V2':>9} {'reduccion':>10} {'p':>9}")
    cells = {(c["engine"], c["lines"]): c for c in result["cells"]}
    for c in result["comparisons"]:
        n = c["lines"]
        print(f"{n:>7} {c['median_v1']:>9.4f} {c['median_v2']:>9.4f} {cells['v1', n]['p95']:>9.4f} "
              f"{cells['v2', n]['p95']:>9.4f} {c['reduction_pct']:>9.1f}% {c['p']:>9.4g}")
    print(f"\nDatos en {a.out}")


if __name__ == "__main__":
    main()
