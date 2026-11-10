"use strict";
const COLORS = ["#4f46e5", "#0891b2", "#059669", "#d97706", "#db2777", "#7c3aed"];
const colorFor = (st) => COLORS[[...String(st)].reduce((n, c) => n + c.charCodeAt(0), 0) % COLORS.length];

let user = null;
let products = [];
let cart = store.cart; // [{id, quantity}]

// ---------- session ----------
function setSession(data) { store.token = data.token; user = data.user; location.hash = "#/tienda"; render(); }
function logout() { store.token = null; user = null; cart = []; store.cart = cart; closeCart(); location.hash = "#/login"; render(); }

// ---------- cart ----------
const productById = (id) => products.find((p) => p.id === id);
const cartLines = () => cart.map((l) => ({ ...l, p: productById(l.id) })).filter((l) => l.p);
const cartCount = () => cartLines().reduce((n, l) => n + l.quantity, 0);
const cartSubtotal = () => cartLines().reduce((s, l) => s + Number(l.p.price) * l.quantity, 0);

function setQty(id, qty) {
  const p = productById(id);
  qty = Math.min(qty, p ? p.stock : qty);
  cart = qty <= 0 ? cart.filter((l) => l.id !== id) : cart.some((l) => l.id === id) ? cart.map((l) => (l.id === id ? { ...l, quantity: qty } : l)) : [...cart, { id, quantity: qty }];
  store.cart = cart; renderCart(); renderNav();
}
function addToCart(id) {
  const cur = cart.find((l) => l.id === id)?.quantity || 0;
  const p = productById(id);
  if (cur >= p.stock) return toast("No hay más stock disponible");
  setQty(id, cur + 1); toast(`${p.name} agregado`);
}
function openCart() { renderCart(); $("#cart").hidden = false; $("#scrim").hidden = false; }
function closeCart() { $("#cart").hidden = true; $("#scrim").hidden = true; }

function renderCart() {
  const lines = cartLines();
  $("#cart-body").innerHTML = lines.length ? lines.map(({ p, quantity }) => `
    <div class="cart-line">
      <div><strong>${esc(p.name)}</strong><div class="muted">${money(p.price)} c/u</div></div>
      <strong>${money(Number(p.price) * quantity)}</strong>
      <div class="qty"><button data-dec="${p.id}" aria-label="Menos">−</button><span>${quantity}</span><button data-inc="${p.id}" aria-label="Más">+</button></div>
      <button class="icon-btn" data-del="${p.id}" aria-label="Quitar ${esc(p.name)}" style="justify-self:end">Quitar</button>
    </div>`).join("") : '<div class="empty">Tu carrito está vacío.</div>';
  const sub = cartSubtotal(), tax = sub * 0.21;
  $("#cart-foot").innerHTML = lines.length ? `
    <div class="sum"><span>Subtotal</span><span>${money(sub)}</span></div>
    <div class="sum"><span>IVA (21%)</span><span>${money(tax)}</span></div>
    <div class="sum total"><span>Total</span><span>${money(sub + tax)}</span></div>
    <button class="btn primary block" id="pay">Comprar ahora</button>` : "";
}

$("#cart").addEventListener("click", async (e) => {
  const b = e.target.closest("button"); if (!b) return;
  const q = (id) => cart.find((l) => l.id === id)?.quantity || 0;
  if (b.dataset.inc) setQty(b.dataset.inc, q(b.dataset.inc) + 1);
  else if (b.dataset.dec) setQty(b.dataset.dec, q(b.dataset.dec) - 1);
  else if (b.dataset.del) setQty(b.dataset.del, 0);
  else if (b.id === "pay") {
    b.disabled = true; b.textContent = "Procesando…";
    const t0 = Date.now();
    const tick = setInterval(() => { b.textContent = `Generando recibo… ${((Date.now() - t0) / 1000).toFixed(0)} s`; }, 250);
    try {
      const order = await api("/orders", { method: "POST", body: { lines: cart.map((l) => ({ product_id: l.id, quantity: l.quantity })) } });
      cart = []; store.cart = cart; closeCart(); await loadProducts(); showReceipt(order); render();
    } catch (err) { toast(err.message); await loadProducts(); renderCart(); }
    finally { clearInterval(tick); }
  } else if (b.id === "cart-close") closeCart();
});
$("#cart-close").onclick = closeCart;
$("#scrim").onclick = closeCart;

