"use strict";
// Shared helpers for the client store (/) and the admin panel (/admin).
const SESSION = document.body.dataset.session; // "client" | "admin"
const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (v) => "$" + Number(v).toFixed(2);
const fmtDate = (iso) => new Date(iso).toLocaleString("es", { dateStyle: "medium", timeStyle: "short" });

// Separate storage keys: a client session is never valid in the admin panel and vice versa.
const store = {
  get token() { try { return localStorage.getItem(SESSION + "_token"); } catch { return null; } },
  set token(v) { try { v ? localStorage.setItem(SESSION + "_token", v) : localStorage.removeItem(SESSION + "_token"); } catch {} },
  get cart() { try { return JSON.parse(localStorage.getItem("cart")) || []; } catch { return []; } },
  set cart(v) { try { localStorage.setItem("cart", JSON.stringify(v)); } catch {} },
};

async function api(path, { method = "GET", body } = {}) {
  const res = await fetch("/api" + path, {
    method,
    headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...(store.token ? { Authorization: "Bearer " + store.token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && store.token && typeof logout === "function") logout();
    const d = data.detail;
    throw new Error(Array.isArray(d) ? d.map((e) => e.msg.replace(/^Value error, /, "")).join(". ") : d || "Error inesperado");
  }
  return data;
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg; t.classList.add("show");
  clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove("show"), 2600);
}

function closeModal() { $("#modal").hidden = true; $("#modal").innerHTML = ""; }
$("#modal").addEventListener("mousedown", (e) => { if (e.target.id === "modal") closeModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeModal(); if (typeof closeCart === "function") closeCart(); } });
