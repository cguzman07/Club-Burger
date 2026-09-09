-- Club Burger · esquema Supabase
-- Pegar en: SQL Editor → New query → Run
-- El computador del restaurante es la fuente de la caja.
-- El celular (Netlify) lee en vivo y envía pedidos remotos.

create table if not exists panel_estado (
  id int primary key default 1 check (id = 1),
  payload jsonb not null default '{}'::jsonb,
  pc_en_linea boolean not null default false,
  impresora text,
  updated_at timestamptz not null default now()
);

create table if not exists productos (
  id bigint primary key,
  nombre text,
  categoria text,
  precio numeric,
  stock int,
  stock_inicial int,
  updated_at timestamptz not null default now()
);

create table if not exists caja (
  id bigint primary key,
  usuario text,
  fecha text,
  hora_apertura text,
  capital_inicial numeric,
  detalle_capital text,
  hora_cierre text,
  capital_final numeric,
  total_ventas numeric,
  fecha_cierre text,
  updated_at timestamptz not null default now()
);

create table if not exists ventas (
  id bigint primary key,
  fecha text,
  producto_id bigint,
  nombre_producto text,
  cantidad int,
  precio_unitario numeric,
  total numeric,
  metodo_pago text,
  id_caja bigint,
  nota text,
  updated_at timestamptz not null default now()
);

create table if not exists pedidos_remotos (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  created_by uuid,
  items jsonb not null,
  metodo_pago text not null,
  recibido numeric,
  nota text,
  estado text not null default 'pendiente'
    check (estado in ('pendiente', 'procesando', 'impreso', 'registrado', 'error')),
  factura int,
  error text,
  total numeric
);

insert into panel_estado (id, payload, pc_en_linea)
values (1, '{}'::jsonb, false)
on conflict (id) do nothing;

alter table panel_estado enable row level security;
alter table productos enable row level security;
alter table caja enable row level security;
alter table ventas enable row level security;
alter table pedidos_remotos enable row level security;

drop policy if exists "dueño lee estado" on panel_estado;
create policy "dueño lee estado"
  on panel_estado for select
  to authenticated
  using (true);

drop policy if exists "dueño lee productos" on productos;
create policy "dueño lee productos"
  on productos for select
  to authenticated
  using (true);

drop policy if exists "dueño lee caja" on caja;
create policy "dueño lee caja"
  on caja for select
  to authenticated
  using (true);

drop policy if exists "dueño lee ventas" on ventas;
create policy "dueño lee ventas"
  on ventas for select
  to authenticated
  using (true);

drop policy if exists "dueño lee pedidos" on pedidos_remotos;
create policy "dueño lee pedidos"
  on pedidos_remotos for select
  to authenticated
  using (true);

drop policy if exists "dueño crea pedidos" on pedidos_remotos;
create policy "dueño crea pedidos"
  on pedidos_remotos for insert
  to authenticated
  with check (created_by is null or created_by = auth.uid());

-- Realtime para el celular (si ya estaba agregada, se ignora)
do $$
begin
  alter publication supabase_realtime add table panel_estado;
exception when others then null;
end $$;
do $$
begin
  alter publication supabase_realtime add table pedidos_remotos;
exception when others then null;
end $$;
