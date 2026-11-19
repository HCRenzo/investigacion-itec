"""Software quality evaluation (ISO/IEC 25010): what is measured automatically, and what is declared as not measured.

* Functional correctness: V1 and V2 must produce identical receipts on randomized orders.
* Maintainability: static metrics of each receipt engine (size, cyclomatic complexity, nesting depth).
* Test suite inventory and CI gate.
"""
import ast
import random
from decimal import Decimal
from pathlib import Path

from api.config import Settings
from api.services.experiment_service import ExperimentService
from api.services.receipt import ReceiptEngineFactory

ROOT = Path(__file__).resolve().parents[2]
RECEIPT_FILES = {"v1": "api/services/receipt/legacy.py", "v2": "api/services/receipt/fast.py",
                 "base": "api/services/receipt/base.py"}
_BRANCHES = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.IfExp, ast.comprehension, ast.Assert)
_NESTING = (ast.If, ast.For, ast.While, ast.Try, ast.With)


def _complexity(fn: ast.AST) -> int:
    score = 1
    for node in ast.walk(fn):
        if isinstance(node, _BRANCHES):
            score += 1
        elif isinstance(node, ast.BoolOp):
            score += len(node.values) - 1
    return score


def _depth(node: ast.AST, level: int = 0) -> int:
    deepest = level
    for child in ast.iter_child_nodes(node):
        deepest = max(deepest, _depth(child, level + 1 if isinstance(child, _NESTING) else level))
    return deepest


def file_metrics(path: Path) -> dict | None:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    tree = ast.parse(source)
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    lines = source.splitlines()
    code = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    per_fn = [{"name": f.name, "complexity": _complexity(f), "nesting": _depth(f)} for f in funcs]
    total_cc = sum(f["complexity"] for f in per_fn)
    return {"file": str(path.relative_to(ROOT)), "lines": len(lines), "code_lines": len(code),
            "functions": len(funcs), "total_complexity": total_cc,
            "max_complexity": max((f["complexity"] for f in per_fn), default=0),
            "avg_complexity": round(total_cc / len(funcs), 2) if funcs else 0.0,
            "max_nesting": max((f["nesting"] for f in per_fn), default=0),
            "worst": sorted(per_fn, key=lambda f: -f["complexity"])[:3]}


class QualityService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.experiments = ExperimentService(settings)

    def functional_equivalence(self, cases: int, seed: int) -> dict:
        """V1 and V2 must agree on every receipt: same lines, subtotal, tax and total."""
        rng = random.Random(seed)
        catalog = self.experiments.make_catalog(30)
        v1, v2 = self.experiments.make_engine("v1", 1), self.experiments.make_engine("v2", 1)
        failures = []
        for case in range(cases):
            order = self.experiments.make_order(rng, rng.randint(1, 40), 30)
            a, b = v1.calculate(order, catalog), v2.calculate(order, catalog)
            if (a.subtotal, a.tax, a.total, a.item_count) != (b.subtotal, b.tax, b.total, b.item_count) or \
                    [(i.key, i.line_total) for i in a.items] != [(i.key, i.line_total) for i in b.items]:
                failures.append({"case": case, "lines": len(order), "v1_total": str(a.total), "v2_total": str(b.total)})
        # Monetary precision: the tax rounds half-up to cents and the total is the sum of exact Decimals.
        sample = v2.calculate(self.experiments.make_order(rng, 5, 30), catalog)
        exact = sample.subtotal + sample.tax == sample.total
        return {"cases": cases, "passed": cases - len(failures), "failed": len(failures), "failures": failures[:5],
                "agreement_pct": 100 * (cases - len(failures)) / cases if cases else 100.0,
                "decimal_exact": exact, "seed": seed}

    @staticmethod
    def maintainability() -> dict:
        return {k: file_metrics(ROOT / v) for k, v in RECEIPT_FILES.items()}

    @staticmethod
    def tests_inventory() -> dict:
        folder = ROOT / "tests"
        files, total = [], 0
        for f in sorted(folder.glob("test_*.py")) if folder.is_dir() else []:
            names = [n.name for n in ast.walk(ast.parse(f.read_text(encoding="utf-8")))
                     if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
            files.append({"file": f.name, "tests": len(names)})
            total += len(names)
        workflows = ROOT / ".github" / "workflows"
        return {"total": total, "files": files,
                "ci_workflows": sorted(w.name for w in workflows.glob("*.yml")) if workflows.is_dir() else []}

    def report(self, cases: int, seed: int) -> dict:
        equivalence = self.functional_equivalence(cases, seed)
        maint = self.maintainability()
        tests = self.tests_inventory()
        v1, v2 = maint.get("v1"), maint.get("v2")
        characteristics = [
            {"characteristic": "Idoneidad funcional", "sub": "Corrección funcional", "status": "medido",
             "evidence": f"V1 y V2 coinciden en {equivalence['passed']}/{equivalence['cases']} pedidos aleatorios "
                         f"({equivalence['agreement_pct']:.1f} %)."},
            {"characteristic": "Eficiencia de desempeño", "sub": "Comportamiento temporal", "status": "medido",
             "evidence": "Módulo Experimentos: mediana, p95 y p99 por motor y tamaño de pedido."},
            {"characteristic": "Eficiencia de desempeño", "sub": "Utilización de recursos", "status": "parcial",
             "evidence": "El experimento registra tiempo de CPU y pico de memoria del heap de Python por celda; "
                         "no mide CPU/memoria del sistema ni de la base de datos."},
            {"characteristic": "Eficiencia de desempeño", "sub": "Capacidad", "status": "parcial",
             "evidence": "Rendimiento (recibos/s) de un usuario secuencial; no hay prueba de carga concurrente."},
            {"characteristic": "Mantenibilidad", "sub": "Analizabilidad / Modificabilidad",
             "status": "medido" if v1 and v2 else "no disponible",
             "evidence": (f"Complejidad ciclomática total V1 {v1['total_complexity']} vs V2 {v2['total_complexity']}; "
                          f"anidamiento máx. {v1['max_nesting']} vs {v2['max_nesting']}.") if v1 and v2 else "Código fuente no disponible en este despliegue."},
            {"characteristic": "Mantenibilidad", "sub": "Capacidad de ser probado", "status": "medido",
             "evidence": f"{tests['total']} pruebas automáticas; CI: {', '.join(tests['ci_workflows']) or 'no detectada'}."},
            {"characteristic": "Fiabilidad", "sub": "Madurez / Tolerancia a fallos", "status": "no medido",
             "evidence": "No se evaluó tasa de fallos ni recuperación."},
            {"characteristic": "Seguridad", "sub": "Confidencialidad / Autenticidad", "status": "no medido",
             "evidence": "No se evaluó en este estudio (el CI ejecuta CodeQL y auditoría de dependencias)."},
            {"characteristic": "Usabilidad / Compatibilidad / Portabilidad", "sub": "—", "status": "no medido",
             "evidence": "Fuera del alcance del estudio."},
        ]
        return {"equivalence": equivalence, "maintainability": maint, "tests": tests, "characteristics": characteristics}
