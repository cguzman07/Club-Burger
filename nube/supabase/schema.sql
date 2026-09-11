-- Club Burger · esquema Supabase
-- Pegar en: SQL Editor → New query → Run
--
-- panel_estado / productos / caja: foto en vivo del computador.
-- libro_ventas: contabilidad permanente. No se borra aunque se borre datos_pos.db.
-- El PC (service_role) escribe. El celular autenticado solo lee reportes.

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

create table if not exists libro_ventas (
  id uuid primary key default gen_random_uuid(),
  clave_local text not null unique,
  fecha_hora timestamptz,
  fecha_dia date not null,
  fecha_texto text,
  producto_id bigint,
  nombre_producto text not null default '',
  cantidad int not null default 0,
  precio_unitario numeric not null default 0,
  total numeric not null default 0,
  metodo_pago text not null default '',
  id_caja bigint,
  nota text,
  origen text not null default 'pos',
  created_at timestamptz not null default now()
);

create index if not exists libro_ventas_dia_idx on libro_ventas (fecha_dia);
create index if not exists libro_ventas_metodo_idx on libro_ventas (fecha_dia, metodo_pago);

insert into panel_estado (id, payload, pc_en_linea)
values (1, '{}'::jsonb, false)
on conflict (id) do nothing;

alter table panel_estado enable row level security;
alter table productos enable row level security;
alter table caja enable row level security;
alter table ventas enable row level security;
alter table pedidos_remotos enable row level security;
alter table libro_ventas enable row level security;

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

drop policy if exists "dueño lee libro" on libro_ventas;
create policy "dueño lee libro"
  on libro_ventas for select
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

create or replace function reporte_ventas(p_desde date, p_hasta date)
returns jsonb
language sql
stable
security invoker
as $$
  with base as (
    select *
    from libro_ventas
    where fecha_dia >= p_desde
      and fecha_dia <= p_hasta
  ),
  tot as (
    select
      coalesce(round(sum(total), 2), 0) as total,
      coalesce(sum(cantidad), 0) as items,
      count(*)::int as lineas,
      coalesce(round(sum(total) filter (where lower(coalesce(metodo_pago, '')) = 'efectivo'), 2), 0) as efectivo
    from base
  ),
  met as (
    select
      coalesce(nullif(trim(metodo_pago), ''), 'Sin método') as metodo,
      round(sum(total), 2) as tot
    from base
    group by coalesce(nullif(trim(metodo_pago), ''), 'Sin método')
  ),
  dia as (
    select
      fecha_dia,
      round(sum(total), 2) as total,
      sum(cantidad) as items,
      count(*) as lineas
    from base
    group by fecha_dia
  ),
  prod as (
    select
      coalesce(nullif(trim(nombre_producto), ''), 'Producto') as nombre,
      sum(cantidad) as cantidad,
      round(sum(total), 2) as total
    from base
    group by coalesce(nullif(trim(nombre_producto), ''), 'Producto')
    order by round(sum(total), 2) desc
    limit 30
  )
  select jsonb_build_object(
    'desde', p_desde,
    'hasta', p_hasta,
    'total', tot.total,
    'items', tot.items,
    'lineas', tot.lineas,
    'efectivo', tot.efectivo,
    'otros_medios', round(tot.total - tot.efectivo, 2),
    'por_metodo', coalesce((select jsonb_object_agg(metodo, tot) from met), '{}'::jsonb),
    'por_dia', coalesce(
      (
        select jsonb_agg(
          jsonb_build_object(
            'fecha', fecha_dia,
            'total', total,
            'items', items,
            'lineas', lineas
          )
          order by fecha_dia
        )
        from dia
      ),
      '[]'::jsonb
    ),
    'por_producto', coalesce(
      (
        select jsonb_agg(
          jsonb_build_object(
            'nombre', nombre,
            'cantidad', cantidad,
            'total', total
          )
        )
        from prod
      ),
      '[]'::jsonb
    )
  )
  from tot;
$$;

grant execute on function reporte_ventas(date, date) to authenticated;
grant execute on function reporte_ventas(date, date) to service_role;

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
