"""Small statistics toolkit (standard library only) used by the experiment and performance modules.

Covers: descriptive statistics, Student t / F distributions, Welch's t-test, balanced two-way ANOVA and a
log-log regression to estimate empirical complexity.
"""
import math
import random
from collections.abc import Sequence


# ---- descriptive ---------------------------------------------------------
def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def variance(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def stdev(xs: Sequence[float]) -> float:
    return math.sqrt(variance(xs))


def percentile(xs: Sequence[float], q: float) -> float:
    """Linear-interpolated percentile, q in [0, 100]."""
    s = sorted(xs)
    if not s:
        return 0.0
    pos = (len(s) - 1) * q / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


# ---- distributions -------------------------------------------------------
def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > tiny else tiny)
        c = 1 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > tiny else tiny)
        c = 1 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-12:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1 - front * _betacf(b, a, 1 - x) / b


def t_two_sided_p(t: float, df: float) -> float:
    """P(|T| >= |t|) for Student's t with df degrees of freedom."""
    if df <= 0:
        return 1.0
    return betainc(df / 2, 0.5, df / (df + t * t))


def t_critical(df: float, confidence: float = 0.95) -> float:
    """Two-sided critical value (bisection on the CDF)."""
    alpha = 1 - confidence
    lo, hi = 0.0, 1000.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if t_two_sided_p(mid, df) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def f_upper_p(f: float, d1: float, d2: float) -> float:
    """P(F >= f) for the F distribution."""
    if f <= 0 or d1 <= 0 or d2 <= 0:
        return 1.0
    return betainc(d2 / 2, d1 / 2, d2 / (d2 + d1 * f))


# ---- inference -----------------------------------------------------------
def describe(xs: Sequence[float], confidence: float = 0.95) -> dict:
    n = len(xs)
    m, s = mean(xs), stdev(xs)
    half = t_critical(n - 1, confidence) * s / math.sqrt(n) if n > 1 else 0.0
    return {"n": n, "mean": m, "sd": s, "min": min(xs), "max": max(xs), "median": percentile(xs, 50),
            "ci_low": m - half, "ci_high": m + half, "cv": (s / m) if m else 0.0}


def welch(a: Sequence[float], b: Sequence[float], confidence: float = 0.95) -> dict:
    """Welch's t-test for mean(a) - mean(b), with Cohen's d and a confidence interval for the difference."""
    na, nb = len(a), len(b)
    va, vb = variance(a), variance(b)
    se2 = va / na + vb / nb
    diff = mean(a) - mean(b)
    if se2 == 0:
        return {"diff": diff, "t": 0.0, "df": na + nb - 2, "p": 0.0 if diff else 1.0, "cohen_d": 0.0,
                "ci_low": diff, "ci_high": diff}
    t = diff / math.sqrt(se2)
    df = se2 ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    pooled = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    half = t_critical(df, confidence) * math.sqrt(se2)
    return {"diff": diff, "t": t, "df": df, "p": t_two_sided_p(t, df), "cohen_d": diff / pooled if pooled else 0.0,
            "ci_low": diff - half, "ci_high": diff + half}


def anova_two_way(cells: dict[tuple[int, int], Sequence[float]]) -> dict:
    """Balanced two-way ANOVA with interaction. `cells[(i, j)]` = replicates for level i of A and level j of B."""
    a_levels = sorted({i for i, _ in cells})
    b_levels = sorted({j for _, j in cells})
    r = len(next(iter(cells.values())))
    a, b = len(a_levels), len(b_levels)
    grand = mean([x for v in cells.values() for x in v])
    cell_mean = {k: mean(v) for k, v in cells.items()}
    mean_a = {i: mean([cell_mean[(i, j)] for j in b_levels]) for i in a_levels}
    mean_b = {j: mean([cell_mean[(i, j)] for i in a_levels]) for j in b_levels}
    ss_a = b * r * sum((mean_a[i] - grand) ** 2 for i in a_levels)
    ss_b = a * r * sum((mean_b[j] - grand) ** 2 for j in b_levels)
    ss_ab = r * sum((cell_mean[(i, j)] - mean_a[i] - mean_b[j] + grand) ** 2 for i in a_levels for j in b_levels)
    ss_e = sum((x - cell_mean[k]) ** 2 for k, v in cells.items() for x in v)
    df = {"A": a - 1, "B": b - 1, "AB": (a - 1) * (b - 1), "E": a * b * (r - 1)}
    ss = {"A": ss_a, "B": ss_b, "AB": ss_ab, "E": ss_e}
    ms_e = ss_e / df["E"] if df["E"] else 0.0
    rows = []
    for key in ("A", "B", "AB"):
        ms = ss[key] / df[key] if df[key] else 0.0
        f = ms / ms_e if ms_e else 0.0
        rows.append({"source": key, "ss": ss[key], "df": df[key], "ms": ms, "f": f,
                     "p": f_upper_p(f, df[key], df["E"]) if ms_e else 0.0})
    rows.append({"source": "E", "ss": ss_e, "df": df["E"], "ms": ms_e, "f": None, "p": None})
    total = ss_a + ss_b + ss_ab + ss_e
    return {"rows": rows, "eta_squared": {k: (ss[k] / total if total else 0.0) for k in ("A", "B", "AB")}}


