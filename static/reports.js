"use strict";
// Admin module "Reportes": charts comparing receipt engine V1 vs V2 (inline SVG, no libraries).
// Palette: categorical slots 1 (blue = V1) and 2 (orange = V2), validated light and dark with the dataviz validator.

const THEMES = {
  light: { surface: "#fcfcfb", ink: "#0b0b0b", ink2: "#52514e", muted: "#6f6e69", grid: "#e6e5e1", v1: "#2a78d6", v2: "#eb6834", data: "#1baf7a" },
  dark: { surface: "#1a1a19", ink: "#f0efec", ink2: "#c3c2b7", muted: "#9a9990", grid: "#302f2d", v1: "#3987e5", v2: "#d95926", data: "#199e70" },
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
function niceScale(max) {
  const raw = max / 4, p = 10 ** Math.floor(Math.log10(raw)), step = [1, 2, 2.5, 5, 10].map((k) => k * p).find((x) => x >= raw);
  const n = Math.max(1, Math.ceil(max / step));
  return { top: n * step, ticks: Array.from({ length: n + 1 }, (_, i) => i * step) };
}
const DB_FLOOR = 1e-3; // t_pedido stores the time with 1 ms resolution
const dbTime = (s) => Math.max(s, DB_FLOOR);
const dbLabel = (s) => (s <= DB_FLOOR ? "≤ 1 ms (resolución de la base)" : null);
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
  const m = { l: 68, r: 24, t: 38, b: 52 }, pw = W - m.l - m.r, ph = H - m.t - m.b, ns = niceScale(Math.max(...values, 1)), top = ns.top;
  const y = (v) => m.t + (1 - v / top) * ph, band = pw / cats.length, bw = Math.min(24, band * 0.5);
  const cx = (i) => m.l + band * (i + 0.5);
  const points = values.map((v, i) => ({ x: cx(i), y: y(v), value: fmt(v), label: `${name} · ${cats[i]}` }));
  const svg = (t) => {
    const grid = ns.ticks.map((v) => { return `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="${t.grid}"/><text x="${m.l - 8}" y="${y(v) + 4}" text-anchor="end" fill="${t.muted}" font-size="11">${fmtX(v)}</text>`; }).join("");
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
  const points = pts.map((p) => ({ x: x(p.x), y: sc.y(p.y), value: p.display || fmtTime(p.y), label: `${ENGINE_NAME[p.engine]} · ${xLabel} ${p.x}${p.extra ? " · " + p.extra : ""}` }));
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


function groupedColumns({ cats, series, xTitle, yTitle, name }) {
  const m = { l: 68, r: 24, t: 38, b: 64 }, pw = W - m.l - m.r, ph = H - m.t - m.b, ns = niceScale(Math.max(...series.flatMap((s) => s.values), 1)), top = ns.top;
  const y = (v) => m.t + (1 - v / top) * ph, band = pw / cats.length, bw = Math.min(24, (band * 0.7) / series.length - 2);
  const bx = (i, k) => m.l + band * (i + 0.5) + (k - (series.length - 1) / 2) * (bw + 2) - bw / 2;
  const points = series.flatMap((s, k) => s.values.map((v, i) => ({ x: bx(i, k) + bw / 2, y: y(v), value: fmtX(v), label: `${s.name} · ${cats[i]}` })));
  const svg = (t) => {
    const grid = ns.ticks.map((v) => { return `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="${t.grid}"/><text x="${m.l - 8}" y="${y(v) + 4}" text-anchor="end" fill="${t.muted}" font-size="11">${fmtX(v)}</text>`; }).join("");
    const bars = series.map((s, k) => s.values.map((v, i) => { if (!v) return ""; const h = ph * v / top, r = Math.min(4, h), x0 = bx(i, k), y0 = y(v);
      return `<path d="M${x0},${y0 + h} V${y0 + r} Q${x0},${y0} ${x0 + r},${y0} H${x0 + bw - r} Q${x0 + bw},${y0} ${x0 + bw},${y0 + r} V${y0 + h} Z" fill="${t[s.key]}"/>`; }).join("")).join("");
    const xs = cats.map((c, i) => `<text x="${m.l + band * (i + 0.5)}" y="${H - m.b + 18}" text-anchor="${cats.length > 8 ? "end" : "middle"}" ${cats.length > 8 ? `transform="rotate(-35 ${m.l + band * (i + 0.5)} ${H - m.b + 18})"` : ""} fill="${t.muted}" font-size="11">${esc(c)}</text>`).join("");
    return frame(t, series.length > 1 ? series.map((s) => ({ label: s.name, color: t[s.key], shape: SHAPE[s.key] })) : []) +
      `<text x="14" y="${m.t + ph / 2}" transform="rotate(-90 14 ${m.t + ph / 2})" text-anchor="middle" fill="${t.muted}" font-size="11">${esc(yTitle)}</text>${grid}
       <line x1="${m.l}" x2="${W - m.r}" y1="${y(0)}" y2="${y(0)}" stroke="${t.muted}"/>${bars}${xs}<text x="${m.l + pw / 2}" y="${H - 6}" text-anchor="middle" fill="${t.muted}" font-size="11">${esc(xTitle)}</text></svg>`;
  };
  return { svg, points, table: { head: ["Categoría", ...series.map((s) => s.name)], rows: cats.map((c, i) => [esc(c), ...series.map((s) => String(s.values[i]))]) } };
}

function hbarChart({ labels, values, xTitle, fmt, name }) {
  const row = 28, m = { l: 178, r: 70, t: 20, b: 44 }, h = m.t + labels.length * row + m.b, pw = W - m.l - m.r;
  const ns = niceScale(Math.max(...values, 1)), top = ns.top, xv = (v) => (v / top) * pw, cy = (i) => m.t + row * (i + 0.5);
  const cut = (l) => (l.length > 26 ? l.slice(0, 25) + "…" : l);
  const points = values.map((v, i) => ({ x: m.l + xv(v), y: cy(i), value: fmt(v), label: `${name} · ${labels[i]}` }));
  const svg = (t) => {
    const grid = ns.ticks.map((v) => { return `<line x1="${m.l + xv(v)}" x2="${m.l + xv(v)}" y1="${m.t}" y2="${h - m.b}" stroke="${t.grid}"/><text x="${m.l + xv(v)}" y="${h - m.b + 16}" text-anchor="middle" fill="${t.muted}" font-size="11">${fmtX(v)}</text>`; }).join("");
    const bars = values.map((v, i) => { const w = xv(v), r = Math.min(4, w), y0 = cy(i) - 9;
      return `<text x="${m.l - 8}" y="${cy(i) + 4}" text-anchor="end" fill="${t.ink2}" font-size="12">${esc(cut(labels[i]))}</text>
        <path d="M${m.l},${y0} H${m.l + w - r} Q${m.l + w},${y0} ${m.l + w},${y0 + r} V${y0 + 18 - r} Q${m.l + w},${y0 + 18} ${m.l + w - r},${y0 + 18} H${m.l} Z" fill="${t.data}"/>
        <text x="${m.l + w + 8}" y="${cy(i) + 4}" fill="${t.ink}" font-size="12" font-weight="600">${esc(fmt(v))}</text>`; }).join("");
    return frame(t, [], W, h) + `${grid}<line x1="${m.l}" x2="${m.l}" y1="${m.t}" y2="${h - m.b}" stroke="${t.muted}"/>${bars}
      <text x="${m.l + pw / 2}" y="${h - 6}" text-anchor="middle" fill="${t.muted}" font-size="11">${esc(xTitle)}</text></svg>`;
  };
  return { svg, points, h, table: { head: ["Elemento", name], rows: labels.map((l, i) => [esc(l), String(values[i])]) } };
}

function logHistogram(rows) {
  const vals = rows.map((r) => dbTime(r.seconds)), lo = Math.log10(Math.min(...vals)), hi = Math.log10(Math.max(...vals)), n = 10, step = (hi - lo || 1) / n;
  const bin = (v) => Math.min(n - 1, Math.floor((Math.log10(v) - lo) / step));
  const counts = { v1: Array(n).fill(0), v2: Array(n).fill(0) };
  rows.forEach((r) => counts[r.engine][bin(dbTime(r.seconds))]++);
  const cats = counts.v1.map((_, i) => fmtTime(10 ** (lo + i * step)));
  const series = ["v1", "v2"].filter((e) => counts[e].some(Boolean)).map((e) => ({ key: e, name: ENGINE_NAME[e], values: counts[e] }));
  return groupedColumns({ cats, series, xTitle: "Tiempo de recibo (límite inferior del intervalo, escala logarítmica)", yTitle: "Pedidos", name: "Pedidos" });
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
      const c = document.createElement("canvas"); const hh = ch.h || H; c.width = W * 3; c.height = hh * 3; const g = c.getContext("2d"); g.scale(3, 3); g.drawImage(img, 0, 0, W, hh);
      c.toBlob((blob) => { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name + ".png"; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000); }); URL.revokeObjectURL(url);
    };
    img.src = url;
  };
}

