const dinero = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

const cfg = window.CLUB_BURGER_NUBE || {};
const loginEl = document.getElementById("login");
const panelEl = document.getElementById("panel");
const loginError = document.getElementById("login-error");
const metodosEl = document.getElementById("metodos");
const topEl = document.getElementById("top");
const feedEl = document.getElementById("feed");
const invListaEl = document.getElementById("inv-lista");
const filtrosEl = document.getElementById("filtros");
const alertaStockEl = document.getElementById("alerta-stock");
const buscarEl = document.getElementById("buscar");
const pcBanner = document.getElementById("pc-banner");

let supabase = null;
let user = null;
let channel = null;
let poll = null;
let ultimaFirma = "";
let ultimoEstado = null;
let tabActual = "caja";
let diaReporte = "";
let periodoReporte = "dia";
let reporteNube = null;
let filtroInv = "todos";
let inventario = { productos: [], categorias: [], umbral: 5, atencion: 0, agotados: 0, bajos: 0, ok: 0, total: 0 };
let carrito = {};
let metodoPago = "Efectivo";
let metodosPago = ["Efectivo", "Nequi", "Daviplata", "Transferencia", "Tarjeta"];
let puedeVender = false;
let pcEnLinea = false;
let cobrando = false;

const POS_DOMINIO = "usuarios.clubburger";
const POS_CLAVE_EXTRA = "#cb";

function credencialesPos(usuario, contrasena) {
  const u = (usuario || "").trim();
  const clave = contrasena || "";
  const slug = u.toLowerCase().replace(/[^a-z0-9._-]/g, "") || "usuario";
  const emailPos = `${slug}@${POS_DOMINIO}`;
  const password = clave.endsWith(POS_CLAVE_EXTRA) ? clave : `${clave}${POS_CLAVE_EXTRA}`;
  if (u.includes("@") && !u.toLowerCase().endsWith(`@${POS_DOMINIO}`)) {
    return { email: u, password: clave, fallback: { email: emailPos, password } };
  }
  return { email: emailPos, password };
}

function crearCliente() {
  if (!window.supabase || typeof window.supabase.createClient !== "function") {
    throw new Error("No se cargó la app. Cierra Chrome o Safari, entra otra vez a clubburger.app y usa datos o WiFi.");
  }
  if (!cfg.url || !cfg.anonKey) {
    throw new Error("Falta configurar Supabase en Netlify (SUPABASE_URL y SUPABASE_ANON_KEY).");
  }
  return window.supabase.createClient(cfg.url, cfg.anonKey);
}

function sesionDeAuth(persona) {
  const meta = persona?.user_metadata || {};
  const rol = String(meta.rol || "").toLowerCase();
  const admins = new Set(["admin", "administrador", "dueño", "dueno", "owner", "jefe"]);
  if (meta.pos) {
    return { usuario: meta.usuario || "—", rol: meta.rol || "cajero", es_admin: admins.has(rol) };
  }
  return { usuario: persona?.email || "—", rol: "admin", es_admin: true };
}

function aplicarPoliticas(sesion) {
  const admin = Boolean(sesion?.es_admin);
  const btn = document.querySelector('#tabs button[data-tab="reporte"]');
  if (btn) btn.hidden = !admin;
  const etiqueta = document.getElementById("quien-sesion");
  if (etiqueta) {
    etiqueta.textContent = sesion?.usuario ? `${sesion.usuario}${admin ? " · admin" : " · cajero"}` : "";
  }
  if (!admin && tabActual === "reporte") cambiarTab("caja");
}

