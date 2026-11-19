"""Controlled experiment: receipt time of engine V1 vs V2 under different workloads.

Follows the protocol of the research article: factorial design (engine x order size), warm-up runs that are
discarded and reported, n measured runs per cell in randomized order, the SAME order for both engines at each size,
raw data kept per run, median / p95 / p99 reporting, Mann-Whitney U with effect size in seconds and percent,
bootstrap CI for the difference of medians, and an acceptance criterion (p95 <= threshold) declared beforehand.
Everything runs in memory against a synthetic catalog: it never touches real stock or orders.
"""
import math
import os
import platform
import random
import subprocess
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from decimal import Decimal
from itertools import product as cartesian
from pathlib import Path

from api.config import Settings
from api.errors import DomainError
from api.services import stats
from api.services.receipt import InMemoryCatalog, OrderLine, ReceiptEngineFactory

ENGINES = ("v1", "v2")
# Estimated total allowed for one request. Serverless functions are cut off early; locally (or with the
# scripts/run_experiment.py CLI) the full-size campaign of the article fits.
TIME_BUDGET_SECONDS = float(os.getenv("EXPERIMENT_MAX_SECONDS") or (45 if os.getenv("VERCEL") else 900))


class ExperimentTooLargeError(DomainError):
    status_code = 422


def environment() -> dict:
    """Declares where the measurements were taken (a control variable of the study)."""
    commit = os.getenv("VERCEL_GIT_COMMIT_SHA")
    if not commit:
        try:
            commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=2,
                                    cwd=Path(__file__).resolve().parents[2]).stdout.strip() or None
        except Exception:
            commit = None
    try:
        mem_gb = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30, 1)
    except (ValueError, OSError, AttributeError):
        mem_gb = None
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "system": f"{platform.system()} {platform.release()}", "machine": platform.machine(),
            "cpu_count": os.cpu_count(), "memory_gb": mem_gb, "commit": commit,
            "serverless": bool(os.getenv("VERCEL")), "database": None,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "argv": Path(sys.argv[0]).name}


