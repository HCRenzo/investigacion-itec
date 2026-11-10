"use strict";
let user = null;
let engineInfo = null; // which receipt engine this deployment runs (shown to staff only)

function logout() { store.token = null; user = null; engineInfo = null; location.hash = "#/login"; render(); }

function renderNav() {
  $("#topbar").hidden = !user;
  if (!user) return;
  const route = location.hash.split("/")[1] || "resumen";
  const link = (r, label) => `<a href="#/${r}" class="${route === r ? "active" : ""}">${label}</a>`;
  $("#nav").innerHTML = link("resumen", "Resumen") + link("ventas", "Ventas") + link("inventario", "Inventario");
  const engine = engineInfo ? `<span class="pill ${engineInfo.receipt_engine === "v1" ? "off" : ""}" title="${esc(engineInfo.source)}">Motor ${esc(engineInfo.receipt_engine.toUpperCase())}</span>` : "";
  $("#userbox").innerHTML = `${engine}<span id="user-name" class="muted">${esc(user.name)}</span><button class="btn" id="logout">Salir</button>`;
  $("#logout").onclick = logout;
}

// Temporary: pre-fill the login with the default admin. Set to null to disable.
const DEMO_LOGIN = { email: "admin@tienda.local", password: "admin1234" };

function viewLogin() {
  $("#app").innerHTML = `<div class="auth-wrap"><div class="card auth admin-auth">
    <div class="auth-hero admin-hero"><h1>Panel de administración</h1><p>Acceso exclusivo para el personal autorizado.</p></div>
    <div class="auth-form"><h2>Iniciar sesión</h2>
      <form class="stack" id="auth-form" novalidate>
        <label>Correo electrónico<input name="email" type="email" autocomplete="username" required value="${esc(DEMO_LOGIN?.email)}"></label>
        <label>Contraseña<input name="password" type="password" autocomplete="current-password" required value="${esc(DEMO_LOGIN?.password)}"></label>
        <p class="error" id="auth-error" role="alert"></p>
        <button class="btn primary block" type="submit">Entrar</button>
      </form><a href="/" class="muted">← Ir a la tienda</a>
    </div></div></div>`;
  $("#auth-form").onsubmit = async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("button[type=submit]"); btn.disabled = true;
    try {
      const data = await api("/admin/login", { method: "POST", body: Object.fromEntries(new FormData(e.target)) });
      store.token = data.token; user = data.user; location.hash = "#/resumen"; render();
    } catch (err) { $("#auth-error").textContent = err.message; btn.disabled = false; }
  };
}

async function viewSummary() {
  $("#app").innerHTML = '<div class="page-head"><h1>Resumen de ventas</h1></div><div id="box" class="muted">Cargando…</div>';
  const s = await api("/admin/summary");
  const max = Math.max(1, ...s.top_products.map((t) => t.units));
  $("#box").className = "";
  $("#box").innerHTML = `
    <div class="kpis">
      <div class="card kpi"><span>Ingresos</span><strong>${money(s.revenue)}</strong></div>
      <div class="card kpi"><span>Pedidos</span><strong>${s.orders}</strong></div>
      <div class="card kpi"><span>Unidades vendidas</span><strong>${s.units}</strong></div>
      <div class="card kpi"><span>Clientes</span><strong>${s.customers}</strong></div>
    </div>
    <div class="cols">
      <div class="card pad"><h2>Más vendidos</h2>${s.top_products.map((t) => `<div class="bar-row"><span>${esc(t.name)}</span><strong>${t.units} u · ${money(t.revenue)}</strong><div class="bar"><i style="width:${(t.units / max) * 100}%"></i></div></div>`).join("") || '<p class="muted">Sin ventas todavía.</p>'}</div>
      <div class="card pad"><h2>Tiempo de generación del recibo</h2>${s.engines.map((e) => `<div class="receipt-row"><span><span class="pill ${e.engine === "v1" ? "off" : ""}">${esc(e.engine.toUpperCase())}</span> ${e.orders} pedidos</span><strong>${e.avg_seconds} s promedio</strong></div>`).join("") || '<p class="muted">Sin datos todavía.</p>'}</div>
      <div class="card pad"><h2>Stock bajo</h2>${s.low_stock.map((p) => `<div class="receipt-row"><span>${esc(p.name)}</span><strong class="stock low">${p.stock} u.</strong></div>`).join("") || '<p class="muted">Todo en orden.</p>'}</div>
    </div>`;
}

