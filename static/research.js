"use strict";
// Admin modules: "Experimentos" (experimental design) and "Rendimiento y calidad" (performance + ISO/IEC 25010).

const num = (v, d = 4) => (v === null || v === undefined ? "—" : Number(v).toLocaleString("es", { maximumFractionDigits: d, minimumFractionDigits: 0 }));
const secs = (v) => (v === null || v === undefined ? "—" : Number(v) >= 1 ? Number(v).toFixed(2) : Number(v) === 0 ? "0" : Number(v).toPrecision(3));
const pval = (p) => (p === null || p === undefined ? "—" : p < 0.001 ? "< 0,001" : Number(p).toFixed(3).replace(".", ","));
const eng = (e) => `<span class="pill ${e === "v1" ? "off" : ""}">${esc(e.toUpperCase())}</span>`;

function toCSV(rows) {
  if (!rows.length) return "";
  const cols = Object.keys(rows[0]);
  const cell = (v) => { const s = v === null || v === undefined ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  return [cols.join(","), ...rows.map((r) => cols.map((c) => cell(r[c])).join(","))].join("\n");
}
function download(name, text, type = "text/csv") {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: type + ";charset=utf-8" }));
  a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
const stamp = () => new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
function table(head, rows, cls = "") {
  return `<div class="table-wrap"><table class="${cls}"><thead><tr>${head.map((h) => `<th${h.startsWith("#") ? ' class="num"' : ""}>${esc(h.replace(/^#/, ""))}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c, i) => `<td${head[i].startsWith("#") ? ' class="num"' : ""}>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
function field(label, name, value, attrs = "", hint = "") {
  return `<label>${esc(label)}<input name="${name}" value="${esc(value)}" ${attrs}>${hint ? `<small class="muted">${esc(hint)}</small>` : ""}</label>`;
}

// ---------------------------------------------------------------- Experimentos
const SAVED_KEY = "last_experiment";
let lastExperiment = (() => { try { return JSON.parse(localStorage.getItem(SAVED_KEY)); } catch { return null; } })();
function saveExperiment() { try { localStorage.setItem(SAVED_KEY, JSON.stringify(lastExperiment)); } catch {} } // lets /reportes reuse it after a reload

async function viewExperiments() {
  $("#app").innerHTML = `<div class="page-head"><div><h1>Diseño de pruebas experimentales</h1>
    <p class="muted">Experimento controlado V1 vs V2: factorial, corridas aleatorizadas, calentamiento descartado, Mann-Whitney e IC por remuestreo. Se ejecuta en memoria: no crea pedidos ni toca el stock.</p></div></div>
    <form class="card pad stack" id="xf" novalidate>
      <h2>Parámetros</h2>
      <div class="form-grid3">
        ${field("Tamaños de pedido (líneas)", "sizes", "10, 100, 500, 1500", "", "Separados por coma. Moderadora.")}
        ${field("Corridas medidas por celda", "replicates", 30, 'type="number" min="3" max="200"', "n por condición y tamaño")}
        ${field("Corridas de calentamiento", "warmup", 5, 'type="number" min="0" max="20"', "Se descartan y se reportan")}
        ${field("Intensidad de V1", "work_factor", 1, 'type="number" min="1" max="200"', "Trabajo inútil fijo (sin auto-calibrar)")}
        ${field("Productos en el catálogo", "catalog_size", 200, 'type="number" min="1" max="5000"', "Variable de control")}
        ${field("Semilla", "seed", 2026, 'type="number" min="0"', "Reproduce pedidos y orden de corridas")}
        ${field("Nivel de significancia α", "alpha", 0.05, 'type="number" step="0.01" min="0.001" max="0.2"')}
        ${field("Umbral de aceptación p95 (s)", "threshold", 20, 'type="number" step="0.5" min="0.1"', "Declarado antes de medir")}
        ${field("Réplicas del bootstrap", "bootstrap_reps", 10000, 'type="number" min="200" max="50000"')}
      </div>
      <p class="error" id="xf-error" role="alert"></p>
      <div><button class="btn primary" type="submit" id="xf-run">Ejecutar experimento</button> <span class="muted" id="xf-status"></span></div>
    </form><div id="xres"></div>`;
  $("#xf").onsubmit = async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target));
    const body = { sizes: f.sizes.split(/[,\s]+/).filter(Boolean).map(Number), replicates: +f.replicates, warmup: +f.warmup, work_factor: +f.work_factor,
      catalog_size: +f.catalog_size, seed: +f.seed, alpha: +f.alpha, threshold: +f.threshold, bootstrap_reps: +f.bootstrap_reps };
    const btn = $("#xf-run"); btn.disabled = true; $("#xf-error").textContent = ""; $("#xf-status").textContent = "Ejecutando… puede tardar según los tamaños elegidos.";
    try { lastExperiment = await api("/admin/experiments/run", { method: "POST", body }); saveExperiment(); drawExperiment(lastExperiment); $("#xf-status").textContent = "Listo."; }
    catch (err) { $("#xf-error").textContent = err.message; $("#xf-status").textContent = ""; }
    btn.disabled = false;
  };
  if (lastExperiment) drawExperiment(lastExperiment);
}

function drawExperiment(r) {
  const d = r.design, c = r.conclusion, env = r.environment;
  const cellRows = r.cells.map((x) => [eng(x.engine), "#" + x.lines, x.n, secs(x.median), secs(x.p95), secs(x.p99), secs(x.mean), secs(x.sd),
    `[${secs(x.ci_low)} ; ${secs(x.ci_high)}]`, secs(x.cpu_mean), num(x.peak_memory_kb, 0), x.meets_threshold ? "✔" : "✘"]);
  const cmpRows = r.comparisons.map((x) => [x.lines, secs(x.median_v1), secs(x.median_v2), secs(x.delta_median), `[${secs(x.ci_low)} ; ${secs(x.ci_high)}]`,
    pval(x.p), num(x.reduction_pct, 1) + " %", num(x.speedup, 1) + "×", num(x.rank_biserial, 2), x.same_total ? "idénticos" : "<strong>DIFIEREN</strong>"]);
  $("#xres").innerHTML = `
    <div class="card pad" style="margin-top:16px"><h2>Diseño experimental</h2>
      <div class="receipt-row"><span>Diseño</span><strong>${esc(d.type)}</strong></div>
      <div class="receipt-row"><span>Variable respuesta</span><strong>${esc(d.response)}</strong></div>
      <div class="receipt-row"><span>Factores</span><strong>${d.factors.map((f) => esc(f.name) + ": " + f.levels.map(esc).join(", ")).join(" · ")}</strong></div>
      <div class="receipt-row"><span>Variables de control</span><strong>${d.controlled.map(esc).join("; ")}</strong></div>
      <div class="receipt-row"><span>Aleatorización</span><strong>${esc(d.randomization)}</strong></div>
      <div class="receipt-row"><span>Calentamiento</span><strong>${esc(d.warmup)}</strong></div>
      <div class="receipt-row"><span>Análisis</span><strong>${esc(d.analysis)}</strong></div>
      <div class="receipt-row"><span>H0</span><strong>${esc(d.h0)}</strong></div>
      <div class="receipt-row"><span>H1</span><strong>${esc(d.h1)}</strong></div></div>
    <div class="card pad" style="margin-top:16px"><h2>Entorno de medición</h2>
      <p class="muted">Declararlo en el artículo: ${esc(env.system)} (${esc(env.machine)}) · ${env.cpu_count} núcleos${env.memory_gb ? " · " + env.memory_gb + " GB" : ""} · ${esc(env.implementation)} ${esc(env.python)} ·
        base ${esc(env.database || "—")} · ${env.serverless ? "serverless" : "local"} · commit ${esc((env.commit || "no disponible").slice(0, 10))} · ${esc(env.timestamp)}</p></div>
    <div class="card pad" style="margin-top:16px"><h2>Conclusión automática</h2>
      <div class="receipt-row"><span>¿Se rechaza H0 en todos los tamaños (p &lt; ${d.alpha})?</span><strong>${c.all_reject_h0 ? "Sí" : "No"}</strong></div>
      <div class="receipt-row"><span>V2 cumple p95 ≤ ${d.threshold} s en todos los tamaños</span><strong>${c.v2_meets_threshold ? "Sí" : "No"}</strong></div>
      <div class="receipt-row"><span>V1 cumple p95 ≤ ${d.threshold} s en todos los tamaños</span><strong>${c.v1_meets_threshold ? "Sí" : "No"}</strong></div>
      <div class="receipt-row"><span>Salidas de V1 y V2 idénticas</span><strong>${c.outputs_identical ? "Sí" : "No"}</strong></div>
      <p class="muted" style="margin-top:8px">La significancia se reporta junto al tamaño del efecto; el criterio de cumplimiento es el cruce del umbral, no el valor p.</p></div>
    <div class="card pad" style="margin-top:16px"><h2>Tabla de resultados por condición (s)</h2>
      ${table(["Motor", "#Líneas", "#n", "#Mediana", "#p95", "#p99", "#Media", "#Desv.", "#IC media", "#CPU medio", "#Pico mem. (KB)", "p95 ≤ umbral"], cellRows)}</div>
    <div class="card pad" style="margin-top:16px"><h2>Comparación V1 → V2 por tamaño (Mann-Whitney)</h2>
      ${table(["#Líneas", "#Mediana V1", "#Mediana V2", "#Δ mediana (s)", "#IC Δ (bootstrap)", "#p", "#Reducción", "#Aceleración", "#r (rank-biserial)", "Totales"], cmpRows)}</div>
    ${r.anova ? `<div class="card pad" style="margin-top:16px"><h2>ANOVA factorial (${esc(r.anova.response)})</h2>
      ${table(["Fuente", "#SC", "#gl", "#CM", "#F", "#p", "#η²"], r.anova.rows.map((x) => [esc(r.anova.factors[x.source]), num(x.ss, 4), x.df, num(x.ms, 4), num(x.f, 2), pval(x.p), x.source === "E" ? "—" : num(r.anova.eta_squared[x.source], 3)]))}
      <p class="muted">Complementario: la interacción Motor × Líneas indica si la ventaja de V2 crece con el tamaño del pedido.</p></div>` : ""}
    <div class="card pad" style="margin-top:16px"><h2>Datos para el artículo</h2>
      <p class="muted">Los datos crudos (una fila por corrida) permiten recalcular cualquier estadístico sin repetir el experimento.</p>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn" data-dl="runs">Corridas (CSV)</button><button class="btn" data-dl="warmup">Calentamiento (CSV)</button>
        <button class="btn" data-dl="cells">Resultados por condición (CSV)</button><button class="btn" data-dl="cmp">Comparaciones (CSV)</button>
        <button class="btn" data-dl="json">Todo (JSON)</button></div></div>`;
  $("#xres").onclick = (e) => {
    const b = e.target.closest("[data-dl]"); if (!b) return;
    const k = b.dataset.dl, n = "experimento-" + stamp();
    if (k === "runs") download(n + "-corridas.csv", toCSV(r.runs));
    else if (k === "warmup") download(n + "-calentamiento.csv", toCSV(r.warmup));
    else if (k === "cells") download(n + "-condiciones.csv", toCSV(r.cells));
    else if (k === "cmp") download(n + "-comparaciones.csv", toCSV(r.comparisons));
    else download(n + ".json", JSON.stringify(r, null, 2), "application/json");
  };
}

// ---------------------------------------------------------------- Rendimiento y calidad
let lastBenchmark = null, lastQuality = null;

async function viewPerformance() {
  const tab = (location.hash.split("?")[1] || "").replace("tab=", "") || "rendimiento";
  $("#app").innerHTML = `<div class="page-head"><div><h1>Rendimiento y calidad</h1>
    <p class="muted">Evaluación del rendimiento y de la calidad del software según ISO/IEC 25010.</p></div></div>
    <div class="tabs"><a href="#/rendimiento" class="${tab === "rendimiento" ? "on" : ""}">Rendimiento</a><a href="#/rendimiento?tab=calidad" class="${tab === "calidad" ? "on" : ""}">Calidad</a></div>
    <div id="box" class="muted">Cargando…</div>`;
  if (tab === "calidad") return drawQuality();
  const real = await api("/admin/performance/orders");
  $("#box").className = "";
  $("#box").innerHTML = `
    <div class="card pad"><h2>Latencia real de la tienda (pedidos registrados)</h2>
      <p class="muted">Distribución del tiempo de generación de los recibos que ya se emitieron. Es asimétrica: se reportan mediana, p95 y p99.</p>
      ${real.length ? table(["Motor", "#Pedidos", "#Mediana", "#p90", "#p95", "#p99", "#Mín.", "#Máx.", "#Media", "#Desv."],
        real.map((x) => [eng(x.engine), x.n, secs(x.p50), secs(x.p90), secs(x.p95), secs(x.p99), secs(x.min), secs(x.max), secs(x.mean), secs(x.sd)])) : '<div class="empty">Todavía no hay pedidos.</div>'}
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px">
        <button class="btn" id="dl-orders">Pedidos reales (CSV, datos crudos)</button>
        ${real.length ? '<button class="btn" id="dl-real">Estadísticos (CSV)</button>' : ""}</div></div>
    <form class="card pad stack" id="bf" style="margin-top:16px" novalidate><h2>Prueba de escalado y rendimiento (benchmark)</h2>
      <p class="muted">Mide tiempo y recibos por segundo al crecer el pedido, y estima el exponente de complejidad empírica (pendiente log-log: ≈1 lineal, ≈2 cuadrático).</p>
      <div class="form-grid3">${field("Tamaños (líneas)", "sizes", "10, 50, 100, 250, 500")}${field("Repeticiones", "repetitions", 10, 'type="number" min="1" max="100"')}
        ${field("Intensidad de V1", "v1_work_factor", 1, 'type="number" min="1" max="200"')}${field("Productos en el catálogo", "catalog_size", 200, 'type="number" min="1" max="5000"')}</div>
      <p class="error" id="bf-error" role="alert"></p><div><button class="btn primary" type="submit" id="bf-run">Ejecutar benchmark</button></div></form>
    <div id="bres"></div>`;
  $("#dl-orders").onclick = async () => {
    const orders = await api("/admin/orders?limit=500");
    download("pedidos-" + stamp() + ".csv", toCSV(orders.map((o) => ({ numero: o.number, fecha: o.created_at, motor: o.engine, lineas: o.items.length, unidades: o.item_count, segundos: o.processing_seconds, total: o.total }))));
  };
  if (real.length) $("#dl-real").onclick = () => download("latencia-real-" + stamp() + ".csv", toCSV(real));
  $("#bf").onsubmit = async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target)); const btn = $("#bf-run"); btn.disabled = true; $("#bf-error").textContent = "";
    try { lastBenchmark = await api("/admin/performance/benchmark", { method: "POST", body: { sizes: f.sizes.split(/[,\s]+/).filter(Boolean).map(Number), repetitions: +f.repetitions, v1_work_factor: +f.v1_work_factor, catalog_size: +f.catalog_size } }); drawBenchmark(); }
    catch (err) { $("#bf-error").textContent = err.message; }
    btn.disabled = false;
  };
  if (lastBenchmark) drawBenchmark();
}

