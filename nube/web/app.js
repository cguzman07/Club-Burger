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
let tabActual = "caja";
let filtroInv = "todos";
let inventario = { productos: [], categorias: [], umbral: 5, atencion: 0, agotados: 0, bajos: 0, ok: 0, total: 0 };
let carrito = {};
let metodoPago = "Efectivo";
let metodosPago = ["Efectivo", "Nequi", "Daviplata", "Transferencia", "Tarjeta"];
let puedeVender = false;
let pcEnLinea = false;
let cobrando = false;

function esc(texto) {
  return String(texto ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function crearCliente() {
  if (!cfg.url || !cfg.anonKey) {
    throw new Error("Falta configurar Supabase en Netlify (SUPABASE_URL y SUPABASE_ANON_KEY).");
  }
  return window.supabase.createClient(cfg.url, cfg.anonKey);
}

document.getElementById("login-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  loginError.hidden = true;
  try {
    supabase = crearCliente();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    user = data.user;
    mostrarPanel();
  } catch (err) {
    loginError.hidden = false;
    loginError.textContent = err.message || "No se pudo entrar";
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
  document.getElementById("vista-caja").hidden = tab !== "caja";
  document.getElementById("vista-inventario").hidden = tab !== "inventario";
  document.getElementById("vista-vender").hidden = tab !== "vender";
  document.querySelectorAll("#tabs button").forEach((b) => {
    b.classList.toggle("activo", b.dataset.tab === tab);
  });
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
  return Number.isFinite(t) && Date.now() - t < 20000;
}

function aplicarFila(row) {
  if (!row) return;
  pcEnLinea = Boolean(row.pc_en_linea) && pcReciente(row.updated_at);
  setLive(pcEnLinea, pcEnLinea ? "En vivo" : "PC apagado");
  if (!pcEnLinea) {
    pcBanner.hidden = false;
    pcBanner.innerHTML =
      "<strong>El computador del restaurante no está en línea</strong><span class=\"muted\">Puedes ver lo último que se subió. Para imprimir, enciende el panel en el PC.</span>";
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
  document.getElementById("total-hoy").textContent = dinero.format(estado.ventas_hoy?.total || 0);
  document.getElementById("items-hoy").textContent = String(estado.ventas_hoy?.items || 0);
  const metodos = abierta ? estado.ventas_caja?.por_metodo : estado.ventas_hoy?.por_metodo;
  document.getElementById("metodos-titulo").textContent = abierta
    ? "Por método de pago · caja actual"
    : "Por método de pago · hoy";
  pintarMetodos(metodos || {});
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
  inventario = estado.inventario || inventario;
  metodosPago = estado.metodos_pago || metodosPago;
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

function pintarMetodos(mapa) {
  const entradas = Object.entries(mapa);
  if (!entradas.length) {
    metodosEl.innerHTML = '<p class="vacio">Todavía no hay cobros</p>';
    return;
  }
  const max = Math.max(...entradas.map(([, n]) => n), 1);
  metodosEl.innerHTML = entradas
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

function pintarLista(el, items, mapear) {
  if (!items.length) {
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
