const dinero = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

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

let token = sessionStorage.getItem("cb_token") || "";
let socket = null;
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
let cobrando = false;

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
  if (/failed to fetch|networkerror|load failed/i.test(t)) {
    return "No se pudo conectar al panel. Cierra Club Burger y vuelve a abrirlo; el panel arranca solo.";
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
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        usuario: document.getElementById("usuario").value,
        contrasena: document.getElementById("contrasena").value,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detalle = typeof data.detail === "string" ? data.detail : "Usuario o contraseña incorrectos";
      throw new Error(detalle);
    }
    token = data.token;
    sessionStorage.setItem("cb_token", token);
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

document.getElementById("salir").addEventListener("click", () => {
  sessionStorage.removeItem("cb_token");
  token = "";
  if (socket) socket.close();
  clearInterval(poll);
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
  if (tab === "reporte") cargarReporte();
}

function headers() {
  return { Authorization: `Bearer ${token}` };
}

function mostrarPanel() {
  loginEl.hidden = true;
  panelEl.hidden = false;
  conectar();
  cargarEstado();
}

function conectar() {
  if (socket) socket.close();
  const proto = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${proto}://${location.host}/ws?token=${encodeURIComponent(token)}`);
  socket.onmessage = (ev) => pintar(JSON.parse(ev.data));
  socket.onopen = () => setLive(true);
  socket.onclose = () => {
    setLive(false);
    clearInterval(poll);
    poll = setInterval(cargarEstado, 2000);
  };
}

async function cargarEstado() {
  if (!token) return;
  const res = await fetch("/api/estado", { headers: headers() });
  if (res.status === 401) {
    document.getElementById("salir").click();
    return;
  }
  if (!res.ok) return;
  pintar(await res.json());
}

function setLive(ok) {
  const el = document.getElementById("live-label");
  el.textContent = ok ? "En vivo" : "Reconectando";
  el.classList.toggle("off", !ok);
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
  const total = estado.ventas_caja?.total || 0;
  totalEl.textContent = dinero.format(total);
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
  if (tabActual === "reporte") pintarReporteLocal(estado);
  aplicarPoliticas(estado.sesion);
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

  puedeVender = Boolean(estado.puede_vender);
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
      <article class="metodo">
        <div>
          <span>${nombre}</span>
          <strong>${dinero.format(valor)}</strong>
          <div class="barra"><i style="width:${Math.max(8, (valor / max) * 100)}%"></i></div>
        </div>
      </article>`
    )
    .join("");
}

function pintarReporte(estado) {
  pintarReporteLocal(estado);
}

function paramsReporte() {
  const params = new URLSearchParams({ periodo: periodoReporte });
  const desde = document.getElementById("rep-desde")?.value || "";
  const hasta = document.getElementById("rep-hasta")?.value || "";
  if (periodoReporte === "dia" && diaReporte) params.set("desde", diaReporte);
  if (periodoReporte === "rango") {
    if (desde) params.set("desde", desde);
    if (hasta) params.set("hasta", hasta);
  }
  if (periodoReporte === "mes" && desde) params.set("desde", desde);
  if (periodoReporte === "anio" && desde) params.set("desde", desde);
  if (periodoReporte === "semana" && desde) params.set("desde", desde);
  return params;
}

async function cargarReporte() {
  if (!token) return;
  const fechaEl = document.getElementById("rep-fecha");
  if (fechaEl) fechaEl.textContent = "Cargando…";
  try {
    const res = await fetch(`/api/reporte?${paramsReporte()}`, { headers: headers() });
    if (res.status === 401) {
      document.getElementById("salir").click();
      return;
    }
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "No se pudo cargar el reporte");
    }
    reporteNube = await res.json();
    pintarReporteNube(reporteNube);
    if (ultimoEstado) pintarReporteLocal(ultimoEstado);
  } catch (err) {
    if (fechaEl) fechaEl.textContent = err.message || "No se pudo cargar el reporte";
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
    ? `${items} ítem${items === 1 ? "" : "s"} · ${lineas} línea${lineas === 1 ? "" : "s"} · ${data.fuente === "nube" ? "nube" : "computador"}`
    : "Sin ventas en ese período";
  const aviso = document.getElementById("rep-aviso");
  if (data.aviso) {
    aviso.hidden = false;
    aviso.textContent = data.aviso;
  } else {
    aviso.hidden = true;
  }
  pintarMetodos(mapaMetodos(data.por_metodo), document.getElementById("rep-metodos"));
  pintarLista(document.getElementById("rep-productos"), data.por_producto || [], (p) => ({
    titulo: p.nombre,
    sub: `${p.cantidad} vendidos`,
    valor: dinero.format(p.total),
  }));
  pintarLista(document.getElementById("rep-por-dia"), data.por_dia || [], (d) => ({
    titulo: d.fecha,
    sub: `${d.items || 0} ítems`,
    valor: dinero.format(d.total),
  }));
}

function pintarReporteLocal(estado) {
  const reporte = estado?.reporte;
  const diasEl = document.getElementById("rep-dias");
  if (!diasEl) return;
  const mostrarDias = periodoReporte === "dia";
  diasEl.hidden = !mostrarDias;
  const dias = reporte?.dias || [];
  if (mostrarDias) {
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
  if (!sesiones.length) {
    sesionesEl.innerHTML =
      periodoReporte === "dia"
        ? '<p class="vacio">No hubo caja ese día en este computador</p>'
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
  if (!fiados.nuevos && !fiados.pagos && !fiados.pendiente) {
    fiadosEl.textContent = periodoReporte === "dia" ? "Sin fiados" : "Los fiados se ven en el reporte del día";
  } else {
    fiadosEl.textContent = `Nuevos ${dinero.format(fiados.monto_nuevo || 0)} · pagos ${dinero.format(fiados.monto_pagado || 0)} · pendiente ${dinero.format(fiados.pendiente || 0)}`;
  }
}

function pintarLista(el, items, mapear) {
  if (!items.length) {
    el.innerHTML = '<p class="vacio">Sin movimientos todavía</p>';
    return;
  }
  el.innerHTML = items
    .map((item) => {
      const fila = mapear(item);
      return `<article class="fila-item">
        <div>
          <div class="prod">${fila.titulo}</div>
          <div class="muted mini">${fila.sub}</div>
        </div>
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
  const max = Math.max(0, prod.stock);
  const next = Math.max(0, Math.min(max, cantidad));
  if (next <= 0) delete carrito[id];
  else carrito[id] = next;
  pintarVender();
}

function pintarVender() {
  const bloque = document.getElementById("vender-bloque");
  const ok = document.getElementById("vender-ok");
  bloque.hidden = puedeVender;
  ok.hidden = !puedeVender;
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
  const catalogo = (inventario.productos || []).filter((p) => {
    if (p.stock <= 0) return false;
    if (q && !`${p.nombre} ${p.categoria}`.toLowerCase().includes(q)) return false;
    return true;
  });
  const catEl = document.getElementById("catalogo");
  if (!catalogo.length) {
    catEl.innerHTML = '<p class="vacio">No hay productos disponibles</p>';
  } else {
    catEl.innerHTML = catalogo
      .map((p) => {
        const n = carrito[p.id] || 0;
        return `<article class="prod-venta">
          <div>
            <div class="prod">${esc(p.nombre)}</div>
            <div class="muted mini">${esc(p.categoria)} · ${dinero.format(p.precio)} · ${p.stock} disp.</div>
          </div>
          <div class="qty">
            <button type="button" data-add="${p.id}">+</button>
            ${n ? `<span>${n}</span>` : ""}
          </div>
        </article>`;
      })
      .join("");
  }

  const cartEl = document.getElementById("carrito");
  if (!items.length) {
    cartEl.innerHTML = "";
  } else {
    cartEl.innerHTML = items
      .map(
        (p) => `<article class="cart-item">
          <div>
            <div class="prod">${esc(p.nombre)}</div>
            <div class="muted mini">${dinero.format(p.subtotal)}</div>
          </div>
          <div class="qty">
            <button type="button" data-qty="${p.id}" data-delta="-1">−</button>
            <span>${p.cantidad}</span>
            <button type="button" data-qty="${p.id}" data-delta="1">+</button>
          </div>
        </article>`
      )
      .join("");
  }

  document.getElementById("metodos-venta").innerHTML = metodosPago
    .map(
      (m) =>
        `<button type="button" data-metodo="${esc(m)}" class="${metodoPago === m ? "activo" : ""}">${esc(m)}</button>`
    )
    .join("");
  document.getElementById("efectivo-box").hidden = metodoPago !== "Efectivo";
  actualizarCambio();
  document.getElementById("cobrar").disabled = !puedeVender || !items.length || cobrando;
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

async function cobrar() {
  if (cobrando || !itemsCarrito().length) return;
  const msg = document.getElementById("venta-msg");
  const ok = document.getElementById("venta-ok");
  msg.hidden = true;
  ok.hidden = true;
  cobrando = true;
  pintarVender();
  const body = {
    items: itemsCarrito().map((p) => ({ id: p.id, cantidad: p.cantidad })),
    metodo_pago: metodoPago,
    nota: "",
  };
  if (metodoPago === "Efectivo") {
    const rec = Number(String(document.getElementById("recibido").value || "").replace(/\D/g, ""));
    if (rec) body.recibido = rec;
  }
  try {
    const res = await fetch("/api/vender", {
      method: "POST",
      headers: { ...headers(), "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "No se pudo cobrar");
    carrito = {};
    document.getElementById("recibido").value = "";
    ok.hidden = false;
    ok.textContent = data.impreso
      ? `Factura ${data.factura} · ${dinero.format(data.total)} · ticket en la impresora`
      : `Factura ${data.factura} registrada. El ticket no se pudo imprimir${data.error_impresion ? `: ${data.error_impresion}` : ""}`;
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
  const id = Number(boton.dataset.qty);
  const delta = Number(boton.dataset.delta);
  setCantidad(id, (carrito[id] || 0) + delta);
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
  document.getElementById("rep-desde").value = diaReporte;
  if (ultimoEstado) pintarReporteLocal(ultimoEstado);
  cargarReporte();
});

document.getElementById("rep-periodos").addEventListener("click", (ev) => {
  const boton = ev.target.closest("button[data-periodo]");
  if (!boton) return;
  periodoReporte = boton.dataset.periodo;
  document.querySelectorAll("#rep-periodos button").forEach((b) => {
    b.classList.toggle("activo", b.dataset.periodo === periodoReporte);
  });
  const cajaRango = document.getElementById("rep-rango");
  cajaRango.hidden = periodoReporte === "dia";
  document.getElementById("rep-hasta").hidden = periodoReporte !== "rango";
  if (periodoReporte === "dia") {
    diaReporte = "";
    document.getElementById("rep-desde").value = "";
    document.getElementById("rep-hasta").value = "";
  }
  cargarReporte();
});

document.getElementById("rep-aplicar").addEventListener("click", () => cargarReporte());
document.getElementById("rep-desde").addEventListener("change", () => {
  if (periodoReporte !== "dia") cargarReporte();
});
document.getElementById("rep-hasta").addEventListener("change", () => {
  if (periodoReporte === "rango") cargarReporte();
});

async function descargarExcel() {
  if (!token) return;
  const res = await fetch(`/api/reporte.xlsx?${paramsReporte()}`, { headers: headers() });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "No se pudo exportar");
  }
  const blob = await res.blob();
  const dispo = res.headers.get("Content-Disposition") || "";
  const match = dispo.match(/filename="([^"]+)"/);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = match ? match[1] : "ClubBurger_InformeIngresos.xlsx";
  a.click();
  URL.revokeObjectURL(a.href);
}

document.getElementById("rep-excel").addEventListener("click", async () => {
  const btn = document.getElementById("rep-excel");
  btn.disabled = true;
  btn.textContent = "Generando Excel…";
  try {
    await descargarExcel();
  } catch (err) {
    const aviso = document.getElementById("rep-aviso");
    aviso.hidden = false;
    aviso.textContent = err.message || "No se pudo exportar el Excel";
  } finally {
    btn.disabled = false;
    btn.textContent = "Exportar Excel para el contador";
  }
});

document.getElementById("rep-imprimir").addEventListener("click", () => {
  const url = `/api/reporte/imprimir?token=${encodeURIComponent(token)}&${paramsReporte()}`;
  window.open(url, "_blank", "noopener,width=900,height=1100");
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/static/sw.js").catch(() => {});
}

if (token) mostrarPanel();
