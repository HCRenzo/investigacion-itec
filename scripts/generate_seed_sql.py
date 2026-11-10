#!/usr/bin/env python3
"""Generates supabase/seed/0002_datos_demo.sql: demo users, categories, products and initial stock.

Paste the generated file in Supabase > SQL Editor (after 0001_esquema.sql). It is idempotent: rows that already
exist are skipped. Passwords come from ADMIN_PASSWORD / DEMO_CUSTOMER_PASSWORD (.env or defaults) and are
written as scrypt hashes, never in clear text. The output is git-ignored because it contains those hashes.

    python3 scripts/generate_seed_sql.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.config import settings  # noqa: E402  (also loads .env)
from api.models import ROLE_ADMIN, ROLE_CUSTOMER  # noqa: E402
from api.services.security import PasswordHasher  # noqa: E402
from api.services.seed_service import SEED_PRODUCTS  # noqa: E402

q = lambda v: "'" + str(v).replace("'", "''") + "'"
hasher = PasswordHasher()
out = ["-- Datos de demostracion. Generado por scripts/generate_seed_sql.py. Idempotente.", ""]

out.append("-- Usuarios (contrasenas como hash scrypt)")
for name, email, password, role in (
    ("Administrador", settings.admin_email, settings.admin_password, ROLE_ADMIN),
    ("Cliente Prueba", settings.demo_customer_email, settings.demo_customer_password, ROLE_CUSTOMER),
):
    out.append(f"""insert into t_usuario (rol_id, nombre, email, password_hash)
select r.id, {q(name)}, {q(email)}, {q(hasher.hash(password))}
from t_rol r
where r.codigo = {q(role)} and r.deleted_at is null
  and not exists (select 1 from t_usuario u where lower(u.email) = {q(email.lower())} and u.deleted_at is null);
""")

out.append("-- Categorias")
for cat in sorted({p[3] for p in SEED_PRODUCTS}):
    out.append(f"""insert into t_categoria (nombre)
select {q(cat)}
where not exists (select 1 from t_categoria where lower(nombre) = {q(cat.lower())} and deleted_at is null);
""")

out.append("-- Productos")
for sku, name, desc, cat, price, stock in SEED_PRODUCTS:
    out.append(f"""insert into t_producto (categoria_id, sku, nombre, descripcion, precio, stock)
select c.id, {q(sku)}, {q(name)}, {q(desc)}, {price}, {stock}
from t_categoria c
where lower(c.nombre) = {q(cat.lower())} and c.deleted_at is null
  and not exists (select 1 from t_producto p where p.sku = {q(sku)} and p.deleted_at is null);
""")

out.append("""-- Historial de stock: un ingreso inicial por cada producto que aun no tiene movimientos
insert into t_movimiento_inventario (producto_id, tipo, cantidad, stock_resultante, motivo)
select p.id, 'INGRESO', p.stock, p.stock, 'Stock inicial'
from t_producto p
where p.stock > 0 and p.deleted_at is null
  and not exists (select 1 from t_movimiento_inventario m where m.producto_id = p.id);
""")

target = ROOT / "supabase" / "seed" / "0002_datos_demo.sql"
target.write_text("\n".join(out), encoding="utf-8")
print(f"Generado {target.relative_to(ROOT)}  ({len(SEED_PRODUCTS)} productos, 2 usuarios)")
