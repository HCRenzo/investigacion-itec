"use strict";
// Admin module "Reportes": charts comparing receipt engine V1 vs V2 (inline SVG, no libraries).
// Palette: categorical slots 1 (blue = V1) and 2 (orange = V2), validated light and dark with the dataviz validator.

const THEMES = {
  light: { surface: "#fcfcfb", ink: "#0b0b0b", ink2: "#52514e", muted: "#6f6e69", grid: "#e6e5e1", v1: "#2a78d6", v2: "#eb6834" },
  dark: { surface: "#1a1a19", ink: "#f0efec", ink2: "#c3c2b7", muted: "#9a9990", grid: "#302f2d", v1: "#3987e5", v2: "#d95926" },
};
const isDark = () => { const f = document.documentElement.dataset.theme; return f ? f === "dark" : matchMedia("(prefers-color-scheme: dark)").matches; };
const ENGINE_NAME = { v1: "V1 (heredado)", v2: "V2 (optimizado)" };
const W = 680, H = 340;

function fmtTime(v) {
  if (v === null || v === undefined || !isFinite(v)) return "—";
  if (v >= 1) return (+v.toPrecision(3)).toLocaleString("es") + " s";
  if (v >= 1e-3) return (+(v * 1e3).toPrecision(3)).toLocaleString("es") + " ms";
  return (+(v * 1e6).toPrecision(3)).toLocaleString("es") + " µs";
}
const fmtX = (v) => (+Number(v).toPrecision(3)).toLocaleString("es");

