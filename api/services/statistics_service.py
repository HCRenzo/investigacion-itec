"""Statistical tests applied to the project's own measurements (real orders or the runs of an experiment).

Input rows are (engine, lines, seconds). The service checks assumptions (normality, equal variances), compares
V1 vs V2 with parametric and non-parametric tests, relates workload to time (correlation, regression) and tests the
acceptance threshold. Each result carries a plain-language decision so it can be cited in the research write-up.
"""
from api.errors import DomainError
from api.repositories.order import OrderRepository
from api.services import stats


class NotEnoughDataError(DomainError):
    status_code = 422


def _decision(p: float | None, alpha: float, yes: str, no: str) -> str:
    if p is None:
        return "No calculable con estos datos."
    return f"{yes} (p = {p:.4g} < α = {alpha})." if p < alpha else f"{no} (p = {p:.4g} ≥ α = {alpha})."


class StatisticsService:
    def __init__(self, orders: OrderRepository):
        self.orders = orders

    def order_rows(self) -> list[dict]:
        return [{"engine": o.engine, "lines": len(o.items), "seconds": float(o.processing_seconds or 0)}
                for o in self.orders.recent(5000)]

    def analyze(self, rows: list[dict], *, alpha: float, threshold: float, source: str) -> dict:
        by: dict[str, list[dict]] = {}
        for r in rows:
            by.setdefault(r["engine"], []).append(r)
        groups = {e: [x["seconds"] for x in v] for e, v in by.items() if len(v) >= 3}
        if not groups:
            raise NotEnoughDataError("Se necesitan al menos 3 observaciones por motor. Genera pedidos o ejecuta un experimento.")

        descriptive = [{"engine": e, **stats.describe(v), "p90": stats.percentile(v, 90), "p95": stats.percentile(v, 95),
                        "p99": stats.percentile(v, 99)} for e, v in sorted(groups.items())]

        normality = []
        for e, v in sorted(groups.items()):
            jb = stats.jarque_bera(v)
            normality.append({"engine": e, "n": len(v), **jb, "normal": jb["p"] >= alpha,
                              "decision": _decision(jb["p"], alpha, "Se rechaza normalidad: usar pruebas no paramétricas",
                                                    "No se rechaza normalidad")})

        out = {"source": source, "alpha": alpha, "threshold": threshold, "n_total": len(rows),
               "descriptive": descriptive, "normality": normality, "variance": None, "comparison": None,
               "correlation": [], "threshold_tests": []}

        a, b = groups.get("v1"), groups.get("v2")
        if a and b:
            lev = stats.levene([a, b])
            out["variance"] = {**lev, "equal": lev["p"] >= alpha,
                               "decision": _decision(lev["p"], alpha, "Varianzas distintas: usar Welch o no paramétrica",
                                                     "No se rechaza igualdad de varianzas")}
            welch, mw = stats.welch(a, b, 1 - alpha), stats.mann_whitney(a, b)
            kw, an = stats.kruskal_wallis([a, b]), stats.anova_one_way([a, b])
            lo, hi = stats.bootstrap_median_diff(a, b, reps=5000, confidence=1 - alpha)
            all_normal = all(n["normal"] for n in normality)
            out["comparison"] = {
                "median_v1": stats.percentile(a, 50), "median_v2": stats.percentile(b, 50),
                "delta_median": stats.percentile(a, 50) - stats.percentile(b, 50), "ci_low": lo, "ci_high": hi,
                "reduction_pct": (1 - stats.percentile(b, 50) / stats.percentile(a, 50)) * 100 if stats.percentile(a, 50) else 0.0,
                "welch": welch, "mann_whitney": mw, "kruskal_wallis": kw, "anova": an,
                "recommended": "welch" if all_normal and out["variance"]["equal"] else "mann_whitney",
                "decision": _decision(mw["p"], alpha, "V2 difiere significativamente de V1 (Mann-Whitney)",
                                      "No hay diferencia significativa entre V1 y V2 (Mann-Whitney)"),
                "welch_decision": _decision(welch["p"], alpha, "Diferencia significativa de medias (Welch)",
                                            "Sin diferencia significativa de medias (Welch)"),
            }

        for e, v in sorted(by.items()):
            if len(v) < 3:
                continue
            xs, ys = [x["lines"] for x in v], [x["seconds"] for x in v]
            sp, pe, reg = stats.spearman(xs, ys), stats.correlation(xs, ys), stats.linear_regression(xs, ys)
            out["correlation"].append({"engine": e, "n": len(v), "distinct_sizes": len(set(xs)), "spearman": sp, "pearson": pe,
                                       "regression": reg,
                                       "decision": _decision(sp["p"], alpha, "El tiempo depende del tamaño del pedido",
                                                             "No hay relación significativa entre tamaño y tiempo") if sp["p"] is not None
                                       else "Un solo tamaño de pedido: no se puede evaluar la relación."})

        for e, v in sorted(groups.items()):
            ok = sum(1 for x in v if x <= threshold)
            lo, hi = stats.wilson_interval(ok, len(v))
            t = stats.one_sample_t(v, threshold, 1 - alpha)
            p95 = stats.percentile(v, 95)
            out["threshold_tests"].append({
                "engine": e, "n": len(v), "within": ok, "proportion": ok / len(v), "wilson_low": lo, "wilson_high": hi,
                "p95": p95, "meets_p95": p95 <= threshold, "t": t["t"], "p_less": t["p_less"], "mean": t["mean"],
                "decision": _decision(t["p_less"], alpha, f"La media es significativamente menor que {threshold:g} s",
                                      f"No se demuestra que la media sea menor que {threshold:g} s")})
        return out