function showReceipt(o) {
  const m = $("#modal");
  m.hidden = false;
  m.innerHTML = `<div class="card" role="dialog" aria-label="Compra realizada">
    <div class="check">✓</div><h2 style="text-align:center">¡Compra realizada!</h2>
    <p class="muted" style="text-align:center;margin:4px 0 16px">Recibo ${esc(o.number)} · ${fmtDate(o.created_at)}</p>
    <p style="text-align:center"><span class="muted">Recibo generado en ${o.processing_seconds} s</span></p>
    ${o.items.map((i) => `<div class="receipt-row"><span>${i.quantity} × ${esc(i.name)}</span><span>${money(i.line_total)}</span></div>`).join("")}
    <div class="receipt-row"><span>Subtotal</span><span>${money(o.subtotal)}</span></div>
    <div class="receipt-row"><span>IVA</span><span>${money(o.tax)}</span></div>
    <div class="receipt-row"><strong>Total</strong><strong>${money(o.total)}</strong></div>
    <button class="btn primary block" id="modal-ok" style="margin-top:18px">Seguir comprando</button></div>`;
  $("#modal-ok").onclick = closeModal;
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeCart(); });

// ---------- chrome ----------
function renderNav() {
  const bar = $("#topbar");
  bar.hidden = !user;
  if (!user) return;
  const route = location.hash.split("/")[1] || "tienda";
  const link = (r, label) => `<a href="#/${r}" class="${route === r ? "active" : ""}">${label}</a>`;
  $("#nav").innerHTML = link("tienda", "Tienda") + link("pedidos", "Mis pedidos");
  $("#userbox").innerHTML = `<span id="user-name" class="muted">${esc(user.name)}</span>
    <button class="btn" id="open-cart">Carrito${cartCount() ? `<span class="badge">${cartCount()}</span>` : ""}</button>
    <button class="btn" id="logout">Salir</button>`;
  $("#open-cart").onclick = openCart;
  $("#logout").onclick = logout;
}

// ---------- views ----------
// Temporary: pre-fill the login with the demo customer. Set to null to disable.
const DEMO_LOGIN = { email: "cliente@prueba.com", password: "cliente1234" };

function viewAuth(mode = "login") {
  const reg = mode === "register";
  $("#app").innerHTML = `<div class="auth-wrap"><div class="card auth">
    <div class="auth-hero"><h1>Compra fácil,<br>vende mejor.</h1><p>Explora el catálogo, arma tu carrito y paga en segundos.</p></div>
    <div class="auth-form">
      <div class="tabs"><button class="${reg ? "" : "on"}" data-m="login">Iniciar sesión</button><button class="${reg ? "on" : ""}" data-m="register">Crear cuenta</button></div>
      <form class="stack" id="auth-form" novalidate>
        ${reg ? '<label>Nombre completo<input name="name" autocomplete="name" required minlength="2"></label>' : ""}
        <label>Correo electrónico<input name="email" type="email" autocomplete="email" required value="${reg ? "" : esc(DEMO_LOGIN?.email)}"></label>
        <label>Contraseña<input name="password" type="password" autocomplete="${reg ? "new-password" : "current-password"}" required value="${reg ? "" : esc(DEMO_LOGIN?.password)}" ${reg ? 'minlength="8" placeholder="Mínimo 8 caracteres"' : ""}></label>
        <p class="error" id="auth-error" role="alert"></p>
        <button class="btn primary block" type="submit">${reg ? "Registrarme" : "Entrar"}</button>
      </form>
    </div></div></div>`;
  document.querySelectorAll(".tabs button").forEach((b) => (b.onclick = () => viewAuth(b.dataset.m)));
  $("#auth-form").onsubmit = async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target));
    const btn = e.target.querySelector("button[type=submit]"); btn.disabled = true;
    try { setSession(await api(reg ? "/auth/register" : "/auth/login", { method: "POST", body })); }
    catch (err) { $("#auth-error").textContent = err.message; btn.disabled = false; }
  };
}