function drawBenchmark() {
  const b = lastBenchmark, cx = b.complexity;
  const label = (c) => c.slope === null ? "—" : `${num(c.slope, 2)} (R² ${num(c.r2, 3)})`;
  $("#bres").innerHTML = `<div class="card pad" style="margin-top:16px"><h2>Resultado del benchmark</h2>
    ${table(["#Líneas", "#V1 media (s)", "#V1 p95 (s)", "#V1 recibos/s", "#V2 media (s)", "#V2 p95 (s)", "#V2 recibos/s", "#Aceleración"],
      b.points.map((p) => [p.lines, secs(p.v1.mean), secs(p.v1.p95), num(p.v1.throughput, 2), secs(p.v2.mean), secs(p.v2.p95), num(p.v2.throughput, 0), num(p.speedup, 1) + "×"]))}
    <div class="receipt-row"><span>Exponente de complejidad empírica V1</span><strong>${label(cx.v1)}</strong></div>
    <div class="receipt-row"><span>Exponente de complejidad empírica V2</span><strong>${label(cx.v2)}</strong></div>
    <div style="margin-top:12px"><button class="btn" id="dl-bench">Benchmark (CSV)</button></div></div>`;
  $("#dl-bench").onclick = () => download("benchmark-" + stamp() + ".csv", toCSV(b.points.map((p) => ({ lineas: p.lines,
    v1_media: p.v1.mean, v1_p50: p.v1.p50, v1_p95: p.v1.p95, v1_max: p.v1.max, v1_recibos_s: p.v1.throughput,
    v2_media: p.v2.mean, v2_p50: p.v2.p50, v2_p95: p.v2.p95, v2_max: p.v2.max, v2_recibos_s: p.v2.throughput, aceleracion: p.speedup }))));
}