function esc(texto) {
  return String(texto ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function mensajeLogin(err) {
  const t = String(err?.message || err || "");
  if (/invalid login|invalid_credentials/i.test(t)) {
    return "Usuario o contraseña incorrectos. Escríbelos igual que en el computador, por ejemplo admin.";
  }
  if (/failed to fetch|networkerror|load failed/i.test(t)) {
    return "No se pudo conectar. Revisa el internet del celular e intenta de nuevo.";
  }
  return t || "No se pudo entrar";
}

document.getElementById("login-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const boton = ev.target.querySelector("button[type='submit']");
  loginError.hidden = true;
  if (boton) {
    boton.disabled = true;
    boton.textContent = "Entrando…";
  }
  try {
    supabase = crearCliente();
    const usuario = document.getElementById("usuario").value;
    const contrasena = document.getElementById("contrasena").value;
    const creds = credencialesPos(usuario, contrasena);
    let resultado = await supabase.auth.signInWithPassword({
      email: creds.email,
      password: creds.password,
    });
    if (resultado.error && creds.fallback) {
      resultado = await supabase.auth.signInWithPassword(creds.fallback);
    }
    if (resultado.error) throw resultado.error;
    user = resultado.data.user;
    mostrarPanel();
  } catch (err) {
    loginError.hidden = false;
    loginError.textContent = mensajeLogin(err);
  } finally {
    if (boton) {
      boton.disabled = false;
      boton.textContent = "Entrar";
    }
  }
});

document.getElementById("salir").addEventListener("click", async () => {
  if (channel) supabase.removeChannel(channel);
  clearInterval(poll);
  if (supabase) await supabase.auth.signOut();
  user = null;
  loginEl.hidden = false;
  panelEl.hidden = true;
});

document.getElementById("tabs").addEventListener("click", (ev) => {
  const boton = ev.target.closest("button[data-tab]");
  if (boton) cambiarTab(boton.dataset.tab);
});
alertaStockEl.addEventListener("click", () => cambiarTab("inventario"));
buscarEl.addEventListener("input", () => pintarInventario());
filtrosEl.addEventListener("click", (ev) => {
  const boton = ev.target.closest("button[data-filtro]");
  if (!boton) return;
  filtroInv = boton.dataset.filtro;
  pintarFiltros();
  pintarInventario();
});

function cambiarTab(tab) {
  tabActual = tab;
  ["caja", "inventario", "vender", "reporte"].forEach((id) => {
    const vista = document.getElementById(`vista-${id}`);
    if (vista) vista.hidden = tab !== id;
  });
  document.querySelectorAll("#tabs button").forEach((b) => {
    b.classList.toggle("activo", b.dataset.tab === tab);
  });
  if (tab === "reporte") cargarReporteNube();
}

function mostrarPanel() {
  loginEl.hidden = true;
  panelEl.hidden = false;
  conectar();
  cargarEstado();
}

function setLive(ok, texto) {
  const el = document.getElementById("live-label");
  el.textContent = texto || (ok ? "En vivo" : "Sin conexión");
  el.classList.toggle("off", !ok);
}

function pcReciente(iso) {
  if (!iso) return false;
  const t = new Date(iso).getTime();
  return Number.isFinite(t) && Date.now() - t < 45000;
}

function aplicarFila(row) {
  if (!row) return;
  pcEnLinea = Boolean(row.pc_en_linea) && pcReciente(row.updated_at);
  const equipo = row.payload?.equipo ? String(row.payload.equipo) : "";
  setLive(pcEnLinea, pcEnLinea ? (equipo ? `En vivo · ${equipo}` : "En vivo") : "PC apagado");
  if (!pcEnLinea) {
    pcBanner.hidden = false;
    pcBanner.innerHTML =
      "<strong>El computador del restaurante no está en línea</strong><span class=\"muted\">Abre Club Burger en el PC del negocio (el panel arranca solo). No hace falta el otro portátil. Luego espera unos segundos y recarga.</span>";
  } else {
    pcBanner.hidden = true;
  }
  if (row.payload) pintar(row.payload);
}

async function cargarEstado() {
  const { data, error } = await supabase.from("panel_estado").select("*").eq("id", 1).maybeSingle();
  if (error) {
    setLive(false, "Error");
    return;
  }
  aplicarFila(data);
}

function conectar() {
  if (channel) supabase.removeChannel(channel);
  channel = supabase
    .channel("club-burger")
    .on(
      "postgres_changes",
      { event: "*", schema: "public", table: "panel_estado" },
      (payload) => aplicarFila(payload.new)
    )
    .subscribe();
  clearInterval(poll);
  poll = setInterval(cargarEstado, 4000);
}

function pintar(estado) {
  if (!estado) return;
  ultimoEstado = estado;
  const cambio = estado.firma && estado.firma !== ultimaFirma;
  ultimaFirma = estado.firma || "";
  const caja = estado.caja;
  const card = document.getElementById("caja-card");
  const badge = document.getElementById("caja-estado");
  const abierta = Boolean(caja && caja.abierta);
  card.classList.toggle("abierta", abierta);
  card.classList.toggle("cerrada", !abierta);
  badge.textContent = abierta ? "Caja abierta" : "Caja cerrada";
  badge.className = `badge ${abierta ? "ok" : "off"}`;
  document.getElementById("quien").textContent = abierta
    ? `Atiende ${caja.usuario}`
    : caja
      ? `Última caja: ${caja.usuario}`
      : "Nadie atendiendo";
  document.getElementById("caja-desde").textContent = caja
    ? abierta
      ? `Desde ${caja.desde}`
      : `Cerrada ${caja.hora_cierre || ""}`.trim()
    : "Aún no hay movimientos de caja";
  document.getElementById("capital").textContent = caja
    ? `Capital inicial ${dinero.format(caja.capital_inicial || 0)}`
    : "";
  const totalEl = document.getElementById("total-caja");
  totalEl.textContent = dinero.format(estado.ventas_caja?.total || 0);
  if (cambio) {
    totalEl.classList.remove("flash");
    void totalEl.offsetWidth;
    totalEl.classList.add("flash");
  }
  const items = estado.ventas_caja?.items || 0;
  document.getElementById("items-caja").textContent = items
    ? `${items} ítem${items === 1 ? "" : "s"} en esta caja`
    : "Sin ventas en esta caja";
  inventario = estado.inventario || inventario;
  metodosPago = estado.metodos_pago || metodosPago;
  document.getElementById("total-hoy").textContent = dinero.format(estado.ventas_hoy?.total || 0);
  document.getElementById("items-hoy").textContent = String(estado.ventas_hoy?.items || 0);
  document.getElementById("metodos-titulo").textContent = abierta
    ? "Por método de pago · caja actual"
    : "Por método de pago · última caja";
  pintarMetodos(mapaMetodos(estado.ventas_caja?.por_metodo));
  pintarReporteLocal(estado);
  aplicarPoliticas(sesionDeAuth(user));
  pintarLista(topEl, estado.top_productos || [], (p) => ({
    titulo: p.nombre,
    sub: `${p.cantidad} vendidos`,
    valor: dinero.format(p.total),
  }));
  pintarLista(feedEl, estado.ultimas_ventas || [], (v) => ({
    titulo: `${v.cantidad}× ${v.producto}`,
    sub: `${v.fecha_corta} · ${v.metodo}`,
    valor: dinero.format(v.total),
  }));
  puedeVender = Boolean(estado.puede_vender) && pcEnLinea;
  pintarAlertaStock();
  pintarResumenInv();
  pintarFiltros();
  pintarInventario();
  pintarVender();
  document.getElementById("pie").textContent = `Actualizado ${estado.ahora || ""}`;
}

function pintarAlertaStock() {
  const n = inventario.atencion || 0;
  if (!n) {
    alertaStockEl.hidden = true;
    alertaStockEl.innerHTML = "";
    return;
  }
  const agotados = inventario.agotados || 0;
  const bajos = inventario.bajos || 0;
  alertaStockEl.hidden = false;
  alertaStockEl.classList.toggle("bajo", agotados === 0);
  alertaStockEl.innerHTML = `<strong>${n} producto${n === 1 ? "" : "s"} necesitan atención</strong>
    <span class="muted">${agotados} agotado${agotados === 1 ? "" : "s"} · ${bajos} bajo${bajos === 1 ? "" : "s"}</span>`;
}

function pintarResumenInv() {
  const total = inventario.total || 0;
  document.getElementById("inv-resumen").textContent = `${total} producto${total === 1 ? "" : "s"}`;
  document.getElementById("inv-umbral").textContent = `Alerta si quedan ${inventario.umbral ?? 5} o menos`;
  document.getElementById("n-agotados").textContent = String(inventario.agotados || 0);
  document.getElementById("n-bajos").textContent = String(inventario.bajos || 0);
  document.getElementById("n-ok").textContent = String(inventario.ok || 0);
  const badge = document.getElementById("inv-badge");
  const atencion = inventario.atencion || 0;
  badge.hidden = atencion === 0;
  badge.textContent = String(atencion);
}

function pintarFiltros() {
  const chips = [
    ["todos", "Todos"],
    ["agotado", "Agotados"],
    ["bajo", "Bajos"],
    ...(inventario.categorias || []).map((cat) => [`cat:${cat}`, cat]),
  ];
  filtrosEl.innerHTML = chips
    .map(
      ([id, etiqueta]) =>
        `<button type="button" data-filtro="${esc(id)}" class="${filtroInv === id ? "activo" : ""}">${esc(etiqueta)}</button>`
    )
    .join("");
}

function pintarInventario() {
  const q = (buscarEl.value || "").trim().toLowerCase();
  const items = (inventario.productos || []).filter((p) => {
    if (filtroInv === "agotado" && p.nivel !== "agotado") return false;
    if (filtroInv === "bajo" && p.nivel !== "bajo") return false;
    if (filtroInv.startsWith("cat:") && p.categoria !== filtroInv.slice(4)) return false;
    if (q && !`${p.nombre} ${p.categoria}`.toLowerCase().includes(q)) return false;
    return true;
  });
  if (!items.length) {
    invListaEl.innerHTML = '<p class="vacio">No hay productos con ese filtro</p>';
    return;
  }
  const etiqueta = { agotado: "Agotado", bajo: "Bajo", ok: "Ok" };
  invListaEl.innerHTML = items
    .map((p) => {
      const max = p.stock_inicial > 0 ? p.stock_inicial : Math.max(p.stock, 1);
      const ancho = Math.max(4, Math.min(100, (p.stock / max) * 100));
      const extra = [];
      if (p.stock_inicial) extra.push(`de ${p.stock_inicial}`);
      if (p.vendido_hoy) extra.push(`hoy ${p.vendido_hoy}`);
      return `<article class="inv-item ${p.nivel}">
        <div class="inv-top">
          <div>
            <div class="prod">${esc(p.nombre)}</div>
            <div class="muted mini">${esc(p.categoria)} · ${dinero.format(p.precio)}</div>
          </div>
          <div class="der">
            <div class="inv-stock">${p.stock}</div>
            <span class="badge ${p.nivel === "ok" ? "ok" : p.nivel === "bajo" ? "warn" : "off"}">${etiqueta[p.nivel]}</span>
          </div>
        </div>
        <div class="barra"><i style="width:${ancho}%"></i></div>
        <div class="muted mini">${extra.join(" · ") || "Sin stock inicial"}</div>
      </article>`;
    })
    .join("");
}

function mapaMetodos(mapa) {
  const out = {};
  for (const m of metodosPago) out[m] = 0;
  for (const [nombre, valor] of Object.entries(mapa || {})) out[nombre] = Number(valor || 0);
  return out;
}

function pintarMetodos(mapa, destino) {
  const el = destino || metodosEl;
  const entradas = Object.entries(mapa || {});
  if (!entradas.length) {
    el.innerHTML = '<p class="vacio">Todavía no hay cobros</p>';
    return;
  }
  const max = Math.max(...entradas.map(([, n]) => n), 1);
  el.innerHTML = entradas
    .map(
      ([nombre, valor]) => `
      <article class="metodo"><div>
        <span>${nombre}</span>
        <strong>${dinero.format(valor)}</strong>
        <div class="barra"><i style="width:${Math.max(8, (valor / max) * 100)}%"></i></div>
      </div></article>`
    )
    .join("");
}

function isoLocal(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function parseIso(texto) {
  const m = String(texto || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return null;
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

function rangoPeriodoJS() {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const elegido = parseIso(document.getElementById("rep-desde")?.value) || hoy;
  const hastaSel = parseIso(document.getElementById("rep-hasta")?.value);
  if (periodoReporte === "semana") {
    const inicio = new Date(elegido);
    inicio.setDate(elegido.getDate() - ((elegido.getDay() + 6) % 7));
    const fin = new Date(inicio);
    fin.setDate(inicio.getDate() + 6);
    return { desde: isoLocal(inicio), hasta: isoLocal(fin), etiqueta: `Semana del ${inicio.getDate()} al ${fin.getDate()}` };
  }
  if (periodoReporte === "mes") {
    const inicio = new Date(elegido.getFullYear(), elegido.getMonth(), 1);
    const fin = new Date(elegido.getFullYear(), elegido.getMonth() + 1, 0);
    const meses = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
    return { desde: isoLocal(inicio), hasta: isoLocal(fin), etiqueta: `${meses[inicio.getMonth()]} ${inicio.getFullYear()}` };
  }
  if (periodoReporte === "anio") {
    const inicio = new Date(elegido.getFullYear(), 0, 1);
    const fin = new Date(elegido.getFullYear(), 11, 31);
    return { desde: isoLocal(inicio), hasta: isoLocal(fin), etiqueta: String(inicio.getFullYear()) };
  }
  if (periodoReporte === "rango") {
    let a = elegido;
    let b = hastaSel || elegido;
    if (a > b) [a, b] = [b, a];
    return { desde: isoLocal(a), hasta: isoLocal(b), etiqueta: `${isoLocal(a)} → ${isoLocal(b)}` };
  }
  const dia = periodoReporte === "dia" && diaReporte ? parseIso(diaReporte) || elegido : elegido;
  const esHoy = isoLocal(dia) === isoLocal(hoy);
  return { desde: isoLocal(dia), hasta: isoLocal(dia), etiqueta: esHoy ? "Hoy" : isoLocal(dia) };
}

async function cargarReporteNube() {
  if (!supabase) return;
  const fechaEl = document.getElementById("rep-fecha");
  if (fechaEl) fechaEl.textContent = "Cargando…";
  const rango = rangoPeriodoJS();
  try {
    const { data, error } = await supabase.rpc("reporte_ventas", {
      p_desde: rango.desde,
      p_hasta: rango.hasta,
    });
    if (error) throw error;
    const reporte = data && typeof data === "object" ? data : {};
    reporte.etiqueta = rango.etiqueta;
    reporte.fuente = "nube";
    reporteNube = reporte;
    pintarReporteNube(reporte);
    if (ultimoEstado) pintarReporteLocal(ultimoEstado);
  } catch (err) {
    if (fechaEl) {
      fechaEl.textContent = /schema cache|does not exist|libro_ventas/i.test(String(err.message || err))
        ? "Falta crear el libro en Supabase (schema.sql)"
        : err.message || "No se pudo cargar el reporte";
    }
  }
}

function pintarReporteNube(data) {
  if (!data) return;
  document.getElementById("rep-total").textContent = dinero.format(data.total || 0);
  document.getElementById("rep-fecha").textContent = data.etiqueta || "—";
  document.getElementById("rep-efectivo").textContent = dinero.format(data.efectivo || 0);
  document.getElementById("rep-otros").textContent = dinero.format(data.otros_medios || 0);
  const items = data.items || 0;
  const lineas = data.lineas || 0;
  document.getElementById("rep-items").textContent = items
    ? `${items} ítem${items === 1 ? "" : "s"} · ${lineas} línea${lineas === 1 ? "" : "s"} · nube`
    : "Sin ventas en ese período";
  const aviso = document.getElementById("rep-aviso");
  if (aviso) {
    aviso.hidden = !data.aviso;
    aviso.textContent = data.aviso || "";
  }
  pintarMetodos(mapaMetodos(data.por_metodo), document.getElementById("rep-metodos"));
  const prodEl = document.getElementById("rep-productos");
  const diaEl = document.getElementById("rep-por-dia");
  if (prodEl) {
    pintarLista(prodEl, data.por_producto || [], (p) => ({
      titulo: p.nombre,
      sub: `${p.cantidad} vendidos`,
      valor: dinero.format(p.total),
    }));
  }
  if (diaEl) {
    pintarLista(diaEl, data.por_dia || [], (d) => ({
      titulo: d.fecha,
      sub: `${d.items || 0} ítems`,
      valor: dinero.format(d.total),
    }));
  }
}

function pintarReporte(estado) {
  pintarReporteLocal(estado);
}

function pintarReporteLocal(estado) {
  const reporte = estado?.reporte;
  const diasEl = document.getElementById("rep-dias");
  if (!diasEl) return;
  const mostrarDias = periodoReporte === "dia";
  diasEl.hidden = !mostrarDias;
  const dias = reporte?.dias || [];
  if (mostrarDias && dias.length) {
    if (!diaReporte || !dias.some((d) => d.fecha === diaReporte)) {
      diaReporte = reporte?.hoy?.fecha || dias[0]?.fecha || "";
    }
    diasEl.innerHTML = dias
      .slice(0, 14)
      .map(
        (d) =>
          `<button type="button" data-dia="${esc(d.fecha)}" class="${d.fecha === diaReporte ? "activo" : ""}">${esc(
            d.es_hoy ? "Hoy" : d.etiqueta
          )}</button>`
      )
      .join("");
  }
  const dia = dias.find((d) => d.fecha === diaReporte) || reporte?.hoy;
  const sesionesEl = document.getElementById("rep-sesiones");
  const sesiones = periodoReporte === "dia" ? dia?.sesiones || [] : [];
  if (!sesionesEl) return;
  if (!sesiones.length) {
    sesionesEl.innerHTML =
      periodoReporte === "dia"
        ? '<p class="vacio">No hubo caja ese día</p>'
        : '<p class="vacio">El cuadre de caja se ve en el reporte del día</p>';
  } else {
    sesionesEl.innerHTML = sesiones
      .map((s) => {
        const avisos = [];
        if (s.alerta) avisos.push(s.alerta);
        if (s.capital_final != null && Math.abs(s.diferencia_efectivo || 0) >= 1) {
          avisos.push(
            `Efectivo contado ${dinero.format(s.capital_final)} vs esperado ${dinero.format(s.efectivo_esperado)} (capital inicial + ventas en efectivo).`
          );
        }
        return `<article class="cuadre fila-item">
          <div>
            <div class="prod">${s.abierta ? "Caja abierta" : "Caja cerrada"} · ${esc(s.usuario)}</div>
            <div class="muted mini">${esc(s.desde)}${s.hora_cierre ? ` → ${esc(s.hora_cierre)}` : ""}</div>
            <p class="muted mini">Capital inicial ${dinero.format(s.capital_inicial || 0)}</p>
            <p class="muted mini">Ventas ${dinero.format(s.ventas?.total || 0)}${s.total_pos != null ? ` · POS ${dinero.format(s.total_pos)}` : ""}</p>
            <p class="muted mini">Efectivo esperado ${dinero.format(s.efectivo_esperado || 0)}${s.capital_final != null ? ` · contado ${dinero.format(s.capital_final)}` : ""}</p>
            ${avisos.map((a) => `<p class="aviso">${esc(a)}</p>`).join("")}
            ${!avisos.length && !s.abierta ? '<p class="aviso ok">Ventas y cierre coinciden</p>' : ""}
          </div>
        </article>`;
      })
      .join("");
  }
  const fiados = periodoReporte === "dia" ? dia?.fiados || {} : {};
  const fiadosEl = document.getElementById("rep-fiados");
  if (!fiadosEl) return;
  if (!fiados.nuevos && !fiados.pagos && !fiados.pendiente) {
    fiadosEl.textContent = periodoReporte === "dia" ? "Sin fiados" : "Los fiados se ven en el reporte del día";
  } else {
    fiadosEl.textContent = `Nuevos ${dinero.format(fiados.monto_nuevo || 0)} · pagos ${dinero.format(fiados.monto_pagado || 0)} · pendiente ${dinero.format(fiados.pendiente || 0)}`;
  }
}

function pintarLista(el, items, mapear) {
  if (!el) return;
  if (!items || !items.length) {
    el.innerHTML = '<p class="vacio">Sin movimientos todavía</p>';
    return;
  }
  el.innerHTML = items
    .map((item) => {
      const fila = mapear(item);
      return `<article class="fila-item">
        <div><div class="prod">${fila.titulo}</div><div class="muted mini">${fila.sub}</div></div>
        <div class="der">${fila.valor}</div>
      </article>`;
    })
    .join("");
}

function productoPorId(id) {
  return (inventario.productos || []).find((p) => p.id === id);
}
function itemsCarrito() {
  return Object.entries(carrito)
    .map(([id, cantidad]) => {
      const prod = productoPorId(Number(id));
      if (!prod || cantidad < 1) return null;
      return { ...prod, cantidad, subtotal: prod.precio * cantidad };
    })
    .filter(Boolean);
}
function totalCarrito() {
  return itemsCarrito().reduce((acc, item) => acc + item.subtotal, 0);
}
function qtyCarrito() {
  return itemsCarrito().reduce((acc, item) => acc + item.cantidad, 0);
}
function setCantidad(id, cantidad) {
  const prod = productoPorId(id);
  if (!prod) return;
  const next = Math.max(0, Math.min(Math.max(0, prod.stock), cantidad));
  if (next <= 0) delete carrito[id];
  else carrito[id] = next;
  pintarVender();
}

function pintarVender() {
  const bloque = document.getElementById("vender-bloque");
  const ok = document.getElementById("vender-ok");
  const listo = puedeVender && pcEnLinea;
  if (!pcEnLinea) {
    bloque.hidden = false;
    bloque.textContent = "Enciende el panel en el computador del restaurante para imprimir.";
    ok.hidden = true;
  } else if (!puedeVender) {
    bloque.hidden = false;
    bloque.textContent = "Abre la caja en el computador para facturar desde el celular.";
    ok.hidden = true;
  } else {
    bloque.hidden = true;
    ok.hidden = false;
  }
  const items = itemsCarrito();
  const total = totalCarrito();
  const qty = qtyCarrito();
  document.getElementById("total-carrito").textContent = dinero.format(total);
  document.getElementById("carrito-resumen").textContent = qty
    ? `${qty} ítem${qty === 1 ? "" : "s"} · se imprime en el restaurante`
    : "Sin productos";
  const badge = document.getElementById("cart-badge");
  badge.hidden = qty === 0;
  badge.textContent = String(qty);
  const q = (document.getElementById("buscar-venta").value || "").trim().toLowerCase();
  const catalogo = (inventario.productos || []).filter((p) => p.stock > 0 && `${p.nombre} ${p.categoria}`.toLowerCase().includes(q));
  const catEl = document.getElementById("catalogo");
  catEl.innerHTML = catalogo.length
    ? catalogo
        .map((p) => {
          const n = carrito[p.id] || 0;
          return `<article class="prod-venta"><div>
            <div class="prod">${esc(p.nombre)}</div>
            <div class="muted mini">${esc(p.categoria)} · ${dinero.format(p.precio)} · ${p.stock} disp.</div>
          </div><div class="qty"><button type="button" data-add="${p.id}">+</button>${n ? `<span>${n}</span>` : ""}</div></article>`;
        })
        .join("")
    : '<p class="vacio">No hay productos disponibles</p>';
  document.getElementById("carrito").innerHTML = items
    .map(
      (p) => `<article class="cart-item"><div>
        <div class="prod">${esc(p.nombre)}</div>
        <div class="muted mini">${dinero.format(p.subtotal)}</div>
      </div><div class="qty">
        <button type="button" data-qty="${p.id}" data-delta="-1">−</button>
        <span>${p.cantidad}</span>
        <button type="button" data-qty="${p.id}" data-delta="1">+</button>
      </div></article>`
    )
    .join("");
  document.getElementById("metodos-venta").innerHTML = metodosPago
    .map((m) => `<button type="button" data-metodo="${esc(m)}" class="${metodoPago === m ? "activo" : ""}">${esc(m)}</button>`)
    .join("");
  document.getElementById("efectivo-box").hidden = metodoPago !== "Efectivo";
  actualizarCambio();
  document.getElementById("cobrar").disabled = !listo || !items.length || cobrando;
}

function actualizarCambio() {
  const total = totalCarrito();
  const rec = Number(String(document.getElementById("recibido").value || "").replace(/\D/g, ""));
  const el = document.getElementById("cambio");
  if (metodoPago !== "Efectivo" || !rec) {
    el.textContent = "Cambio: $ 0";
    return;
  }
  el.textContent = rec >= total ? `Cambio: ${dinero.format(rec - total)}` : "Recibido insuficiente";
}

async function esperarPedido(id) {
  for (let i = 0; i < 20; i += 1) {
    await new Promise((r) => setTimeout(r, 1000));
    const { data } = await supabase.from("pedidos_remotos").select("*").eq("id", id).maybeSingle();
    if (!data || data.estado === "pendiente" || data.estado === "procesando") continue;
    return data;
  }
  return null;
}

async function cobrar() {
  if (cobrando || !itemsCarrito().length) return;
  const msg = document.getElementById("venta-msg");
  const ok = document.getElementById("venta-ok");
  msg.hidden = true;
  ok.hidden = true;
  cobrando = true;
  pintarVender();
  const fila = {
    items: itemsCarrito().map((p) => ({ id: p.id, cantidad: p.cantidad })),
    metodo_pago: metodoPago,
    nota: "Nube",
    created_by: user?.id || null,
    estado: "pendiente",
  };
  if (metodoPago === "Efectivo") {
    const rec = Number(String(document.getElementById("recibido").value || "").replace(/\D/g, ""));
    if (rec) fila.recibido = rec;
  }
  try {
    const { data, error } = await supabase.from("pedidos_remotos").insert(fila).select("id").single();
    if (error) throw error;
    ok.hidden = false;
    ok.textContent = "Pedido enviado. Esperando la impresora del restaurante…";
    const fin = await esperarPedido(data.id);
    if (!fin) {
      ok.textContent = "Pedido enviado. Si el PC está encendido, el ticket sale en unos segundos.";
    } else if (fin.estado === "error") {
      throw new Error(fin.error || "No se pudo cobrar en el local");
    } else {
      carrito = {};
      document.getElementById("recibido").value = "";
      ok.textContent =
        fin.estado === "impreso"
          ? `Factura ${fin.factura} · ticket impreso en el restaurante`
          : `Factura ${fin.factura} registrada. Revisa la impresora.`;
    }
  } catch (err) {
    msg.hidden = false;
    msg.textContent = err.message || "No se pudo cobrar";
  } finally {
    cobrando = false;
    pintarVender();
  }
}

document.getElementById("catalogo").addEventListener("click", (ev) => {
  const boton = ev.target.closest("button[data-add]");
  if (!boton) return;
  const id = Number(boton.dataset.add);
  setCantidad(id, (carrito[id] || 0) + 1);
});
document.getElementById("carrito").addEventListener("click", (ev) => {
  const boton = ev.target.closest("button[data-qty]");
  if (!boton) return;
  setCantidad(Number(boton.dataset.qty), (carrito[Number(boton.dataset.qty)] || 0) + Number(boton.dataset.delta));
});
document.getElementById("metodos-venta").addEventListener("click", (ev) => {
  const boton = ev.target.closest("button[data-metodo]");
  if (!boton) return;
  metodoPago = boton.dataset.metodo;
  pintarVender();
});
document.getElementById("buscar-venta").addEventListener("input", () => pintarVender());
document.getElementById("recibido").addEventListener("input", actualizarCambio);
document.getElementById("cobrar").addEventListener("click", cobrar);
document.getElementById("rep-dias").addEventListener("click", (ev) => {
  const boton = ev.target.closest("button[data-dia]");
  if (!boton) return;
  diaReporte = boton.dataset.dia;
  periodoReporte = "dia";
  const desde = document.getElementById("rep-desde");
  if (desde) desde.value = diaReporte;
  if (ultimoEstado) pintarReporteLocal(ultimoEstado);
  cargarReporteNube();
});

document.getElementById("rep-periodos")?.addEventListener("click", (ev) => {
  const boton = ev.target.closest("button[data-periodo]");
  if (!boton) return;
  periodoReporte = boton.dataset.periodo;
  document.querySelectorAll("#rep-periodos button").forEach((b) => {
    b.classList.toggle("activo", b.dataset.periodo === periodoReporte);
  });
  const cajaRango = document.getElementById("rep-rango");
  if (cajaRango) cajaRango.hidden = periodoReporte === "dia";
  const hasta = document.getElementById("rep-hasta");
  if (hasta) hasta.hidden = periodoReporte !== "rango";
  if (periodoReporte === "dia") diaReporte = "";
  cargarReporteNube();
});
document.getElementById("rep-aplicar")?.addEventListener("click", () => cargarReporteNube());
document.getElementById("rep-desde")?.addEventListener("change", () => {
  if (periodoReporte !== "dia") cargarReporteNube();
});
document.getElementById("rep-hasta")?.addEventListener("change", () => {
  if (periodoReporte === "rango") cargarReporteNube();
});

function cop(n) {
  return dinero.format(Number(n || 0));
}

function empresaInforme() {
  return ultimoEstado?.empresa || {
    razon_social: "Club Burger",
    nombre_comercial: "Club Burger",
    nit: "",
    responsabilidad_tributaria: "Pendiente de registrar ante la DIAN",
    actividad_economica: "5611 — Expendio a la mesa de comidas preparadas",
    representante_legal: "",
    contador: "",
    tarjeta_profesional: "",
    direccion: "",
    ciudad: "",
    departamento: "",
  };
}

function htmlInforme(data) {
  const emp = empresaInforme();
  const nit = emp.nit ? `${emp.nit}${emp.dv ? "-" + emp.dv : ""}` : "Por registrar";
  const metodos = Object.entries(data.por_metodo || {})
    .map(([n, v]) => `<tr><td>${esc(n)}</td><td class="num">${cop(v)}</td></tr>`)
    .join("") || `<tr><td colspan="2">Sin movimientos</td></tr>`;
  const dias = (data.por_dia || [])
    .map((d) => `<tr><td>${esc(d.fecha)}</td><td class="num">${d.items || 0}</td><td class="num">${cop(d.total)}</td></tr>`)
    .join("") || `<tr><td colspan="3">Sin ventas</td></tr>`;
  const prods = (data.por_producto || [])
    .map((p, i) => `<tr><td>${i + 1}</td><td>${esc(p.nombre)}</td><td class="num">${p.cantidad}</td><td class="num">${cop(p.total)}</td></tr>`)
    .join("") || `<tr><td colspan="4">Sin productos</td></tr>`;
  return `<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Informe de ingresos Club Burger</title>
  <style>
    body{margin:0;font:11.5pt/1.45 Palatino,Georgia,serif;color:#1a1a1a;background:#fff}
    .hoja{max-width:216mm;margin:0 auto;padding:16mm}
    header{display:flex;justify-content:space-between;border-bottom:3px solid #1f2a44;padding-bottom:10px}
    h1{font-size:13.5pt;color:#1f2a44;text-transform:uppercase}
    table{width:100%;border-collapse:collapse;margin:10px 0 16px;font-size:10pt}
    th,td{border:1px solid #d7d2c8;padding:6px 8px}
    th{background:#1f2a44;color:#fff;font-size:8.5pt;text-transform:uppercase}
    .num{text-align:right}
    .total{background:#1f2a44;color:#fff;padding:12px 14px;display:flex;justify-content:space-between}
    .letras{background:#f3ead2;padding:8px 12px;margin-bottom:16px}
    .firmas{display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px;margin-top:36px;text-align:center;font-size:8.5pt;color:#5b6375}
    .linea{border-top:1px solid #1f2a44;margin:32px 8px 8px}
    ol{font-size:9pt}
    @page{size:letter;margin:12mm}
  </style></head><body><article class="hoja">
  <header><div><strong>${esc(emp.nombre_comercial || "Club Burger")}</strong><div>NIT ${esc(nit)}</div></div>
  <div>${esc(data.etiqueta || "")}</div></header>
  <h1>Informe auxiliar de ingresos por ventas</h1>
  <p>Soporte interno del POS para el contador. No es factura electrónica ni documento equivalente ante la DIAN.</p>
  <div class="total"><span>Total del período</span><b>${cop(data.total)}</b></div>
  <p class="letras">Período: ${esc(data.desde || "")} a ${esc(data.hasta || "")} · ${esc(data.fuente || "nube")}</p>
  <h2>Medios de pago</h2><table><thead><tr><th>Medio</th><th>Valor</th></tr></thead><tbody>${metodos}</tbody></table>
  <h2>Libro diario</h2><table><thead><tr><th>Fecha</th><th>Ítems</th><th>Ingresos</th></tr></thead><tbody>${dias}</tbody></table>
  <h2>Productos</h2><table><thead><tr><th>#</th><th>Producto</th><th>Cant.</th><th>Ingresos</th></tr></thead><tbody>${prods}</tbody></table>
  <h2>Notas</h2>
  <ol>
    <li>Este informe es un soporte auxiliar del POS. No sustituye la factura electrónica DIAN ni los libros oficiales de comercio.</li>
    <li>Los valores son ingresos brutos en pesos colombianos. El IVA y demás impuestos se determinan con la facturación electrónica y la responsabilidad tributaria del contribuyente.</li>
    <li>Úselo como papeles de trabajo para conciliar el POS con la contabilidad y la declaración de renta.</li>
  </ol>
  <div class="firmas">
    <div><div class="linea"></div>Elaboró<br>Sistema POS</div>
    <div><div class="linea"></div>Representante legal<br>${esc(emp.representante_legal || "Nombre y firma")}</div>
    <div><div class="linea"></div>Contador público<br>${esc(emp.contador || "Nombre, firma y T.P.")}</div>
  </div>
  </article><script>window.onload=()=>window.print()</script></body></html>`;
}

function csvCelda(v) {
  const t = String(v ?? "");
  if (/[",;\n]/.test(t)) return `"${t.replace(/"/g, '""')}"`;
  return t;
}

document.getElementById("rep-imprimir")?.addEventListener("click", () => {
  if (!reporteNube) return;
  const w = window.open("", "_blank", "noopener,width=900,height=1100");
  if (!w) return;
  w.document.write(htmlInforme(reporteNube));
  w.document.close();
});

document.getElementById("rep-excel")?.addEventListener("click", () => {
  if (!reporteNube) return;
  const data = reporteNube;
  const lineas = [
    ["Club Burger", "Informe auxiliar de ingresos por ventas"],
    ["Período", data.etiqueta || "", data.desde || "", data.hasta || ""],
    ["Total COP", data.total || 0, "Ítems", data.items || 0],
    [],
    ["Medio de pago", "Valor"],
    ...Object.entries(data.por_metodo || {}).map(([n, v]) => [n, v]),
    [],
    ["Fecha", "Ítems", "Líneas", "Ingresos"],
    ...(data.por_dia || []).map((d) => [d.fecha, d.items, d.lineas, d.total]),
    [],
    ["Producto", "Cantidad", "Ingresos"],
    ...(data.por_producto || []).map((p) => [p.nombre, p.cantidad, p.total]),
    [],
    ["Nota", "Soporte auxiliar del POS. No es factura electrónica DIAN ni libro oficial de comercio."],
  ];
  const csv = "\uFEFF" + lineas.map((row) => row.map(csvCelda).join(";")).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  a.download = `ClubBurger_InformeIngresos_${data.desde || ""}_${data.hasta || ""}.csv`;
  a.click();
});

(async function inicio() {
  try {
    supabase = crearCliente();
    const { data } = await supabase.auth.getSession();
    if (data.session) {
      user = data.session.user;
      mostrarPanel();
    }
  } catch (err) {
    loginError.hidden = false;
    loginError.textContent = err.message;
  }
})();