let shopFilter = { q: "", cat: "Todos" };
function viewShop() {
  const cats = ["Todos", ...new Set(products.map((p) => p.category))];
  $("#app").innerHTML = `
    <div class="page-head"><div><h1>Catálogo</h1><span class="muted">Hola, ${esc(user.name.split(" ")[0])}. ¿Qué necesitas hoy?</span></div></div>
    <div class="toolbar"><input id="q" type="search" placeholder="Buscar productos…" value="${esc(shopFilter.q)}" aria-label="Buscar">
      ${cats.map((c) => `<button class="chip ${c === shopFilter.cat ? "on" : ""}" data-cat="${esc(c)}">${esc(c)}</button>`).join("")}</div>
    <div class="grid" id="grid"></div>`;
  const draw = () => {
    const q = shopFilter.q.toLowerCase();
    const list = products.filter((p) => (shopFilter.cat === "Todos" || p.category === shopFilter.cat) && (p.name + p.description).toLowerCase().includes(q));
    $("#grid").innerHTML = list.map((p) => `
      <article class="card product">
        <div class="thumb" style="background:${colorFor(p.category)}" aria-hidden="true">${esc(p.name[0])}</div>
        <div class="product-body"><span class="cat">${esc(p.category)}</span><strong>${esc(p.name)}</strong><p>${esc(p.description)}</p>
          <div class="price-row"><span class="price">${money(p.price)}</span><span class="stock ${p.stock <= 10 ? "low" : ""}">${p.stock ? (p.stock <= 10 ? `Quedan ${p.stock}` : `${p.stock} disp.`) : "Agotado"}</span></div>
          <button class="btn primary" data-add="${p.id}" ${p.stock ? "" : "disabled"}>Agregar al carrito</button></div>
      </article>`).join("") || '<div class="empty" style="grid-column:1/-1">No encontramos productos.</div>';
  };
  draw();
  $("#q").oninput = (e) => { shopFilter.q = e.target.value; draw(); };
  $(".toolbar").onclick = (e) => { const c = e.target.closest("[data-cat]"); if (c) { shopFilter.cat = c.dataset.cat; viewShop(); } };
  $("#grid").onclick = (e) => { const b = e.target.closest("[data-add]"); if (b) addToCart(b.dataset.add); };
}

async function viewOrders() {
  $("#app").innerHTML = '<div class="page-head"><h1>Mis pedidos</h1></div><div id="list" class="muted">Cargando…</div>';
  const orders = await api("/orders");
  $("#list").className = "";
  $("#list").innerHTML = orders.length ? orders.map((o) => `
    <div class="card pad" style="margin-bottom:14px">
      <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap"><strong>${esc(o.number)}</strong><span class="muted">${fmtDate(o.created_at)}</span></div>
      ${o.items.map((i) => `<div class="receipt-row"><span>${i.quantity} × ${esc(i.name)}</span><span>${money(i.line_total)}</span></div>`).join("")}
      <div class="receipt-row"><strong>Total (IVA incl.)</strong><strong>${money(o.total)}</strong></div></div>`).join("")
    : '<div class="card empty">Aún no has hecho compras. <a href="#/tienda">Ir a la tienda</a></div>';
}

// ---------- router ----------
async function loadProducts() { try { products = await api("/products"); } catch { products = []; } cart = cart.filter((l) => productById(l.id)); store.cart = cart; }

async function render() {
  renderNav();
  const route = (location.hash.split("/")[1] || "").split("?")[0];
  if (!user) return viewAuth(route === "registro" ? "register" : "login");
  try {
    if (route === "pedidos") await viewOrders();
    else { if (!products.length) await loadProducts(); viewShop(); }
  } catch (err) { toast(err.message); }
}

window.addEventListener("hashchange", () => { closeCart(); render(); });

(async function init() {
  if (store.token) { try { user = await api("/auth/me"); await loadProducts(); } catch { store.token = null; } }
  if (!user && !location.hash.startsWith("#/")) location.hash = "#/login";
  render();
})();