// ---- view ----------------------------------------------------------------------------------
function statTile(label, value) { return `<div class="card kpi"><span>${esc(label)}</span><strong>${value}</strong></div>`; }

async function viewReports() {
  const source = (location.hash.split("?")[1] || "").replace("fuente=", "") || "experimento";
  const tab = (id, label) => `<a href="#/reportes${id === "experimento" ? "" : "?fuente=" + id}" class="${source === id ? "on" : ""}">${label}</a>`;
  $("#app").innerHTML = `<div class="page-head"><div><h1>Reportes</h1><p class="muted">Gráficos comparativos de V1 y V2 listos para tu documento: pasa el cursor para ver valores, usa «Ver tabla» para los datos y descarga cada figura en SVG o PNG (tema claro).</p></div></div>
    <div class="tabs">${tab("experimento", "Último experimento")}${tab("pedidos", "Pedidos reales")}${tab("bd", "Base de datos")}</div><div id="rbox"></div>`;
  const box = $("#rbox"), charts = {};
  if (source === "bd") {
    const d = await api("/admin/reports/dataset"), o = d.orders;
    if (!d.stock.length) { box.innerHTML = '<div class="card pad empty">La base no tiene datos para graficar.</div>'; return; }
    const top = (arr, k, n) => arr.slice().sort((a, b) => b[k] - a[k]).slice(0, n);
    const units = d.by_product.reduce((a, x) => a + x.units, 0), revenue = d.by_product.reduce((a, x) => a + x.revenue, 0);
    const cats = {}; d.by_product.forEach((x) => { cats[x.category] = (cats[x.category] || 0) + x.revenue; });
    const catRows = Object.entries(cats).sort((a, b) => b[1] - a[1]);
    const days = [...new Set(o.map((x) => (x.created_at || "").slice(0, 10)).filter(Boolean))].sort().slice(-14);
    const perDay = (e) => days.map((dd) => o.filter((x) => x.engine === e && (x.created_at || "").slice(0, 10) === dd).length);
    const mv = {}; d.movements.forEach((x) => { mv[x.type] = (mv[x.type] || 0) + x.units; });
    const low = d.stock.slice().sort((a, b) => a.stock - b.stock).slice(0, 10);
    const tiles = [statTile("Pedidos", o.length), statTile("Unidades vendidas", units), statTile("Ingresos", money(revenue)), statTile("Productos", d.stock.length),
      statTile("Base", esc(d.database.dialect) + (d.database.supabase ? " · Supabase" : ""))].join("");
    if (o.length) {
      charts.hist = logHistogram(o);
      charts.size = scatterChart({ pts: o.map((x) => ({ x: x.lines, y: dbTime(x.seconds), display: dbLabel(x.seconds), engine: x.engine, extra: x.units + " u." })), xTitle: "Líneas por pedido", xLabel: "líneas" });
      charts.day = groupedColumns({ cats: days, series: ["v1", "v2"].map((e) => ({ key: e, name: ENGINE_NAME[e], values: perDay(e) })).filter((x) => x.values.some(Boolean)), xTitle: "Día", yTitle: "Pedidos", name: "Pedidos" });
      charts.top = hbarChart({ labels: top(d.by_product, "units", 10).map((x) => x.product), values: top(d.by_product, "units", 10).map((x) => x.units), xTitle: "Unidades vendidas", fmt: (v) => fmtX(v), name: "Unidades" });
      charts.cat = hbarChart({ labels: catRows.map((x) => x[0]), values: catRows.map((x) => +x[1].toFixed(2)), xTitle: "Ingresos ($)", fmt: (v) => money(v), name: "Ingresos" });
    }
    charts.stock = hbarChart({ labels: low.map((x) => x.product), values: low.map((x) => x.stock), xTitle: "Stock actual (10 productos con menos existencias)", fmt: (v) => fmtX(v), name: "Stock" });
    const mvKeys = Object.keys(mv);
    if (mvKeys.length) charts.mov = hbarChart({ labels: mvKeys, values: mvKeys.map((k) => mv[k]), xTitle: "Unidades movidas en el kardex", fmt: (v) => fmtX(v), name: "Unidades" });
    const cards = [
      ["hist", "Distribución del tiempo de recibo", "Histograma en intervalos logarítmicos: V1 y V2 ocupan zonas distintas, casi sin solape."],
      ["size", "Tamaño del pedido frente al tiempo", "Cada punto es un pedido real: ¿crece el tiempo con las líneas del pedido?"],
      ["day", "Pedidos por día y motor", "Volumen de ventas procesado con cada motor en los últimos días."],
      ["top", "Productos más vendidos", "Los 10 con más unidades vendidas."], ["cat", "Ingresos por categoría", "Composición de las ventas registradas."],
      ["stock", "Stock más bajo", "Inventario actual de los productos con menos existencias."], ["mov", "Movimientos de inventario por tipo", "Unidades registradas en el kardex."]]
      .filter(([id]) => charts[id]).map(([id, t, sub]) => chartCard(id, t, sub, charts[id])).join("");
    box.innerHTML = `<div class="kpis">${tiles}</div><p class="muted" style="margin-top:8px">Nota: la base guarda el tiempo del recibo con resolución de 1 ms, por lo que los tiempos de V2 (microsegundos) aparecen en el piso de 1 ms. Para medir V2 con precisión usa el módulo Experimentos.</p>${o.length ? "" : '<div class="card pad empty" style="margin-top:12px">Aún no hay pedidos: los gráficos de ventas aparecerán cuando se registren compras.</div>'}
      <div class="charts">${cards}</div>
      <div class="card pad" style="margin-top:16px"><h2>Datos para el artículo</h2><p class="muted">Tablas agregadas de la base (sin datos personales de clientes).</p><div style="display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn" id="dl-o">Pedidos (CSV)</button><button class="btn" id="dl-p">Ventas por producto (CSV)</button><button class="btn" id="dl-s">Stock (CSV)</button><button class="btn" id="dl-m">Movimientos de inventario (CSV)</button></div></div>`;
    $("#dl-o").onclick = () => download("bd-pedidos-" + stamp() + ".csv", toCSV(o));
    $("#dl-p").onclick = () => download("bd-ventas-producto-" + stamp() + ".csv", toCSV(d.by_product));
    $("#dl-s").onclick = () => download("bd-stock-" + stamp() + ".csv", toCSV(d.stock));
    $("#dl-m").onclick = () => download("bd-movimientos-" + stamp() + ".csv", toCSV(d.movements));
  } else if (source === "pedidos") {
    const [orders, lat] = await Promise.all([api("/admin/orders?limit=500"), api("/admin/performance/orders")]);
    if (!orders.length) { box.innerHTML = '<div class="card empty">Todavía no hay pedidos. Compra en la tienda con V1 y V2 para generar datos reales.</div>'; return; }
    const chrono = orders.slice().reverse();
    const byEngine = Object.fromEntries(lat.map((x) => [x.engine, x]));
    const tiles = ["v1", "v2"].filter((e) => byEngine[e]).map((e) => statTile(`Mediana ${e.toUpperCase()} · ${byEngine[e].n} pedidos`, fmtTime(byEngine[e].p50))).join("");
    if (byEngine.v1 && byEngine.v2) charts.pct = lineChart({ cats: ["p50", "p90", "p95", "p99"], xTitle: "Percentil",
      series: ["v1", "v2"].map((e) => ({ key: e, name: ENGINE_NAME[e], values: ["p50", "p90", "p95", "p99"].map((q) => dbTime(byEngine[e][q])) })) });
    charts.seq = scatterChart({ pts: chrono.map((o, i) => ({ x: i + 1, y: dbTime(o.processing_seconds), display: dbLabel(o.processing_seconds), engine: o.engine, extra: `${o.item_count} u.` })), xTitle: "Pedido (orden cronológico)", xLabel: "pedido" });
    box.innerHTML = `<div class="kpis">${tiles}</div><p class="muted" style="margin-top:8px">Nota: la base guarda el tiempo del recibo con resolución de 1 ms, por lo que los tiempos de V2 (microsegundos) aparecen en el piso de 1 ms. Para medir V2 con precisión usa el módulo Experimentos.</p><div class="charts">
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