def loglog_slope(xs: Sequence[float], ys: Sequence[float]) -> dict:
    """Least-squares fit of log(y) = k * log(x) + c. The slope k is the empirical complexity exponent."""
    pts = [(math.log(x), math.log(y)) for x, y in zip(xs, ys) if x > 0 and y > 0]
    if len(pts) < 2:
        return {"slope": None, "r2": None}
    mx, my = mean([p[0] for p in pts]), mean([p[1] for p in pts])
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    syy = sum((p[1] - my) ** 2 for p in pts)
    if sxx == 0:
        return {"slope": None, "r2": None}
    return {"slope": sxy / sxx, "r2": (sxy * sxy) / (sxx * syy) if syy else 1.0}


# ---- non-parametric ------------------------------------------------------
def _normal_two_sided_p(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2))


def mann_whitney(a: Sequence[float], b: Sequence[float]) -> dict:
    """Two-sided Mann-Whitney U test (normal approximation with tie and continuity corrections).
    `rank_biserial` in [-1, 1] is the effect size: positive means values of `a` tend to be larger."""
    na, nb = len(a), len(b)
    combined = sorted([(x, 0) for x in a] + [(x, 1) for x in b])
    ranks = [0.0] * len(combined)
    tie_term, i = 0.0, 0
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[j + 1][0] == combined[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = avg
        t = j - i + 1
        tie_term += t ** 3 - t
        i = j + 1
    r_a = sum(r for r, (_, g) in zip(ranks, combined) if g == 0)
    u_a = r_a - na * (na + 1) / 2
    u_b = na * nb - u_a
    n = na + nb
    sigma2 = na * nb / 12 * ((n + 1) - tie_term / (n * (n - 1))) if n > 1 else 0.0
    if sigma2 <= 0:
        return {"u": min(u_a, u_b), "z": 0.0, "p": 1.0, "rank_biserial": 0.0}
    z = (abs(u_a - na * nb / 2) - 0.5) / math.sqrt(sigma2)
    return {"u": min(u_a, u_b), "z": z, "p": _normal_two_sided_p(max(z, 0.0)),
            "rank_biserial": (u_a - u_b) / (na * nb)}


def bootstrap_median_diff(a: Sequence[float], b: Sequence[float], *, reps: int = 10_000,
                          confidence: float = 0.95, seed: int = 0) -> tuple[float, float]:
    """Percentile bootstrap CI for median(a) - median(b)."""
    rng = random.Random(seed)
    diffs = sorted(percentile(rng.choices(a, k=len(a)), 50) - percentile(rng.choices(b, k=len(b)), 50)
                   for _ in range(reps))
    tail = (1 - confidence) / 2 * 100
    return percentile(diffs, tail), percentile(diffs, 100 - tail)


# ---- more distributions and tests ------------------------------------------
def gammaq(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x) (chi-square survival function is Q(k/2, x/2))."""
    if x <= 0:
        return 1.0
    if x < a + 1:  # series for P, then complement
        term = total = 1 / a
        n = a
        for _ in range(500):
            n += 1
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-14:
                break
        return max(0.0, 1 - total * math.exp(-x + a * math.log(x) - math.lgamma(a)))
    tiny = 1e-300
    b = x + 1 - a
    c, d = 1 / tiny, 1 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = d if abs(d) > tiny else tiny
        c = b + an / c
        c = c if abs(c) > tiny else tiny
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-14:
            break
    return h * math.exp(-x + a * math.log(x) - math.lgamma(a))


def chi2_upper_p(x: float, df: float) -> float:
    return gammaq(df / 2, x / 2)


def ranks(xs: Sequence[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def skew_kurtosis(xs: Sequence[float]) -> tuple[float, float]:
    """Sample skewness and excess kurtosis (moment estimators)."""
    n, m = len(xs), mean(xs)
    m2 = sum((x - m) ** 2 for x in xs) / n
    if m2 == 0:
        return 0.0, 0.0
    m3 = sum((x - m) ** 3 for x in xs) / n
    m4 = sum((x - m) ** 4 for x in xs) / n
    return m3 / m2 ** 1.5, m4 / m2 ** 2 - 3


def jarque_bera(xs: Sequence[float]) -> dict:
    """Normality test: H0 = the data come from a normal distribution."""
    n = len(xs)
    skew, kurt = skew_kurtosis(xs)
    jb = n / 6 * (skew ** 2 + kurt ** 2 / 4)
    return {"statistic": jb, "p": math.exp(-jb / 2), "skewness": skew, "excess_kurtosis": kurt}


def anova_one_way(groups: Sequence[Sequence[float]]) -> dict:
    allx = [x for g in groups for x in g]
    n, k = len(allx), len(groups)
    grand = mean(allx)
    ssb = sum(len(g) * (mean(g) - grand) ** 2 for g in groups)
    ssw = sum((x - mean(g)) ** 2 for g in groups for x in g)
    dfb, dfw = k - 1, n - k
    msw = ssw / dfw if dfw else 0.0
    f = (ssb / dfb) / msw if msw and dfb else 0.0
    return {"f": f, "df_between": dfb, "df_within": dfw, "p": f_upper_p(f, dfb, dfw) if msw else 0.0,
            "eta_squared": ssb / (ssb + ssw) if ssb + ssw else 0.0}


def levene(groups: Sequence[Sequence[float]]) -> dict:
    """Brown-Forsythe variant of Levene's test (median-centered): H0 = equal variances."""
    dev = [[abs(x - percentile(g, 50)) for x in g] for g in groups]
    r = anova_one_way(dev)
    return {"statistic": r["f"], "df1": r["df_between"], "df2": r["df_within"], "p": r["p"]}


def kruskal_wallis(groups: Sequence[Sequence[float]]) -> dict:
    allx = [x for g in groups for x in g]
    n = len(allx)
    rk = ranks(allx)
    h, pos = 0.0, 0
    for g in groups:
        rs = sum(rk[pos:pos + len(g)])
        h += rs * rs / len(g)
        pos += len(g)
    h = 12 / (n * (n + 1)) * h - 3 * (n + 1)
    counts: dict[float, int] = {}
    for x in allx:
        counts[x] = counts.get(x, 0) + 1
    tie = 1 - sum(t ** 3 - t for t in counts.values()) / (n ** 3 - n) if n > 1 else 1
    h = h / tie if tie else 0.0
    df = len(groups) - 1
    return {"h": h, "df": df, "p": chi2_upper_p(h, df), "epsilon_squared": h / (n - 1) if n > 1 else 0.0}


def correlation(xs: Sequence[float], ys: Sequence[float]) -> dict:
    n = len(xs)
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if n < 3 or sxx == 0 or syy == 0:
        return {"r": None, "p": None, "n": n}
    r = max(-1.0, min(1.0, sxy / math.sqrt(sxx * syy)))
    t = r * math.sqrt((n - 2) / max(1e-300, 1 - r * r))
    return {"r": r, "p": t_two_sided_p(t, n - 2), "n": n}


def spearman(xs: Sequence[float], ys: Sequence[float]) -> dict:
    return correlation(ranks(xs), ranks(ys))


def linear_regression(xs: Sequence[float], ys: Sequence[float]) -> dict:
    n = len(xs)
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if n < 3 or sxx == 0:
        return {"slope": None}
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    icpt = my - slope * mx
    sse = sum((y - icpt - slope * x) ** 2 for x, y in zip(xs, ys))
    sst = sum((y - my) ** 2 for y in ys)
    se = math.sqrt(sse / (n - 2) / sxx) if sse > 0 else 0.0
    t = slope / se if se else 0.0
    return {"slope": slope, "intercept": icpt, "r2": 1 - sse / sst if sst else 1.0, "p": t_two_sided_p(t, n - 2) if se else 0.0, "n": n}


def one_sample_t(xs: Sequence[float], mu0: float, confidence: float = 0.95) -> dict:
    """H0: mean = mu0. `p_less` is the one-sided p for H1: mean < mu0."""
    n, m, s = len(xs), mean(xs), stdev(xs)
    se = s / math.sqrt(n)
    if se == 0:
        return {"t": 0.0, "df": n - 1, "p": 1.0 if m == mu0 else 0.0, "p_less": 0.0 if m < mu0 else 1.0, "mean": m}
    t = (m - mu0) / se
    p = t_two_sided_p(t, n - 1)
    return {"t": t, "df": n - 1, "p": p, "p_less": p / 2 if t < 0 else 1 - p / 2, "mean": m,
            "ci_low": m - t_critical(n - 1, confidence) * se, "ci_high": m + t_critical(n - 1, confidence) * se}


def wilson_interval(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)