async function drawQuality() {
  lastQuality = lastQuality || await api("/admin/quality?cases=100");
  const q = lastQuality, e = q.equivalence, m = q.maintainability, t = q.tests;
  const mrow = (k, name) => { const x = m[k]; return x ? [name, esc(x.file), x.code_lines, x.functions, x.total_complexity, num(x.avg_complexity, 2), x.max_complexity, x.max_nesting] : [name, "no disponible", "—", "—", "—", "—", "—", "—"]; };
  $("#box").className = "";
  $("#box").innerHTML = `
    <div class="card pad"><h2>Corrección funcional</h2>
      <div class="receipt-row"><span>Pedidos aleatorios comparados (V1 vs V2)</span><strong>${e.cases}</strong></div>
      <div class="receipt-row"><span>Coinciden (líneas, subtotal, IVA y total)</span><strong>${e.passed} (${num(e.agreement_pct, 1)} %)</strong></div>
      <div class="receipt-row"><span>Aritmética monetaria exacta (subtotal + IVA = total)</span><strong>${e.decimal_exact ? "Sí" : "No"}</strong></div>
      ${e.failed ? `<p class="error">Se encontraron diferencias: ${esc(JSON.stringify(e.failures))}</p>` : ""}</div>
    <div class="card pad" style="margin-top:16px"><h2>Mantenibilidad: métricas estáticas</h2>
      <p class="muted">Complejidad ciclomática (McCabe) y anidamiento por archivo. Útil para declarar si la optimización cambió el costo de mantener el código.</p>
      ${table(["Motor", "Archivo", "#Líneas de código", "#Funciones", "#Complej. total", "#Complej. media", "#Complej. máx.", "#Anidamiento máx."],
        [mrow("v1", "V1 heredado"), mrow("v2", "V2 optimizado"), mrow("base", "Base común")])}
      <div style="margin-top:12px"><button class="btn" id="dl-q">Métricas (CSV)</button></div></div>
    <div class="card pad" style="margin-top:16px"><h2>Pruebas automáticas</h2>
      <p class="muted">${t.total} pruebas en ${t.files.length} archivos. Flujos de CI: ${t.ci_workflows.map(esc).join(", ") || "ninguno"}.</p>
      ${table(["Archivo", "#Pruebas"], t.files.map((f) => [esc(f.file), f.tests]))}</div>
    <div class="card pad" style="margin-top:16px"><h2>Características de calidad (ISO/IEC 25010)</h2>
      <p class="muted">Declarar qué se evaluó y qué quedó fuera delimita lo que el resultado permite afirmar.</p>
      ${table(["Característica", "Subcaracterística", "Estado", "Evidencia"], q.characteristics.map((c) => [esc(c.characteristic), esc(c.sub),
        `<span class="pill ${c.status === "medido" ? "" : "off"}">${esc(c.status)}</span>`, esc(c.evidence)]))}
      <div style="margin-top:12px"><button class="btn" id="dl-iso">Tabla ISO 25010 (CSV)</button></div></div>`;
  $("#dl-q").onclick = () => download("mantenibilidad-" + stamp() + ".csv", toCSV(Object.entries(m).filter(([, x]) => x).map(([k, x]) => ({ motor: k, archivo: x.file, lineas_codigo: x.code_lines,
    funciones: x.functions, complejidad_total: x.total_complexity, complejidad_media: x.avg_complexity, complejidad_max: x.max_complexity, anidamiento_max: x.max_nesting }))));
  $("#dl-iso").onclick = () => download("iso25010-" + stamp() + ".csv", toCSV(q.characteristics));
}