// ---- primitives -----------------------------------------------------------
function frame(t, legend, w = W, h = H) {
  const items = legend.map((l, i) => `<g transform="translate(${64 + i * 170},16)"><${l.shape === "diamond" ? `rect x="-1" y="-5" width="10" height="10" transform="rotate(45 4 0)"` : `circle cx="4" cy="0" r="5"`} fill="${l.color}"/><text x="18" y="4" fill="${t.ink2}" font-size="12">${esc(l.label)}</text></g>`).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" font-family="Inter, system-ui, sans-serif" role="img">
    <rect width="${w}" height="${h}" fill="${t.surface}"/>${items}`;
}
function logScale(values, top, height, extra = []) {
  const all = [...values, ...extra].filter((v) => v > 0);
  const lo = Math.floor(Math.log10(Math.min(...all))), hi = Math.max(lo + 1, Math.ceil(Math.log10(Math.max(...all))));
  const step = Math.ceil((hi - lo) / 6);
  const ticks = []; for (let e = lo; e <= hi; e += step) ticks.push(e);
  return { y: (v) => top + (1 - (Math.log10(Math.max(v, 10 ** lo)) - lo) / (hi - lo)) * height, ticks: ticks.map((e) => ({ v: 10 ** e, e })), lo, hi };
}
function niceMax(v) { const p = 10 ** Math.floor(Math.log10(v)); const n = v / p; return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p; }
function marker(shape, x, y, color, t, r = 4.5) {
  return shape === "diamond"
    ? `<rect x="${x - r}" y="${y - r}" width="${2 * r}" height="${2 * r}" transform="rotate(45 ${x} ${y})" fill="${color}" stroke="${t.surface}" stroke-width="2"/>`
    : `<circle cx="${x}" cy="${y}" r="${r}" fill="${color}" stroke="${t.surface}" stroke-width="2"/>`;
}
const SHAPE = { v1: "circle", v2: "diamond" };

// ---- chart builders: each returns { svg(theme), points, table } -----------------
function lineChart({ cats, series, threshold, xTitle, yTitle = "Tiempo (escala logarítmica)" }) {
  const m = { l: 68, r: 64, t: 38, b: 52 }, pw = W - m.l - m.r, ph = H - m.t - m.b;
  const sc = logScale(series.flatMap((s) => s.values), m.t, ph, threshold ? [threshold.value] : []);
  const x = (i) => m.l + (cats.length === 1 ? pw / 2 : (i / (cats.length - 1)) * pw);
  const points = series.flatMap((s) => s.values.map((v, i) => v == null ? null : { x: x(i), y: sc.y(v), value: fmtTime(v), label: `${s.name} · ${cats[i]}`, color: s.color })).filter(Boolean);
  const svg = (t) => {
    const grid = sc.ticks.map((k) => `<line x1="${m.l}" x2="${W - m.r}" y1="${sc.y(k.v)}" y2="${sc.y(k.v)}" stroke="${t.grid}"/><text x="${m.l - 8}" y="${sc.y(k.v) + 4}" text-anchor="end" fill="${t.muted}" font-size="11">${fmtTime(k.v)}</text>`).join("");
    const xs = cats.map((c, i) => `<text x="${x(i)}" y="${H - m.b + 20}" text-anchor="middle" fill="${t.muted}" font-size="11">${esc(c)}</text>`).join("");
    const thr = threshold ? `<line x1="${m.l}" x2="${W - m.r}" y1="${sc.y(threshold.value)}" y2="${sc.y(threshold.value)}" stroke="${t.ink2}" stroke-width="1.5"/><text x="${m.l + 6}" y="${sc.y(threshold.value) - 6}" fill="${t.ink2}" font-size="11">${esc(threshold.label)}</text>` : "";
    const lines = series.map((s) => {
      const c = t[s.key], pts = s.values.map((v, i) => v == null ? null : [x(i), sc.y(v)]).filter(Boolean);
      const last = pts[pts.length - 1];
      return `<path d="M${pts.map((p) => p.join(",")).join(" L")}" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>${pts.map((p) => marker(SHAPE[s.key], p[0], p[1], c, t)).join("")}
        ${last ? `<text x="${last[0] + 12}" y="${last[1] + 4}" fill="${t.ink2}" font-size="11">${s.key.toUpperCase()}</text>` : ""}`;
    }).join("");
    return frame(t, series.map((s) => ({ label: s.name, color: t[s.key], shape: SHAPE[s.key] }))) +
      `<text x="14" y="${m.t + ph / 2}" transform="rotate(-90 14 ${m.t + ph / 2})" text-anchor="middle" fill="${t.muted}" font-size="11">${esc(yTitle)}</text>
       ${grid}${thr}${lines}<text x="${m.l + pw / 2}" y="${H - 8}" text-anchor="middle" fill="${t.muted}" font-size="11">${esc(xTitle)}</text></svg>`;
  };
  const table = { head: ["Categoría", ...series.map((s) => s.name + " (s)")], rows: cats.map((c, i) => [esc(c), ...series.map((s) => s.values[i] == null ? "—" : String(s.values[i]))]) };
  return { svg, points: points.map((p) => ({ ...p })), table, series };
}

function barChart({ cats, values, key, xTitle, yTitle, fmt, name }) {
  const m = { l: 68, r: 24, t: 38, b: 52 }, pw = W - m.l - m.r, ph = H - m.t - m.b, top = niceMax(Math.max(...values, 1));
  const y = (v) => m.t + (1 - v / top) * ph, band = pw / cats.length, bw = Math.min(24, band * 0.5);
  const cx = (i) => m.l + band * (i + 0.5);
  const points = values.map((v, i) => ({ x: cx(i), y: y(v), value: fmt(v), label: `${name} · ${cats[i]}` }));
  const svg = (t) => {
    const grid = [0, 1, 2, 3, 4].map((i) => { const v = top * i / 4; return `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="${t.grid}"/><text x="${m.l - 8}" y="${y(v) + 4}" text-anchor="end" fill="${t.muted}" font-size="11">${fmtX(v)}</text>`; }).join("");
    const bars = values.map((v, i) => { const h = ph * v / top, r = Math.min(4, h), x0 = cx(i) - bw / 2, y0 = y(v);
      return `<path d="M${x0},${y0 + h} V${y0 + r} Q${x0},${y0} ${x0 + r},${y0} H${x0 + bw - r} Q${x0 + bw},${y0} ${x0 + bw},${y0 + r} V${y0 + h} Z" fill="${t[key]}"/>
        <text x="${cx(i)}" y="${y0 - 7}" text-anchor="middle" fill="${t.ink}" font-size="12" font-weight="600">${esc(fmt(v))}</text>
        <text x="${cx(i)}" y="${H - m.b + 20}" text-anchor="middle" fill="${t.muted}" font-size="11">${esc(cats[i])}</text>`; }).join("");
    return frame(t, []) + `<text x="14" y="${m.t + ph / 2}" transform="rotate(-90 14 ${m.t + ph / 2})" text-anchor="middle" fill="${t.muted}" font-size="11">${esc(yTitle)}</text>
      ${grid}<line x1="${m.l}" x2="${W - m.r}" y1="${y(0)}" y2="${y(0)}" stroke="${t.muted}"/>${bars}<text x="${m.l + pw / 2}" y="${H - 8}" text-anchor="middle" fill="${t.muted}" font-size="11">${esc(xTitle)}</text></svg>`;
  };
  return { svg, points, table: { head: ["Categoría", name], rows: cats.map((c, i) => [esc(c), String(values[i])]) } };
}

function scatterChart({ pts, xTitle, xLabel }) {
  const m = { l: 68, r: 24, t: 38, b: 52 }, pw = W - m.l - m.r, ph = H - m.t - m.b;
  const sc = logScale(pts.map((p) => p.y), m.t, ph), xmax = Math.max(...pts.map((p) => p.x), 1);
  const x = (v) => m.l + (v / xmax) * pw;
  const points = pts.map((p) => ({ x: x(p.x), y: sc.y(p.y), value: fmtTime(p.y), label: `${ENGINE_NAME[p.engine]} · ${xLabel} ${p.x}${p.extra ? " · " + p.extra : ""}` }));
  const engines = ["v1", "v2"].filter((e) => pts.some((p) => p.engine === e));
  const svg = (t) => {
    const grid = sc.ticks.map((k) => `<line x1="${m.l}" x2="${W - m.r}" y1="${sc.y(k.v)}" y2="${sc.y(k.v)}" stroke="${t.grid}"/><text x="${m.l - 8}" y="${sc.y(k.v) + 4}" text-anchor="end" fill="${t.muted}" font-size="11">${fmtTime(k.v)}</text>`).join("");
    const xt = [0, 0.25, 0.5, 0.75, 1].map((f) => `<text x="${x(xmax * f)}" y="${H - m.b + 20}" text-anchor="middle" fill="${t.muted}" font-size="11">${Math.round(xmax * f)}</text>`).join("");
    const dots = pts.map((p) => marker(SHAPE[p.engine], x(p.x), sc.y(p.y), t[p.engine], t, 3.5)).join("");
    return frame(t, engines.map((e) => ({ label: ENGINE_NAME[e], color: t[e], shape: SHAPE[e] }))) +
      `<text x="14" y="${m.t + ph / 2}" transform="rotate(-90 14 ${m.t + ph / 2})" text-anchor="middle" fill="${t.muted}" font-size="11">Tiempo (escala logarítmica)</text>${grid}${dots}${xt}
       <text x="${m.l + pw / 2}" y="${H - 8}" text-anchor="middle" fill="${t.muted}" font-size="11">${esc(xTitle)}</text></svg>`;
  };
  return { svg, points, table: { head: ["Motor", xLabel, "Tiempo (s)"], rows: pts.map((p) => [eng(p.engine), p.x, String(p.y)]) } };
}

// ---- chart cards (hover, table view, export) ---------------------------------------
function chartCard(id, title, subtitle, chart) {
  return `<section class="card pad chart-card" data-chart="${id}"><div class="chart-head"><div><h2>${esc(title)}</h2><p class="muted">${esc(subtitle)}</p></div>
    <div class="chart-actions"><button class="btn" data-act="table">Ver tabla</button><button class="btn" data-act="svg">SVG</button><button class="btn" data-act="png">PNG</button></div></div>
    <div class="chart-plot"></div><div class="chart-table" hidden>${table(chart.table.head, chart.table.rows)}</div></section>`;
}
const TIP = () => { let t = $("#viz-tip"); if (!t) { t = document.createElement("div"); t.id = "viz-tip"; t.className = "viz-tip"; t.hidden = true; document.body.appendChild(t); } return t; };

function mountCharts(root, charts) {
  const draw = () => {
    const t = THEMES[isDark() ? "dark" : "light"];
    root.querySelectorAll(".chart-card").forEach((card) => {
      const ch = charts[card.dataset.chart], plot = card.querySelector(".chart-plot");
      plot.innerHTML = ch.svg(t);
      const svg = plot.querySelector("svg"); svg.removeAttribute("width"); svg.removeAttribute("height"); svg.setAttribute("aria-label", card.querySelector("h2").textContent);
      const ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      ring.setAttribute("r", 9); ring.setAttribute("fill", "none"); ring.setAttribute("stroke", t.ink2); ring.setAttribute("stroke-width", 2); ring.setAttribute("display", "none");
      svg.appendChild(ring);
      const tip = TIP();
      svg.onpointermove = (e) => {
        const r = svg.getBoundingClientRect(), k = W / r.width, px = (e.clientX - r.left) * k, py = (e.clientY - r.top) * k;
        let best = null, d2 = 28 * 28; // hit radius much larger than the mark
        for (const p of ch.points) { const d = (p.x - px) ** 2 + (p.y - py) ** 2; if (d < d2) { d2 = d; best = p; } }
        if (!best) { ring.setAttribute("display", "none"); tip.hidden = true; return; }
        ring.setAttribute("cx", best.x); ring.setAttribute("cy", best.y); ring.setAttribute("display", "");
        tip.replaceChildren(Object.assign(document.createElement("strong"), { textContent: best.value }), Object.assign(document.createElement("span"), { textContent: best.label }));
        tip.hidden = false; tip.style.left = Math.min(e.clientX + 14, innerWidth - 220) + "px"; tip.style.top = e.clientY + 14 + "px";
      };
      svg.onpointerleave = () => { ring.setAttribute("display", "none"); tip.hidden = true; };
    });
  };
  draw();
  matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", draw);
  root.onclick = (e) => {
    const b = e.target.closest("[data-act]"); if (!b) return;
    const card = b.closest(".chart-card"), ch = charts[card.dataset.chart], name = `${card.dataset.chart}-${stamp()}`;
    if (b.dataset.act === "table") { const tb = card.querySelector(".chart-table"); tb.hidden = !tb.hidden; b.textContent = tb.hidden ? "Ver tabla" : "Ocultar tabla"; return; }
    const svgText = ch.svg(THEMES.light); // exports always use the light theme on a white-ish surface
    if (b.dataset.act === "svg") return download(name + ".svg", svgText, "image/svg+xml");
    const img = new Image(), url = URL.createObjectURL(new Blob([svgText], { type: "image/svg+xml;charset=utf-8" }));
    img.onload = () => {
      const c = document.createElement("canvas"); c.width = W * 3; c.height = H * 3; const g = c.getContext("2d"); g.scale(3, 3); g.drawImage(img, 0, 0, W, H);
      c.toBlob((blob) => { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name + ".png"; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000); }); URL.revokeObjectURL(url);
    };
    img.src = url;
  };
}

// ---- view ----------------------------------------------------------------------------------
function statTile(label, value) { return `<div class="card kpi"><span>${esc(label)}</span><strong>${value}</strong></div>`; }

async function viewReports() {
  const source = (location.hash.split("?")[1] || "").replace("fuente=", "") || "experimento";
  $("#app").innerHTML = `<div class="page-head"><div><h1>Reportes</h1><p class="muted">Gráficos comparativos de V1 y V2 listos para tu documento: pasa el cursor para ver valores, usa «Ver tabla» para los datos y descarga cada figura en SVG o PNG (tema claro).</p></div></div>
    <div class="tabs"><a href="#/reportes" class="${source === "experimento" ? "on" : ""}">Último experimento</a><a href="#/reportes?fuente=pedidos" class="${source === "pedidos" ? "on" : ""}">Pedidos reales</a></div><div id="rbox"></div>`;
  const box = $("#rbox"), charts = {};
  if (source === "pedidos") {
    const [orders, lat] = await Promise.all([api("/admin/orders?limit=500"), api("/admin/performance/orders")]);
    if (!orders.length) { box.innerHTML = '<div class="card empty">Todavía no hay pedidos. Compra en la tienda con V1 y V2 para generar datos reales.</div>'; return; }
    const chrono = orders.slice().reverse();
    const byEngine = Object.fromEntries(lat.map((x) => [x.engine, x]));
    const tiles = ["v1", "v2"].filter((e) => byEngine[e]).map((e) => statTile(`Mediana ${e.toUpperCase()} · ${byEngine[e].n} pedidos`, fmtTime(byEngine[e].p50))).join("");
    if (byEngine.v1 && byEngine.v2) charts.pct = lineChart({ cats: ["p50", "p90", "p95", "p99"], xTitle: "Percentil",
      series: ["v1", "v2"].map((e) => ({ key: e, name: ENGINE_NAME[e], values: ["p50", "p90", "p95", "p99"].map((q) => byEngine[e][q]) })) });
    charts.seq = scatterChart({ pts: chrono.map((o, i) => ({ x: i + 1, y: Math.max(o.processing_seconds, 1e-6), engine: o.engine, extra: `${o.item_count} u.` })), xTitle: "Pedido (orden cronológico)", xLabel: "pedido" });
    box.innerHTML = `<div class="kpis">${tiles}</div><div class="charts">
      ${charts.pct ? chartCard("pct", "Percentiles del tiempo de recibo", "Mediana, p90, p95 y p99 de los pedidos reales por motor.", charts.pct) : ""}
      ${chartCard("seq", "Tiempo de cada pedido", "Cada punto es un pedido real, en orden cronológico.", charts.seq)}</div>`;
  } else {
    const r = lastExperiment;
    if (!r) { box.innerHTML = '<div class="card pad empty">No hay un experimento guardado. Ejecútalo en <a href="#/experimentos">Experimentos</a> y vuelve aquí.</div>'; return; }
    const sizes = r.design.factors[1].levels, cell = (e, n) => r.cells.find((c) => c.engine === e && c.lines === n);
    const cats = sizes.map((n) => n + " líneas"), series = (f) => ["v1", "v2"].map((e) => ({ key: e, name: ENGINE_NAME[e], values: sizes.map((n) => cell(e, n)[f]) }));
    charts.median = lineChart({ cats, series: series("median"), xTitle: "Tamaño del pedido" });
    charts.p95 = lineChart({ cats, series: series("p95"), xTitle: "Tamaño del pedido", threshold: { value: r.design.threshold, label: `Umbral ${r.design.threshold} s` } });
    charts.speed = barChart({ cats, values: r.comparisons.map((c) => +c.speedup.toFixed(1)), key: "v2", name: "Aceleración", xTitle: "Tamaño del pedido", yTitle: "Veces más rápido (V1 ÷ V2)", fmt: (v) => fmtX(v) + "×" });
    charts.runs = scatterChart({ pts: r.runs.map((x) => ({ x: x.run, y: Math.max(x.seconds, 1e-6), engine: x.engine, extra: x.lines + " líneas" })), xTitle: "Orden de ejecución (aleatorizado)", xLabel: "corrida" });
    box.innerHTML = `<p class="muted">Experimento: ${esc(r.design.type)} · ${r.design.runs} corridas · semilla ${r.design.seed} · ${esc(r.environment.timestamp)}</p><div class="charts">
      ${chartCard("median", "Mediana del tiempo por tamaño de pedido", "V1 crece con el tamaño; V2 se mantiene casi plano. Escala logarítmica.", charts.median)}
      ${chartCard("p95", "p95 frente al umbral de aceptación", "El criterio de cumplimiento es p95 ≤ umbral. Escala logarítmica.", charts.p95)}
      ${chartCard("speed", "Aceleración de V2 respecto de V1", "Cociente de medianas por tamaño de pedido.", charts.speed)}
      ${chartCard("runs", "Tiempo de cada corrida en orden de ejecución", "Sin tendencia temporal: la aleatorización evita que el calentamiento o la carga sesguen la comparación.", charts.runs)}</div>`;
  }
  mountCharts(box, charts);
}