async function viewSales() {
  $("#app").innerHTML = '<div class="page-head"><h1>Ventas</h1></div><div id="box" class="muted">Cargando…</div>';
  const orders = await api("/admin/orders");
  $("#box").className = "card table-wrap";
  $("#box").innerHTML = orders.length ? `<table><thead><tr><th>Recibo</th><th>Fecha</th><th>Cliente</th><th>Artículos</th><th>Motor</th><th class="num">Tiempo</th><th class="num">Total</th></tr></thead><tbody>
    ${orders.map((o) => `<tr><td><strong>${esc(o.number)}</strong></td><td>${fmtDate(o.created_at)}</td><td>${esc(o.customer)}<div class="muted">${esc(o.customer_email)}</div></td>
      <td>${o.items.map((i) => `${i.quantity} × ${esc(i.name)}`).join(", ")}</td><td><span class="pill ${o.engine === "v1" ? "off" : ""}">${esc(o.engine.toUpperCase())}</span></td><td class="num">${o.processing_seconds} s</td><td class="num"><strong>${money(o.total)}</strong></td></tr>`).join("")}</tbody></table>`
    : '<div class="empty">Todavía no hay ventas.</div>';
}

async function viewInventory() {
  $("#app").innerHTML = '<div class="page-head"><h1>Inventario</h1><button class="btn primary" id="new-p">Nuevo producto</button></div><div id="box" class="muted">Cargando…</div>';
  const list = await api("/admin/products");
  $("#box").className = "card table-wrap";
  $("#box").innerHTML = `<table><thead><tr><th>SKU</th><th>Producto</th><th>Categoría</th><th class="num">Precio</th><th class="num">Stock</th><th>Estado</th><th></th></tr></thead><tbody>
    ${list.map((p) => `<tr><td>${esc(p.sku)}</td><td><strong>${esc(p.name)}</strong></td><td>${esc(p.category)}</td><td class="num">${money(p.price)}</td>
      <td class="num ${p.stock <= 10 ? "stock low" : ""}">${p.stock}</td><td><span class="pill ${p.active ? "" : "off"}">${p.active ? "Activo" : "Oculto"}</span></td>
      <td class="num"><button class="btn" data-edit="${p.id}">Editar</button></td></tr>`).join("")}</tbody></table>`;
  const open = (p) => productForm(p, viewInventory);
  $("#new-p").onclick = () => open(null);
  $("#box").onclick = (e) => { const b = e.target.closest("[data-edit]"); if (b) open(list.find((p) => p.id === b.dataset.edit)); };
}

function productForm(p, done) {
  const m = $("#modal"); m.hidden = false;
  m.innerHTML = `<div class="card" role="dialog" aria-label="Producto"><h2 style="margin-bottom:16px">${p ? "Editar" : "Nuevo"} producto</h2>
    <form class="stack" id="pf" novalidate><div class="form-grid">
      <label>SKU<input name="sku" required value="${esc(p?.sku)}"></label>
      <label>Categoría<input name="category" value="${esc(p?.category || "General")}"></label>
      <label class="full">Nombre<input name="name" required value="${esc(p?.name)}"></label>
      <label class="full">Descripción<textarea name="description" rows="2">${esc(p?.description)}</textarea></label>
      <label>Precio<input name="price" type="number" step="0.01" min="0.01" required value="${esc(p?.price)}"></label>
      <label>Stock<input name="stock" type="number" min="0" step="1" required value="${esc(p?.stock ?? 0)}"></label>
      <label class="full" style="grid-auto-flow:column;justify-content:start;align-items:center;gap:8px"><input name="active" type="checkbox" style="width:auto" ${p?.active === false ? "" : "checked"}> Visible en la tienda</label>
    </div><p class="error" id="pf-error" role="alert"></p>
    <div style="display:flex;gap:10px;justify-content:flex-end"><button type="button" class="btn" id="pf-cancel">Cancelar</button><button class="btn primary" type="submit">Guardar</button></div></form></div>`;
  $("#pf-cancel").onclick = closeModal;
  $("#pf").onsubmit = async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const body = { sku: f.get("sku").trim(), name: f.get("name").trim(), description: f.get("description"), category: f.get("category").trim() || "General",
      price: f.get("price"), stock: parseInt(f.get("stock"), 10), active: f.get("active") === "on" };
    try { await api(p ? `/admin/products/${p.id}` : "/admin/products", { method: p ? "PUT" : "POST", body }); closeModal(); toast("Producto guardado"); await loadProducts(); done(); }
    catch (err) { $("#pf-error").textContent = err.message; }
  };
}


async function loadProducts() {}

async function render() {
  if (user && !engineInfo) { try { engineInfo = await api("/admin/config"); } catch {} }
  renderNav();
  if (!user) return viewLogin();
  const route = (location.hash.split("/")[1] || "resumen").split("?")[0];
  try {
    if (route === "ventas") await viewSales();
    else if (route === "inventario") await viewInventory();
    else await viewSummary();
  } catch (err) { toast(err.message); }
}

window.addEventListener("hashchange", render);

(async function init() {
  if (store.token) { try { user = await api("/auth/me"); if (user.role !== "admin") throw new Error(); } catch { store.token = null; user = null; } }
  if (!user) location.hash = "#/login";
  render();
})();