// ---------------------------------------------------------------- Estadística
let lastStats = null;

async function viewStatistics() {
  const hasExp = !!lastExperiment;
  $("#app").innerHTML = `<div class="page-head"><div><h1>Pruebas estadísticas</h1>
    <p class="muted">Contrastes de hipótesis aplicados a las mediciones del proyecto: supuestos, comparación V1 vs V2, relación tamaño-tiempo y umbral de aceptación.</p></div></div>
    <form class="card pad stack" id="sf" novalidate><h2>Datos y parámetros</h2>
      <div class="form-grid3">
        <label>Fuente de datos<select name="source"><option value="orders">Pedidos reales de la tienda</option>
          <option value="samples" ${hasExp ? "" : "disabled"}>Corridas del último experimento${hasExp ? "" : " (ejecuta uno primero)"}</option></select>
          <small class="muted">Con pedidos reales, V1 y V2 deben tener compras registradas.</small></label>
        ${field("Nivel de significancia α", "alpha", 0.05, 'type="number" step="0.01" min="0.001" max="0.2"')}
        ${field("Umbral de aceptación (s)", "threshold", 20, 'type="number" step="0.5" min="0.1"', "Estándar operativo")}
      </div><p class="error" id="sf-error" role="alert"></p>
      <div><button class="btn primary" type="submit" id="sf-run">Calcular pruebas</button></div></form><div id="sres"></div>`;
  $("#sf").onsubmit = async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target)); const btn = $("#sf-run"); btn.disabled = true; $("#sf-error").textContent = "";
    const body = { source: f.source, alpha: +f.alpha, threshold: +f.threshold };
    if (f.source === "samples") body.samples = lastExperiment.runs.map((r) => ({ engine: r.engine, lines: r.lines, seconds: r.seconds }));
    try { lastStats = await api("/admin/statistics/analyze", { method: "POST", body }); drawStatistics(lastStats); }
    catch (err) { $("#sf-error").textContent = err.message; }
    btn.disabled = false;
  };
  if (lastStats) drawStatistics(lastStats);
}

