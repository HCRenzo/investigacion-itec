import pytest
from fastapi.testclient import TestClient

from api.index import app
from api.services import stats


def test_t_and_f_distributions_match_reference_values():
    assert stats.t_two_sided_p(2.0, 10) == pytest.approx(0.0734, abs=1e-3)
    assert stats.t_critical(10) == pytest.approx(2.228, abs=1e-3)
    assert stats.f_upper_p(4.0, 2, 10) == pytest.approx(0.0529, abs=1e-3)


def test_percentile_and_mann_whitney():
    assert stats.percentile([1, 2, 3, 4], 50) == 2.5
    r = stats.mann_whitney([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
    assert r["u"] == 0 and r["p"] < 0.05 and r["rank_biserial"] == -1
    same = stats.mann_whitney([1, 2, 3], [1, 2, 3])
    assert same["p"] > 0.9


def test_bootstrap_ci_contains_true_difference():
    lo, hi = stats.bootstrap_median_diff([10, 11, 12, 13, 14], [1, 2, 3, 4, 5], reps=500, seed=1)
    assert lo < 9 < hi


@pytest.fixture()
def admin():
    client = TestClient(app)
    token = client.post("/api/admin/login", json={"email": "admin@test.local", "password": "admin-pass-1"}).json()["token"]
    return client, {"Authorization": f"Bearer {token}"}


def test_experiment_reports_everything_needed_for_the_article(admin):
    client, h = admin
    r = client.post("/api/admin/experiments/run", headers=h, json={
        "sizes": [5, 20], "replicates": 6, "warmup": 1, "catalog_size": 15, "bootstrap_reps": 300})
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["runs"]) == 2 * 2 * 6 and len(data["warmup"]) == 2 * 2 * 1
    cell = data["cells"][0]
    assert {"median", "p95", "p99", "cpu_mean", "peak_memory_kb", "meets_threshold"} <= cell.keys()
    cmp = data["comparisons"][0]
    assert {"delta_median", "ci_low", "ci_high", "p", "reduction_pct"} <= cmp.keys()
    assert data["conclusion"]["outputs_identical"] and data["anova"]["rows"]
    assert data["environment"]["python"]


def test_experiment_is_reproducible_in_design_and_rejects_oversized_runs(admin, monkeypatch):
    client, h = admin
    body = {"sizes": [3, 6], "replicates": 3, "warmup": 0, "catalog_size": 10, "bootstrap_reps": 200, "seed": 7}
    a, b = (client.post("/api/admin/experiments/run", headers=h, json=body).json() for _ in range(2))
    assert [(x["engine"], x["lines"]) for x in a["runs"]] == [(x["engine"], x["lines"]) for x in b["runs"]]  # same random order
    monkeypatch.setattr("api.services.experiment_service.TIME_BUDGET_SECONDS", 0.0)
    assert client.post("/api/admin/experiments/run", headers=h, json=body).status_code == 422


def test_quality_and_performance_endpoints(admin):
    client, h = admin
    q = client.get("/api/admin/quality?cases=20", headers=h).json()
    assert q["equivalence"]["failed"] == 0 and q["tests"]["total"] > 0
    assert q["maintainability"]["v1"]["total_complexity"] > q["maintainability"]["v2"]["total_complexity"]
    b = client.post("/api/admin/performance/benchmark", headers=h,
                    json={"sizes": [5, 20], "repetitions": 2, "catalog_size": 10}).json()
    assert b["complexity"]["v2"]["slope"] is not None
    assert client.get("/api/admin/performance/orders", headers=h).status_code == 200
    assert TestClient(app).get("/api/admin/quality").status_code == 401


def test_extra_distributions_match_reference_values():
    assert stats.chi2_upper_p(3.841, 1) == pytest.approx(0.05, abs=1e-3)
    assert stats.chi2_upper_p(5.991, 2) == pytest.approx(0.05, abs=1e-3)
    assert stats.chi2_upper_p(18.307, 10) == pytest.approx(0.05, abs=1e-3)
    assert stats.correlation([1, 2, 3, 4, 5], [2, 4, 6, 8, 10.5])["r"] > 0.99
    assert stats.linear_regression([1, 2, 3, 4], [3, 5, 7, 9])["slope"] == pytest.approx(2)
    assert stats.kruskal_wallis([[1, 2, 3], [7, 8, 9]])["p"] < 0.1
    assert stats.levene([[1, 2, 3, 4, 5], [1, 2, 3, 4, 5]])["p"] > 0.9


def test_statistics_module_on_samples_and_orders(admin):
    client, h = admin
    exp = client.post("/api/admin/experiments/run", headers=h, json={
        "sizes": [5, 20], "replicates": 8, "warmup": 0, "catalog_size": 10, "bootstrap_reps": 200}).json()
    samples = [{"engine": r["engine"], "lines": r["lines"], "seconds": r["seconds"]} for r in exp["runs"]]
    r = client.post("/api/admin/statistics/analyze", headers=h, json={"source": "samples", "samples": samples})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["comparison"]["mann_whitney"]["p"] < 0.05 and d["comparison"]["recommended"]
    assert d["normality"] and d["variance"] and d["correlation"][0]["spearman"]["r"] is not None
    assert d["threshold_tests"][0]["meets_p95"]
    empty = client.post("/api/admin/statistics/analyze", headers=h, json={"source": "samples", "samples": []})
    assert empty.status_code == 422


def test_report_dataset_aggregates_real_tables(admin):
    client, h = admin
    d = client.get("/api/admin/reports/dataset", headers=h)
    assert d.status_code == 200, d.text
    data = d.json()
    assert {"orders", "by_product", "stock", "movements", "database"} <= data.keys()
    assert data["stock"] and {"product", "category", "stock"} <= data["stock"][0].keys()
    assert TestClient(app).get("/api/admin/reports/dataset").status_code == 401
