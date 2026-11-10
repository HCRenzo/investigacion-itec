-- Esquema de la tienda (Supabase / PostgreSQL). Ver docs/PLAN_BASE_DE_DATOS.md
-- Ejecutar una sola vez. Idempotente salvo los datos de t_rol (usa ON CONFLICT).

-- =====================================================================
-- 1. Tablas. Columnas estandar en todas: id, uuid y auditoria.
--    Las FK de created_by/updated_by/deleted_by se agregan al final
--    (t_usuario aun no existe cuando se crean t_rol y t_usuario).
-- =====================================================================

create table if not exists t_rol (
  id          bigint generated always as identity primary key,
  uuid        uuid        not null default gen_random_uuid() unique,
  codigo      varchar(20) not null,
  nombre      varchar(60) not null,
  descripcion varchar(200) not null default '',
  created_at  timestamptz not null default now(), created_by bigint,
  updated_at  timestamptz not null default now(), updated_by bigint,
  deleted_at  timestamptz,                        deleted_by bigint
);

create table if not exists t_usuario (
  id              bigint generated always as identity primary key,
  uuid            uuid         not null default gen_random_uuid() unique,
  rol_id          bigint       not null references t_rol(id) on delete restrict,
  nombre          varchar(120) not null,
  email           varchar(255) not null,
  password_hash   varchar(255) not null,
  activo          boolean      not null default true,
  ultimo_login_at timestamptz,
  created_at      timestamptz  not null default now(), created_by bigint,
  updated_at      timestamptz  not null default now(), updated_by bigint,
  deleted_at      timestamptz,                         deleted_by bigint
);

create table if not exists t_categoria (
  id          bigint generated always as identity primary key,
  uuid        uuid         not null default gen_random_uuid() unique,
  nombre      varchar(60)  not null,
  descripcion varchar(200) not null default '',
  created_at  timestamptz  not null default now(), created_by bigint,
  updated_at  timestamptz  not null default now(), updated_by bigint,
  deleted_at  timestamptz,                         deleted_by bigint
);

create table if not exists t_producto (
  id           bigint generated always as identity primary key,
  uuid         uuid          not null default gen_random_uuid() unique,
  categoria_id bigint        not null references t_categoria(id) on delete restrict,
  sku          varchar(40)   not null,
  nombre       varchar(160)  not null,
  descripcion  varchar(500)  not null default '',
  precio       numeric(12,2) not null check (precio > 0),
  stock        integer       not null default 0 check (stock >= 0),
  activo       boolean       not null default true,
  created_at   timestamptz   not null default now(), created_by bigint,
  updated_at   timestamptz   not null default now(), updated_by bigint,
  deleted_at   timestamptz,                          deleted_by bigint
);

create table if not exists t_pedido (
  id                 bigint generated always as identity primary key,
  uuid               uuid          not null default gen_random_uuid() unique,
  numero             varchar(40)   not null,
  usuario_id         bigint        not null references t_usuario(id) on delete restrict,
  estado             varchar(20)   not null default 'PAGADO' check (estado in ('PAGADO','ANULADO')),
  subtotal           numeric(12,2) not null check (subtotal >= 0),
  tasa_impuesto      numeric(5,4)  not null check (tasa_impuesto >= 0),
  impuesto           numeric(12,2) not null check (impuesto >= 0),
  total              numeric(12,2) not null check (total >= 0),
  motor_recibo       varchar(10)   not null default 'v2' check (motor_recibo in ('v1','v2')),
  tiempo_proceso_seg numeric(10,3) not null default 0,
  created_at         timestamptz   not null default now(), created_by bigint,
  updated_at         timestamptz   not null default now(), updated_by bigint,
  deleted_at         timestamptz,                          deleted_by bigint
);

create table if not exists t_pedido_detalle (
  id              bigint generated always as identity primary key,
  uuid            uuid          not null default gen_random_uuid() unique,
  pedido_id       bigint        not null references t_pedido(id) on delete restrict,
  producto_id     bigint        not null references t_producto(id) on delete restrict,
  nombre_producto varchar(160)  not null,
  precio_unitario numeric(12,2) not null check (precio_unitario >= 0),
  cantidad        integer       not null check (cantidad > 0),
  total_linea     numeric(12,2) not null check (total_linea >= 0),
  created_at      timestamptz   not null default now(), created_by bigint,
  updated_at      timestamptz   not null default now(), updated_by bigint,
  deleted_at      timestamptz,                          deleted_by bigint
);