function drawStatistics(s) {
  const c = s.comparison, ok = (b) => (b ? "✔" : "✘");
  const rec = c ? (c.recommended === "welch" ? "Welch (se cumplen normalidad y homogeneidad)" : "Mann-Whitney (no se cumplen los supuestos paramétricos)") : "";
  $("#sres").innerHTML = `
    <div class="card pad" style="margin-top:16px"><h2>Descriptiva (s)</h2><p class="muted">Fuente: ${esc(s.source)} · ${s.n_total} observaciones · α = ${s.alpha}</p>
      ${table(["Motor", "#n", "#Mediana", "#p90", "#p95", "#p99", "#Media", "#Desv.", "#IC media", "#Mín.", "#Máx."],
        s.descriptive.map((x) => [eng(x.engine), x.n, secs(x.median), secs(x.p90), secs(x.p95), secs(x.p99), secs(x.mean), secs(x.sd), `[${secs(x.ci_low)} ; ${secs(x.ci_high)}]`, secs(x.min), secs(x.max)]))}</div>
    <div class="card pad" style="margin-top:16px"><h2>1. Supuestos</h2>
      <p class="muted">Normalidad (Jarque-Bera, H0: los datos son normales) y homogeneidad de varianzas (Levene/Brown-Forsythe, H0: varianzas iguales).</p>
      ${table(["Motor", "#n", "#Asimetría", "#Curtosis exc.", "#JB", "#p", "Normal", "Decisión"],
        s.normality.map((x) => [eng(x.engine), x.n, num(x.skewness, 2), num(x.excess_kurtosis, 2), num(x.statistic, 2), pval(x.p), ok(x.normal), esc(x.decision)]))}
      ${s.variance ? `<div class="receipt-row"><span>Levene: F = ${num(s.variance.statistic, 3)} (${s.variance.df1}, ${s.variance.df2}) · p = ${pval(s.variance.p)}</span><strong>${esc(s.variance.decision)}</strong></div>` : '<p class="muted">Levene requiere observaciones de V1 y V2.</p>'}</div>
    ${c ? `<div class="card pad" style="margin-top:16px"><h2>2. Comparación V1 vs V2</h2>
      <p class="muted">H0: no hay diferencia en el tiempo de generación. Prueba recomendada según los supuestos: <strong>${esc(rec)}</strong>.</p>
      ${table(["Prueba", "#Estadístico", "#gl", "#p", "#Tamaño del efecto", "Decisión"], [
        ["Mann-Whitney U", num(c.mann_whitney.u, 1), "—", pval(c.mann_whitney.p), "r = " + num(c.mann_whitney.rank_biserial, 3), esc(c.decision)],
        ["Welch t", num(c.welch.t, 3), num(c.welch.df, 1), pval(c.welch.p), "d = " + num(c.welch.cohen_d, 2), esc(c.welch_decision)],
        ["ANOVA de un factor", "F = " + num(c.anova.f, 2), `${c.anova.df_between}, ${c.anova.df_within}`, pval(c.anova.p), "η² = " + num(c.anova.eta_squared, 3), "Equivale a Welch con varianzas iguales"],
        ["Kruskal-Wallis", "H = " + num(c.kruskal_wallis.h, 2), c.kruskal_wallis.df, pval(c.kruskal_wallis.p), "ε² = " + num(c.kruskal_wallis.epsilon_squared, 3), "Equivale a Mann-Whitney para 2 grupos"]])}
      <div class="receipt-row"><span>Δ mediana (V1 − V2)</span><strong>${secs(c.delta_median)} s · IC [${secs(c.ci_low)} ; ${secs(c.ci_high)}] · reducción ${num(c.reduction_pct, 1)} %</strong></div></div>` : ""}
    <div class="card pad" style="margin-top:16px"><h2>3. Tamaño del pedido y tiempo</h2>
      <p class="muted">Correlación (Spearman, Pearson) y regresión lineal tiempo ~ líneas. Requiere pedidos de distinto tamaño.</p>
      ${table(["Motor", "#n", "#Tamaños", "#ρ Spearman", "#p", "#r Pearson", "#Pendiente (s/línea)", "#R²", "Decisión"],
        s.correlation.map((x) => [eng(x.engine), x.n, x.distinct_sizes, num(x.spearman.r, 3), pval(x.spearman.p), num(x.pearson.r, 3),
          x.regression.slope === null ? "—" : num(x.regression.slope, 6), num(x.regression.r2, 3), esc(x.decision)]))}</div>
    <div class="card pad" style="margin-top:16px"><h2>4. Cumplimiento del umbral (${s.threshold} s)</h2>
      <p class="muted">H0: la media ≥ umbral; H1: la media &lt; umbral (t de una muestra, unilateral). Se reporta además p95 y la proporción de recibos dentro del umbral con IC de Wilson.</p>
      ${table(["Motor", "#n", "#Dentro del umbral", "#Proporción", "#IC Wilson 95 %", "#p95", "p95 ≤ umbral", "#p (unilateral)", "Decisión"],
        s.threshold_tests.map((x) => [eng(x.engine), x.n, x.within, num(x.proportion * 100, 1) + " %", `[${num(x.wilson_low * 100, 1)} ; ${num(x.wilson_high * 100, 1)}] %`,
          secs(x.p95), ok(x.meets_p95), pval(x.p_less), esc(x.decision)]))}
      <p class="muted">El criterio de cumplimiento es el cruce del umbral en p95; el valor p no lo sustituye.</p></div>
    <div class="card pad" style="margin-top:16px"><h2>Descargar</h2><div style="display:flex;gap:10px;flex-wrap:wrap">
      <button class="btn" data-sdl="desc">Descriptiva (CSV)</button><button class="btn" data-sdl="tests">Pruebas (CSV)</button><button class="btn" data-sdl="json">Todo (JSON)</button></div></div>`;
  $("#sres").onclick = (e) => {
    const b = e.target.closest("[data-sdl]"); if (!b) return; const n = "estadistica-" + stamp();
    if (b.dataset.sdl === "desc") download(n + "-descriptiva.csv", toCSV(s.descriptive));
    else if (b.dataset.sdl === "json") download(n + ".json", JSON.stringify(s, null, 2), "application/json");
    else {
      const rows = s.normality.map((x) => ({ prueba: "Jarque-Bera", grupo: x.engine, estadistico: x.statistic, gl: "", p: x.p, decision: x.decision }));
      if (s.variance) rows.push({ prueba: "Levene", grupo: "v1 vs v2", estadistico: s.variance.statistic, gl: `${s.variance.df1},${s.variance.df2}`, p: s.variance.p, decision: s.variance.decision });
      if (c) rows.push({ prueba: "Mann-Whitney", grupo: "v1 vs v2", estadistico: c.mann_whitney.u, gl: "", p: c.mann_whitney.p, decision: c.decision },
        { prueba: "Welch", grupo: "v1 vs v2", estadistico: c.welch.t, gl: c.welch.df, p: c.welch.p, decision: c.welch_decision },
        { prueba: "ANOVA", grupo: "v1 vs v2", estadistico: c.anova.f, gl: `${c.anova.df_between},${c.anova.df_within}`, p: c.anova.p, decision: "" },
        { prueba: "Kruskal-Wallis", grupo: "v1 vs v2", estadistico: c.kruskal_wallis.h, gl: c.kruskal_wallis.df, p: c.kruskal_wallis.p, decision: "" });
      s.correlation.forEach((x) => rows.push({ prueba: "Spearman", grupo: x.engine, estadistico: x.spearman.r, gl: "", p: x.spearman.p, decision: x.decision }));
      s.threshold_tests.forEach((x) => rows.push({ prueba: "t una muestra (media < umbral)", grupo: x.engine, estadistico: x.t, gl: "", p: x.p_less, decision: x.decision }));
      download(n + "-pruebas.csv", toCSV(rows));
    }
  };
}