class ExperimentService:
    def __init__(self, settings: Settings):
        self.settings = settings

    # ---- helpers (shared with the performance module) -----------------------
    @staticmethod
    def make_catalog(size: int) -> InMemoryCatalog:
        return InMemoryCatalog({f"P-{i:03d}": {"name": f"Producto {i}", "price": f"{5 + (i * 7) % 90}.{(i * 13) % 100:02d}"}
                                for i in range(size)})

    @staticmethod
    def make_order(rng: random.Random, lines: int, catalog_size: int) -> list[OrderLine]:
        return [OrderLine(f"P-{rng.randrange(catalog_size):03d}", rng.randint(1, 5)) for _ in range(lines)]

    def make_engine(self, name: str, work_factor: int):
        # Fixed work factor (no time targeting): the intensity of V1 is an explicit experimental setting.
        settings = Settings(**{**self.settings.__dict__, "legacy_work_factor": work_factor, "legacy_target_seconds": None})
        return ReceiptEngineFactory(settings).create(name, Decimal("0.21"))

    # ---- run ---------------------------------------------------------------
    def run(self, *, sizes: list[int], replicates: int, warmup: int, work_factor: int, catalog_size: int,
            seed: int, alpha: float, threshold: float, bootstrap_reps: int) -> dict:
        sizes = sorted(set(sizes))
        catalog = self.make_catalog(catalog_size)
        rng = random.Random(seed)
        orders = {n: self.make_order(rng, n, catalog_size) for n in sizes}
        engines = {(e, n): self.make_engine(e, work_factor) for e in ENGINES for n in sizes}

        # Pilot: one run per cell tells us the cost before committing to the whole plan.
        estimate = 0.0
        for key, eng in engines.items():
            estimate += eng.calculate(orders[key[1]], catalog).processing_seconds * (replicates + warmup)
        if estimate > TIME_BUDGET_SECONDS:
            raise ExperimentTooLargeError(
                f"El experimento tardaría unos {estimate:.0f} s (máximo {TIME_BUDGET_SECONDS:.0f} s). "
                "Reduce repeticiones, tamaños de pedido o la intensidad de V1, o ejecútalo con scripts/run_experiment.py.")

        warmup_log = []
        for key, eng in engines.items():  # discarded, but reported
            for k in range(warmup):
                r = eng.calculate(orders[key[1]], catalog)
                warmup_log.append({"engine": key[0], "lines": key[1], "seconds": r.processing_seconds})

        plan = [(e, n) for e, n in cartesian(ENGINES, sizes) for _ in range(replicates)]
        rng.shuffle(plan)  # randomization removes drift (CPU, caches) as a systematic effect
        times = {key: [] for key in engines}
        cpu = {key: [] for key in engines}
        totals = {}
        run_log = []
        for number, (e, n) in enumerate(plan, 1):
            c0 = time.process_time()
            receipt = engines[(e, n)].calculate(orders[n], catalog)
            cpu_s = time.process_time() - c0
            times[(e, n)].append(receipt.processing_seconds)
            cpu[(e, n)].append(cpu_s)
            totals[(e, n)] = (str(receipt.total), receipt.item_count)
            run_log.append({"run": number, "engine": e, "lines": n, "seconds": receipt.processing_seconds,
                            "cpu_seconds": round(cpu_s, 6), "total": str(receipt.total)})

        memory = self._peak_memory(engines, orders, catalog)
        result = self._analyze(sizes, replicates, warmup, work_factor, catalog_size, seed, alpha, threshold,
                               bootstrap_reps, times, cpu, totals, memory, run_log, warmup_log)
        result["environment"] = environment()
        return result

    @staticmethod
    def _peak_memory(engines, orders, catalog) -> dict:
        """Peak Python heap per cell (one extra, untimed run: tracemalloc slows execution down)."""
        peaks = {}
        for (e, n), eng in engines.items():
            tracemalloc.start()
            eng.calculate(orders[n], catalog)
            peaks[(e, n)] = tracemalloc.get_traced_memory()[1] / 1024
            tracemalloc.stop()
        return peaks

    # ---- analysis ------------------------------------------------------------
    @staticmethod
    def _analyze(sizes, replicates, warmup, work_factor, catalog_size, seed, alpha, threshold, boot, times, cpu,
                 totals, memory, run_log, warmup_log) -> dict:
        confidence = 1 - alpha
        cells = []
        for e, n in cartesian(ENGINES, sizes):
            v = times[(e, n)]
            cells.append({"engine": e, "lines": n, **stats.describe(v, confidence),
                          "p90": stats.percentile(v, 90), "p95": stats.percentile(v, 95), "p99": stats.percentile(v, 99),
                          "cpu_mean": stats.mean(cpu[(e, n)]), "peak_memory_kb": memory[(e, n)],
                          "meets_threshold": stats.percentile(v, 95) <= threshold})

        comparisons = []
        for n in sizes:
            a, b = times[("v1", n)], times[("v2", n)]
            med1, med2 = stats.percentile(a, 50), stats.percentile(b, 50)
            lo, hi = stats.bootstrap_median_diff(a, b, reps=boot, confidence=confidence, seed=seed + n)
            mw = stats.mann_whitney(a, b)
            welch = stats.welch(a, b, confidence)
            comparisons.append({
                "lines": n, "median_v1": med1, "median_v2": med2, "delta_median": med1 - med2,
                "ci_low": lo, "ci_high": hi, "reduction_pct": (1 - med2 / med1) * 100 if med1 else 0.0,
                "speedup": med1 / med2 if med2 else None,
                "u": mw["u"], "z": mw["z"], "p": mw["p"], "rank_biserial": mw["rank_biserial"],
                "reject_h0": mw["p"] < alpha,
                "welch_t": welch["t"], "welch_df": welch["df"], "welch_p": welch["p"], "cohen_d": welch["cohen_d"],
                "same_total": totals[("v1", n)] == totals[("v2", n)],
            })

        anova = None
        if len(sizes) >= 2 and replicates >= 2:
            logged = {(ENGINES.index(e), sizes.index(n)): [math.log(x) for x in v if x > 0]
                      for (e, n), v in times.items()}
            if all(len(v) == replicates for v in logged.values()):
                anova = stats.anova_two_way(logged)
                anova["factors"] = {"A": "Motor", "B": "Líneas por pedido", "AB": "Motor × Líneas", "E": "Error"}
                anova["response"] = "ln(tiempo)"

        speedups = [c["speedup"] for c in comparisons if c["speedup"]]
        return {
            "design": {
                "type": f"Factorial completo 2 × {len(sizes)}, {replicates} corridas medidas por celda",
                "response": "Tiempo de generación del recibo (s): mediana, p95 y p99",
                "factors": [{"name": "Motor de recibo", "levels": ["V1 (heredado)", "V2 (optimizado)"]},
                            {"name": "Líneas por pedido", "levels": sizes}],
                "controlled": [f"Catálogo sintético de {catalog_size} productos", f"Intensidad de V1 = {work_factor}",
                               "Mismo pedido para ambos motores en cada tamaño", "Misma sesión y mismo proceso"],
                "randomization": f"Orden de las {len(run_log)} corridas aleatorizado (semilla {seed})",
                "warmup": f"{warmup} corridas de calentamiento por celda, descartadas ({len(warmup_log)} en total)",
                "analysis": f"Mann-Whitney U; IC {confidence:.0%} de la diferencia de medianas por remuestreo "
                            f"({boot} réplicas); tamaño del efecto en segundos y % de reducción",
                "alpha": alpha, "threshold": threshold, "runs": len(run_log), "seed": seed, "warmup_runs": warmup,
                "replicates": replicates, "work_factor": work_factor, "catalog_size": catalog_size,
                "h0": "El tiempo de generación con V2 no es menor que con V1 (sin reducción significativa).",
                "h1": f"V2 reduce de forma significativa el tiempo de generación, con p95 ≤ {threshold:g} s.",
            },
            "cells": cells, "comparisons": comparisons, "anova": anova, "runs": run_log, "warmup": warmup_log,
            "conclusion": {
                "all_reject_h0": all(c["reject_h0"] for c in comparisons),
                "v2_meets_threshold": all(c["meets_threshold"] for c in cells if c["engine"] == "v2"),
                "v1_meets_threshold": all(c["meets_threshold"] for c in cells if c["engine"] == "v1"),
                "median_speedup": stats.mean(speedups) if speedups else None,
                "outputs_identical": all(c["same_total"] for c in comparisons),
            },
        }