create table if not exists t_movimiento_inventario (
  id               bigint generated always as identity primary key,
  uuid             uuid         not null default gen_random_uuid() unique,
  producto_id      bigint       not null references t_producto(id) on delete restrict,
  pedido_id        bigint       references t_pedido(id) on delete restrict,
  tipo             varchar(20)  not null check (tipo in ('VENTA','INGRESO','AJUSTE','ANULACION')),
  cantidad         integer      not null check (cantidad <> 0),
  stock_resultante integer      not null check (stock_resultante >= 0),
  motivo           varchar(200) not null default '',
  created_at       timestamptz  not null default now(), created_by bigint,
  updated_at       timestamptz  not null default now(), updated_by bigint,
  deleted_at       timestamptz,                         deleted_by bigint
);

create table if not exists t_auditoria (
  id            bigint generated always as identity primary key,
  uuid          uuid        not null default gen_random_uuid() unique,
  tabla         varchar(60) not null,
  registro_uuid uuid        not null,
  accion        varchar(10) not null check (accion in ('INSERT','UPDATE','DELETE')),
  datos_antes   jsonb,
  datos_despues jsonb,
  usuario_id    bigint,
  created_at    timestamptz not null default now(), created_by bigint,
  updated_at    timestamptz not null default now(), updated_by bigint,
  deleted_at    timestamptz,                        deleted_by bigint
);

create table if not exists t_parametro (
  id          bigint generated always as identity primary key,
  uuid        uuid         not null default gen_random_uuid() unique,
  clave       varchar(60)  not null,
  valor       varchar(200) not null,
  descripcion varchar(200) not null default '',
  created_at  timestamptz  not null default now(), created_by bigint,
  updated_at  timestamptz  not null default now(), updated_by bigint,
  deleted_at  timestamptz,                         deleted_by bigint
);

-- =====================================================================
-- 2. Claves foraneas de auditoria (created_by / updated_by / deleted_by -> t_usuario)
-- =====================================================================
do $$
declare
  t text; c text;
begin
  foreach t in array array['t_rol','t_usuario','t_categoria','t_producto','t_pedido',
                           't_pedido_detalle','t_movimiento_inventario','t_auditoria','t_parametro']
  loop
    foreach c in array array['created_by','updated_by','deleted_by'] loop
      if not exists (select 1 from pg_constraint where conname = format('fk_%s_%s', t, c)) then
        execute format('alter table %I add constraint %I foreign key (%I) references t_usuario(id) on delete restrict',
                       t, format('fk_%s_%s', t, c), c);
      end if;
    end loop;
  end loop;
end $$;

-- =====================================================================
-- 3. Indices. Unicos parciales: solo cuentan los registros vigentes (no borrados).
-- =====================================================================
create unique index if not exists ux_t_rol_codigo        on t_rol (codigo)        where deleted_at is null;
create unique index if not exists ux_t_usuario_email     on t_usuario (lower(email)) where deleted_at is null;
create unique index if not exists ux_t_categoria_nombre  on t_categoria (lower(nombre)) where deleted_at is null;
create unique index if not exists ux_t_producto_sku      on t_producto (sku)      where deleted_at is null;
create unique index if not exists ux_t_pedido_numero     on t_pedido (numero)     where deleted_at is null;
create unique index if not exists ux_t_parametro_clave   on t_parametro (clave)  where deleted_at is null;

create index if not exists ix_t_usuario_rol              on t_usuario (rol_id);
create index if not exists ix_t_producto_categoria       on t_producto (categoria_id);
create index if not exists ix_t_pedido_usuario_fecha     on t_pedido (usuario_id, created_at desc);
create index if not exists ix_t_pedido_fecha             on t_pedido (created_at desc);
create index if not exists ix_t_pedido_detalle_pedido    on t_pedido_detalle (pedido_id);
create index if not exists ix_t_pedido_detalle_producto  on t_pedido_detalle (producto_id);
create index if not exists ix_t_mov_inv_producto         on t_movimiento_inventario (producto_id, created_at desc);
create index if not exists ix_t_mov_inv_pedido           on t_movimiento_inventario (pedido_id);
create index if not exists ix_t_auditoria_registro       on t_auditoria (tabla, registro_uuid);

-- =====================================================================
-- 4. Triggers de auditoria
--    El backend informa el usuario de cada transaccion con:
--      select set_config('app.user_id', '<id>', true);
-- =====================================================================
create or replace function fn_t_fijar_auditoria() returns trigger
language plpgsql as $$
declare
  v_user bigint := nullif(current_setting('app.user_id', true), '')::bigint;
begin
  if tg_op = 'INSERT' then
    new.created_at := now();
    new.created_by := coalesce(new.created_by, v_user);
    new.updated_at := now();
    new.updated_by := coalesce(new.updated_by, v_user);
  else
    -- Estas columnas no se pueden modificar a mano.
    new.id         := old.id;
    new.uuid       := old.uuid;
    new.created_at := old.created_at;
    new.created_by := old.created_by;
    new.updated_at := now();
    new.updated_by := coalesce(v_user, new.updated_by);
    if new.deleted_at is not null and old.deleted_at is null then
      new.deleted_by := coalesce(new.deleted_by, v_user);
    end if;
  end if;
  return new;
end $$;

create or replace function fn_t_registrar_auditoria() returns trigger
language plpgsql as $$
declare
  v_user bigint := nullif(current_setting('app.user_id', true), '')::bigint;
begin
  if tg_op = 'INSERT' then
    insert into t_auditoria (tabla, registro_uuid, accion, datos_antes, datos_despues, usuario_id, created_by)
    values (tg_table_name, new.uuid, 'INSERT', null, to_jsonb(new) - 'password_hash', v_user, v_user);
    return new;
  elsif tg_op = 'UPDATE' then
    insert into t_auditoria (tabla, registro_uuid, accion, datos_antes, datos_despues, usuario_id, created_by)
    values (tg_table_name, new.uuid, 'UPDATE', to_jsonb(old) - 'password_hash', to_jsonb(new) - 'password_hash', v_user, v_user);
    return new;
  else
    insert into t_auditoria (tabla, registro_uuid, accion, datos_antes, datos_despues, usuario_id, created_by)
    values (tg_table_name, old.uuid, 'DELETE', to_jsonb(old) - 'password_hash', null, v_user, v_user);
    return old;
  end if;
end $$;

do $$
declare t text;
begin
  foreach t in array array['t_rol','t_usuario','t_categoria','t_producto','t_pedido',
                           't_pedido_detalle','t_movimiento_inventario','t_auditoria','t_parametro']
  loop
    execute format('drop trigger if exists trg_%s_auditoria_cols on %I', t, t);
    execute format('create trigger trg_%s_auditoria_cols before insert or update on %I
                    for each row execute function fn_t_fijar_auditoria()', t, t);
    if t <> 't_auditoria' then  -- la tabla de auditoria no se audita a si misma
      execute format('drop trigger if exists trg_%s_registro on %I', t, t);
      execute format('create trigger trg_%s_registro after insert or update or delete on %I
                      for each row execute function fn_t_registrar_auditoria()', t, t);
    end if;
  end loop;
end $$;

-- =====================================================================
-- 5. Seguridad (Supabase expone el esquema public por API REST):
--    RLS activado SIN politicas + sin permisos para anon/authenticated.
--    Solo entra el backend con la conexion directa a Postgres.
-- =====================================================================
do $$
declare t text;
begin
  foreach t in array array['t_rol','t_usuario','t_categoria','t_producto','t_pedido',
                           't_pedido_detalle','t_movimiento_inventario','t_auditoria','t_parametro']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('revoke all on %I from anon, authenticated', t);
  end loop;
end $$;

-- =====================================================================
-- 6. Datos base
-- =====================================================================
insert into t_rol (codigo, nombre, descripcion) values
  ('ADMIN',   'Administrador', 'Gestiona ventas e inventario'),
  ('CLIENTE', 'Cliente',       'Compra en la tienda')
on conflict (codigo) where deleted_at is null do nothing;

insert into t_parametro (clave, valor, descripcion) values
  ('TASA_IVA',      '0.21', 'Tasa de impuesto aplicada a los pedidos'),
  ('MOTOR_RECIBO',  'v2',   'Motor de calculo del recibo: v1 (lento) o v2 (rapido)')
on conflict (clave) where deleted_at is null do nothing;
