/* corte seco · estúdio
   A interface lê e grava o projeto pelo servidor local. O Claude mexe no
   mesmo arquivo pela linha de comando, e a interface recarrega sozinha
   quando percebe a mudança. */

const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

const RITMOS = {
  calmo: { pausa_max: 0.70, folga: 0.16 },
  natural: { pausa_max: 0.40, folga: 0.10 },
  acelerado: { pausa_max: 0.18, folga: 0.06 },
};
const PALETA = ["#FFFFFF", "#FFD84D", "#FB76B2", "#C2366F", "#2B2B2B", "#C98A4B", "#7CE0B5", "#8AB6FF"];

const S = {
  proj: null, mtime: null, plano: null, estilos: null,
  modo: "ouvir", sujo: false, salvando: false,
  selIni: null, selFim: null, arrastando: false,
  blocoAtual: null, titAtual: null, ultimoExport: null, quadro: null,
};

const video = $("#video");
const fundo = $("#fundo");

/* ============================================================ oncinha
   mesma estampa desenhada na hora do site domigalvao.com */
function oncinha({ base, centro, mancha, tam = 360, n = 58, semente = 7 }) {
  const c = document.createElement("canvas"); c.width = c.height = tam; const g = c.getContext("2d");
  let s = semente; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
  g.fillStyle = base; g.fillRect(0, 0, tam, tam);
  const emenda = fn => { for (const dx of [-tam, 0, tam]) for (const dy of [-tam, 0, tam]) { g.save(); g.translate(dx, dy); fn(); g.restore(); } };
  for (let i = 0; i < n; i++) {
    const x = r() * tam, y = r() * tam, raio = 6 + r() * 10, rot = r() * Math.PI;
    emenda(() => {
      g.save(); g.translate(x, y); g.rotate(rot); g.fillStyle = centro; g.beginPath(); g.ellipse(0, 0, raio * .85, raio * .65, 0, 0, 7); g.fill();
      g.strokeStyle = mancha; g.lineCap = "round"; let a = r() * 6; const k = 3 + Math.floor(r() * 3);
      for (let j = 0; j < k; j++) { const len = .7 + r() * .9; g.lineWidth = raio * (.32 + r() * .2); g.beginPath(); g.ellipse(0, 0, raio * 1.05, raio * .82, 0, a, a + len); g.stroke(); a += len + .35 + r() * .4; }
      g.restore();
    });
  }
  for (let i = 0; i < n * 1.4; i++) { const x = r() * tam, y = r() * tam, rr = 2 + r() * 4; emenda(() => { g.fillStyle = mancha; g.beginPath(); g.ellipse(x, y, rr, rr * .8, r() * 3, 0, 7); g.fill(); }); }
  g.globalAlpha = .07;
  for (let i = 0; i < 2600; i++) { const x = r() * tam, y = r() * tam; g.strokeStyle = r() > .5 ? "#fff" : "#000"; g.lineWidth = .8; g.beginPath(); g.moveTo(x, y); g.lineTo(x + 2 + r() * 3, y + 3 + r() * 3); g.stroke(); }
  return `url(${c.toDataURL("image/png")})`;
}
document.documentElement.style.setProperty("--leo", oncinha({ base: "#c98a4b", centro: "#a9662f", mancha: "#2a1c12", semente: 11 }));
document.documentElement.style.setProperty("--leo-rosa", oncinha({ base: "#fb76b2", centro: "#f2569c", mancha: "#2b2b2b", tam: 320, semente: 5 }));

/* ============================================================ utilidades */
const fmt = t => { t = Math.max(0, t || 0); const m = Math.floor(t / 60); const s = t - m * 60; return `${m}:${s.toFixed(1).padStart(4, "0")}`; };
const fmtCurto = t => { t = Math.max(0, t || 0); const m = Math.floor(t / 60); const s = Math.floor(t - m * 60); return `${m}:${String(s).padStart(2, "0")}`; };
const seg = n => `${n.toFixed(1).replace(".", ",")}s`;
const esc = t => String(t).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let tAviso;
function aviso(txt) {
  const el = $("#aviso"); el.textContent = txt; el.classList.add("mostra");
  clearTimeout(tAviso); tAviso = setTimeout(() => el.classList.remove("mostra"), 3200);
}

async function api(metodo, rota, corpo) {
  const r = await fetch(rota, {
    method: metodo, headers: corpo ? { "Content-Type": "application/json" } : {},
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  const dados = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, dados };
}

function corDe(valor) {
  if (!valor) return null;
  if (valor.startsWith("#")) return valor;
  const m = Object.assign({}, S.estilos.marca_padrao, S.proj.marca || {});
  return m[valor] || "#FFFFFF";
}

/* ============================================================ salvar e plano */
let tSalvar, tPlano;
function mudou({ transcricao = true } = {}) {
  S.sujo = true;
  clearTimeout(tSalvar); tSalvar = setTimeout(salvar, 450);
  clearTimeout(tPlano); tPlano = setTimeout(atualizarPlano, 60);
  if (transcricao) desenharTranscricao();
  desenharControles();
}

async function salvar() {
  if (S.salvando) { clearTimeout(tSalvar); tSalvar = setTimeout(salvar, 300); return; }
  S.salvando = true;
  const r = await api("PUT", "/api/projeto", { projeto: S.proj, mtime: S.mtime });
  S.salvando = false;
  if (r.status === 409) {
    S.proj = r.dados.projeto; S.mtime = r.dados.mtime; S.sujo = false;
    aviso("o claude mexeu no projeto agora, carreguei a versão dele");
    tudo();
    return;
  }
  if (r.ok) { S.mtime = r.dados.mtime; S.sujo = false; }
}

async function atualizarPlano() {
  const r = await api("POST", "/api/plano", S.proj);
  if (!r.ok) return;
  S.plano = r.dados;
  S.blocoAtual = null; S.titAtual = null;
  desenharResumo();
  desenharQuadro(true);
}

async function recarregar() {
  const r = await api("GET", "/api/projeto");
  S.proj = r.dados.projeto; S.mtime = r.dados.mtime;
  tudo();
}

function tudo() {
  desenharControles();
  desenharTranscricao();
  desenharEstilos();
  desenharTitulos();
  atualizarPlano();
}

/* ============================================================ tempo: original <-> editado */
function segDe(t) {
  const segs = S.plano?.segmentos || [];
  for (const s of segs) if (t >= s.ini - 0.0005 && t < s.fim) return s;
  return null;
}
function paraSaida(t) {
  const segs = S.plano?.segmentos || [];
  const s = segDe(t);
  if (s) return s.out + (t - s.ini);
  const prox = segs.find(s => s.ini > t);
  return prox ? prox.out : (S.plano?.duracao_saida || 0);
}
function paraOriginal(out) {
  const segs = S.plano?.segmentos || [];
  for (const s of segs) { const d = s.fim - s.ini; if (out >= s.out && out < s.out + d) return s.ini + (out - s.out); }
  return segs.length ? segs[segs.length - 1].fim - 0.01 : 0;
}

/* ============================================================ reprodução */
function tocar() {
  const segs = S.plano?.segmentos || [];
  if (!segs.length) return;
  if (!segDe(video.currentTime)) {
    const prox = segs.find(s => s.ini > video.currentTime);
    video.currentTime = prox ? prox.ini : segs[0].ini;
  }
  video.play();
}
function alternar() { video.paused ? tocar() : video.pause(); }

function laco() {
  const segs = S.plano?.segmentos || [];
  const t = video.currentTime;
  if (!video.paused && segs.length) {
    if (!segDe(t)) {
      const prox = segs.find(s => s.ini > t - 0.001);
      if (prox) video.currentTime = prox.ini;
      else { video.pause(); video.currentTime = segs[0].ini; }
    }
  }
  if (S.proj?.formato?.enquadramento === "ajustar") {
    if (Math.abs(fundo.currentTime - video.currentTime) > 0.2) fundo.currentTime = video.currentTime;
    if (video.paused !== fundo.paused) video.paused ? fundo.pause() : fundo.play().catch(() => {});
  }
  desenharQuadro(false);
  requestAnimationFrame(laco);
}

video.addEventListener("play", () => $("#celular").classList.add("tocando"));
video.addEventListener("pause", () => $("#celular").classList.remove("tocando"));
video.addEventListener("play", () => $("#btn-play").textContent = "❚❚");
video.addEventListener("pause", () => $("#btn-play").textContent = "▶");
$("#btn-play").onclick = alternar;
$("#play-grande").onclick = tocar;
$("#celular").addEventListener("click", e => { if (e.target.id !== "play-grande") alternar(); });
$("#linha-tempo").addEventListener("click", e => {
  const r = e.currentTarget.getBoundingClientRect();
  const out = (e.clientX - r.left) / r.width * (S.plano?.duracao_saida || 0);
  video.currentTime = paraOriginal(out);
});
document.addEventListener("keydown", e => {
  if (e.target.matches("input, textarea, select")) return;
  if (e.code === "Space") { e.preventDefault(); alternar(); }
});

/* ============================================================ texto por cima do vídeo */
function cssTexto(cfg, el, legenda) {
  const fonte = cfg.fonte;
  const fator = S.estilos.fontes[fonte]?.fator_ass || 1.2;
  el.style.fontFamily = `"${fonte}"`;
  el.style.fontSize = cfg.tamanho + "px";
  el.style.lineHeight = fator;
  el.style.color = corDe(cfg.cor);
  const caixa = corDe(cfg.caixa);
  if (!caixa && cfg.contorno) {
    const alfa = 1 - (cfg.alfa_contorno || 0) / 255;
    const c = corDe(cfg.cor_contorno || "#000000");
    el.style.webkitTextStroke = `${cfg.contorno * 2}px ${hexAlfa(c, alfa)}`;
    el.style.paintOrder = "stroke fill";
  } else { el.style.webkitTextStroke = ""; }
  el.style.textShadow = (!caixa && cfg.sombra) ? `${cfg.sombra}px ${cfg.sombra}px 0 rgba(0,0,0,.56)` : "";
  if (cfg.rotacao) el.style.rotate = `${cfg.rotacao}deg`; else el.style.rotate = "";
}
function hexAlfa(hex, a) {
  const h = hex.replace("#", ""); const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

function montarLegenda(bloco, cfg) {
  const el = document.createElement("div");
  el.className = "bloco-leg";
  cssTexto(cfg, el, true);
  el.style.top = (S.proj.legenda.posicao * 1920) + "px";
  const caixa = corDe(cfg.caixa);
  const fonteIt = S.estilos.fontes[cfg.fonte + " Italic"] ? cfg.fonte + " Italic" : null;
  bloco.palavras.forEach((w, k) => {
    const sp = document.createElement("span");
    sp.className = "pal" + (caixa ? " caixa" : "");
    sp.textContent = w.t;
    sp.dataset.k = k;
    if (w.destaque) {
      sp.style.color = corDe(cfg.cor_destaque || cfg.cor);
      if (cfg.italico_destaque && fonteIt) sp.style.fontFamily = `"${fonteIt}"`;
    }
    if (caixa) {
      sp.style.background = corDe(w.destaque ? (cfg.caixa_destaque || cfg.caixa) : cfg.caixa);
      sp.style.padding = `${cfg.contorno * 0.55}px ${cfg.contorno}px`;
    }
    el.appendChild(sp);
    if (k < bloco.palavras.length - 1) el.appendChild(document.createTextNode(" "));
  });
  if (cfg.animacao === "pop") el.classList.add("anima-pop");
  if (cfg.animacao === "fade") el.classList.add("anima-fade");
  return el;
}

function pintarAtiva(el, bloco, cfg, out) {
  if (!cfg.karaoke) return;
  const caixa = corDe(cfg.caixa);
  el.querySelectorAll(".pal").forEach(sp => {
    const w = bloco.palavras[+sp.dataset.k];
    const ativa = out >= w.ini_out && out < w.fim_out;
    sp.style.color = corDe(ativa ? (cfg.cor_ativa || cfg.cor) : (w.destaque ? (cfg.cor_destaque || cfg.cor) : cfg.cor));
    if (caixa) sp.style.background = corDe(ativa ? (cfg.caixa_ativa || cfg.caixa) : (w.destaque ? (cfg.caixa_destaque || cfg.caixa) : cfg.caixa));
  });
}

function montarTitulo(texto, y, cfg) {
  const el = document.createElement("div");
  el.className = "bloco-tit";
  cssTexto(cfg, el, false);
  el.style.top = (y * 1920) + "px";
  const caixa = corDe(cfg.caixa);
  const linhas = (cfg.caixa_alta ? texto.toUpperCase() : texto).split("|").map(t => t.trim()).filter(Boolean);
  linhas.forEach((l, k) => {
    const sp = document.createElement("span");
    sp.className = "linha"; sp.textContent = l;
    if (caixa) {
      sp.style.background = caixa; sp.style.padding = `${cfg.contorno * 0.5}px ${cfg.contorno}px`;
      el.classList.add("caixa");
    }
    el.appendChild(sp);
    if (k < linhas.length - 1) el.appendChild(document.createElement("br"));
  });
  if (cfg.animacao === "pop") el.classList.add("anima-pop"); else el.classList.add("anima-fade");
  return el;
}

function escalaTela(container, tela) {
  const w = container.clientWidth;
  tela.style.transform = `scale(${w / 1080})`;
}

function desenharQuadro(forcar) {
  if (!S.plano || !S.estilos) return;
  const tela = $("#tela");
  escalaTela($("#sobreposicao"), tela);
  const out = paraSaida(video.currentTime);
  const total = S.plano.duracao_saida || 0;
  $("#tempo").textContent = `${fmtCurto(out)} / ${fmtCurto(total)}`;
  $("#preenchido").style.width = total ? `${Math.min(100, out / total * 100)}%` : "0";

  const est = S.plano.estilo;
  const bloco = S.plano.blocos.find(b => out >= b.ini_out && out < b.fim_out) || null;
  const tits = [];
  if (S.plano.gancho && out < S.plano.gancho.fim_out) tits.push({ ...S.plano.gancho, y: S.plano.gancho.posicao });
  for (const t of S.plano.titulos) if (out >= t.ini_out && out < t.fim_out) tits.push({ ...t, y: 0.2 });
  const chaveTit = tits.map(t => t.texto + t.ini_out).join("|");

  if (forcar || bloco !== S.blocoAtual || chaveTit !== S.titAtual) {
    tela.innerHTML = "";
    for (const t of tits) tela.appendChild(montarTitulo(t.texto, t.y, est.titulo));
    if (bloco) tela.appendChild(montarLegenda(bloco, est.legenda));
    S.blocoAtual = bloco; S.titAtual = chaveTit;
  }
  const el = tela.querySelector(".bloco-leg");
  if (el && bloco) pintarAtiva(el, bloco, est.legenda, out);
  marcarPalavraAtual();
}

let palavraAgora = null;
function marcarPalavraAtual() {
  const t = video.currentTime;
  const pal = S.proj?.palavras || [];
  let achada = null;
  for (const p of pal) { if (t >= p.ini && t < p.fim + 0.05) { achada = p.i; break; } if (p.ini > t) break; }
  if (achada === palavraAgora) return;
  if (palavraAgora !== null) document.querySelector(`.w[data-i="${palavraAgora}"]`)?.classList.remove("agora");
  palavraAgora = achada;
  if (achada !== null) {
    const el = document.querySelector(`.w[data-i="${achada}"]`);
    if (el) {
      el.classList.add("agora");
      if (!video.paused) {
        const r = el.getBoundingClientRect();
        if (r.top < 140 || r.bottom > innerHeight - 40) el.scrollIntoView({ block: "center", behavior: "smooth" });
      }
    }
  }
}

/* ============================================================ resumo */
function desenharResumo() {
  const p = S.plano; if (!p) return;
  const economia = Math.max(0, p.duracao_original - p.duracao_saida);
  $("#economia-txt").textContent = "−" + seg(economia);
  $("#resumo-corte").textContent = `${seg(p.duracao_original)} viraram ${seg(p.duracao_saida)} · ${p.cortes} ${p.cortes === 1 ? "corte" : "cortes"}`;
}

/* ============================================================ controles */
function desenharControles() {
  const pj = S.proj; if (!pj) return;
  const aj = pj.ajustes;
  $$("#ritmos .pilula").forEach(b => b.classList.toggle("ativa", b.dataset.ritmo === aj.ritmo));
  $("#r-pausa").value = aj.pausa_max; $("#o-pausa").textContent = seg(+aj.pausa_max);
  $("#r-folga").value = aj.folga; $("#o-folga").textContent = seg(+aj.folga);
  $("#c-pausas").checked = !!aj.cortar_pausas;
  $$("#modos .pilula").forEach(b => b.classList.toggle("ativa", b.dataset.modo === S.modo));
  $("#dica-modo").textContent = {
    ouvir: "clique numa palavra pra ouvir a partir dali.",
    cortar: "clique ou arraste por cima das palavras pra cortar. clique de novo pra trazer de volta.",
    destacar: "clique ou arraste pra deixar as palavras em destaque na legenda.",
  }[S.modo];

  const g = pj.gancho;
  $("#g-ativo").checked = !!g.ativo;
  if (document.activeElement !== $("#g-texto")) $("#g-texto").value = g.texto || "";
  $("#g-dur").value = g.duracao; $("#o-gdur").textContent = seg(+g.duracao);
  $("#g-pos").value = g.posicao ?? 0.2; $("#o-gpos").textContent = Math.round((g.posicao ?? 0.2) * 100) + "%";
  const sug = pj.sugestoes?.ganchos || [];
  $("#sugestoes").innerHTML = sug.length ? `<p>sugestões do claude, clique pra usar</p>` + sug.map((t, k) => `<button class="sugestao" data-k="${k}">${esc(t)}</button>`).join("") : "";

  const l = pj.legenda;
  const est = S.estilos ? S.estilos.estilos.find(e => e.id === l.estilo) : null;
  $("#l-ativa").checked = l.ativa !== false;
  const npal = l.palavras || est?.legenda.palavras || 3;
  $("#l-pal").value = npal; $("#o-lpal").textContent = npal;
  $("#l-pos").value = l.posicao; $("#o-lpos").textContent = Math.round(l.posicao * 100) + "%";
  const ca = l.caixa_alta === null || l.caixa_alta === undefined ? "" : (l.caixa_alta ? "1" : "0");
  $$("#caixa-alta .pilula").forEach(b => b.classList.toggle("ativa", b.dataset.ca === ca));
  $("#l-pont").checked = l.sem_pontuacao !== false;

  $("#m-texto").value = pj.marca.texto; $("#m-destaque").value = pj.marca.destaque;
  $$("#enquadramento .pilula").forEach(b => b.classList.toggle("ativa", b.dataset.enq === pj.formato.enquadramento));
  $("#celular").classList.toggle("ajustar", pj.formato.enquadramento === "ajustar");
  $("#f-volume").checked = pj.formato.volume !== false;

  // cortes feitos pelo claude ou automáticos, agrupados por motivo
  const grupos = {};
  for (const p of pj.palavras) if (p.cortada && p.origem !== "voce") (grupos[p.motivo || "claude"] ||= []).push(p.i);
  const chaves = Object.keys(grupos);
  $("#cortes-claude").hidden = !chaves.length;
  $("#cortes-claude").innerHTML = chaves.length ? `<p class="rotulo">o que já saiu</p>` + chaves.map(m =>
    `<div class="linha"><span><span class="motivo">${esc(m)}</span> ${grupos[m].length} ${grupos[m].length === 1 ? "palavra" : "palavras"}</span>
     <button class="btn borda pequeno" data-desfazer="${esc(m)}">trazer de volta</button></div>`).join("") : "";
}

function desenharTranscricao() {
  const el = $("#transcricao");
  const pj = S.proj;
  el.classList.toggle("modo-cortar", S.modo === "cortar");
  el.classList.toggle("modo-destacar", S.modo === "destacar");
  if (!pj.palavras.length) {
    el.innerHTML = `<div class="carregando" id="carregando">${esc(S.estadoMsg || "esperando a transcrição")}</div>`;
    return;
  }
  const aj = pj.ajustes;
  const titulos = Object.fromEntries((pj.titulos || []).map(t => [t.palavra, t.texto]));
  const partes = ['<p class="paragrafo">'];
  let motivoAnterior = null;
  pj.palavras.forEach((p, k) => {
    if (k) {
      const gap = p.ini - pj.palavras[k - 1].fim;
      if (gap > 1.4) partes.push('</p><p class="paragrafo">');
      if (gap > 0.25) {
        const cortada = aj.cortar_pausas && gap > aj.pausa_max;
        partes.push(`<span class="pausa${cortada ? " cortada" : ""}" title="pausa de ${seg(gap)}">${seg(gap)}</span>`);
      }
    }
    if (titulos[p.i]) partes.push(`<span class="marca-titulo">título · ${esc(titulos[p.i])}</span>`);
    const m = p.cortada ? (p.motivo || "") : null;
    if (m && m !== motivoAnterior && m !== "você") partes.push(`<span class="motivo${p.origem === "auto" ? " auto" : ""}">${esc(m)}</span>`);
    motivoAnterior = m;
    const cls = ["w"];
    if (p.cortada) cls.push("cortada");
    if (p.destaque) cls.push("destaque");
    if (S.selIni !== null && between(p.i, S.selIni, S.selFim)) cls.push("sel");
    partes.push(`<span class="${cls.join(" ")}" data-i="${p.i}" title="${fmt(p.ini)}">${esc(p.t)}</span> `);
  });
  partes.push("</p>");
  el.innerHTML = partes.join("");
  palavraAgora = null;
}
const between = (i, a, b) => i >= Math.min(a, b) && i <= Math.max(a, b);

/* seleção com clique ou arrasto */
$("#transcricao").addEventListener("pointerdown", e => {
  const w = e.target.closest(".w"); if (!w) return;
  const i = +w.dataset.i;
  if (S.modo === "ouvir") { video.currentTime = S.proj.palavras[i].ini; tocar(); return; }
  S.arrastando = true; S.selIni = S.selFim = i;
  marcarSelecao();
});
$("#transcricao").addEventListener("pointerover", e => {
  if (!S.arrastando) return;
  const w = e.target.closest(".w"); if (!w) return;
  S.selFim = +w.dataset.i; marcarSelecao();
});
document.addEventListener("pointerup", () => {
  if (!S.arrastando) return;
  S.arrastando = false;
  const a = Math.min(S.selIni, S.selFim), b = Math.max(S.selIni, S.selFim);
  const faixa = S.proj.palavras.slice(a, b + 1);
  if (S.modo === "cortar") {
    const todas = faixa.every(p => p.cortada);
    for (const p of faixa) {
      if (todas) { p.cortada = false; delete p.motivo; p.origem = "voce"; }
      else { p.cortada = true; p.motivo = "você"; p.origem = "voce"; }
    }
  } else if (S.modo === "destacar") {
    const todas = faixa.every(p => p.destaque);
    for (const p of faixa) p.destaque = !todas;
  }
  S.selIni = S.selFim = null;
  mudou();
});
function marcarSelecao() {
  $$(".w.sel").forEach(el => el.classList.remove("sel"));
  const a = Math.min(S.selIni, S.selFim), b = Math.max(S.selIni, S.selFim);
  for (let i = a; i <= b; i++) document.querySelector(`.w[data-i="${i}"]`)?.classList.add("sel");
}

/* ============================================================ estilos */
function desenharEstilos() {
  if (!S.estilos || !S.proj) return;
  const grade = $("#estilos");
  grade.innerHTML = "";
  const exemplo = {
    palavras: [
      { t: "seu", destaque: false, ini_out: 0, fim_out: 0 },
      { t: "vídeo", destaque: true, ini_out: 0, fim_out: 0 },
      { t: "pronto", destaque: false, ini_out: 0, fim_out: 1 },
    ],
  };
  for (const e of S.estilos.estilos) {
    const card = document.createElement("button");
    card.className = "estilo-card" + (e.id === S.proj.legenda.estilo ? " ativa" : "");
    card.dataset.estilo = e.id;
    const mini = document.createElement("div");
    mini.className = "mini-tela";
    if (S.quadro) mini.style.backgroundImage = `url(${S.quadro})`;
    const tela = document.createElement("div"); tela.className = "tela";
    const cfg = { ...e.legenda };
    const ex = JSON.parse(JSON.stringify(exemplo));
    if (cfg.caixa_alta) ex.palavras.forEach(w => w.t = w.t.toUpperCase());
    const leg = montarLegenda(ex, cfg);
    leg.classList.remove("anima-pop", "anima-fade");
    leg.style.top = "1260px";
    pintarAtiva(leg, ex, cfg, 0.5);
    tela.appendChild(leg);
    mini.appendChild(tela);
    card.appendChild(mini);
    card.insertAdjacentHTML("beforeend", `<strong>${esc(e.nome)}</strong><small>${esc(e.descricao)}</small>`);
    grade.appendChild(card);
    requestAnimationFrame(() => {
      const w = mini.clientWidth, h = mini.clientHeight; if (!w) return;
      const s = w / 1080 * 1.35;
      tela.style.transform = `translate(${(w - 1080 * s) / 2}px, ${h * 0.62 - 1260 * s}px) scale(${s})`;
    });
  }
  $("#amostras").innerHTML = PALETA.map(c => `<button class="amostra" style="background:${c}" data-cor="${c}" title="usar ${c} como destaque"></button>`).join("");
}

function capturarQuadro() {
  try {
    const c = document.createElement("canvas");
    const w = 270, h = 480; c.width = w; c.height = h;
    const g = c.getContext("2d");
    const vw = video.videoWidth, vh = video.videoHeight;
    const esc = Math.max(w / vw, h / vh);
    g.drawImage(video, (w - vw * esc) / 2, (h - vh * esc) / 2, vw * esc, vh * esc);
    S.quadro = c.toDataURL("image/jpeg", 0.8);
    desenharEstilos();
  } catch (e) { /* sem quadro, fica o fundo grafite */ }
}

/* ============================================================ títulos */
function desenharTitulos() {
  const lista = $("#titulos");
  const pj = S.proj;
  lista.innerHTML = (pj.titulos || []).map((t, k) => {
    const p = pj.palavras[t.palavra];
    return `<div class="item-titulo" data-k="${k}">
      <span class="quando">${p ? fmtCurto(paraSaida(p.ini)) : "?"}</span>
      <input type="text" value="${esc(t.texto)}" data-campo="texto">
      <select data-campo="duracao">${[1.5, 2, 2.5, 3, 4].map(d => `<option value="${d}" ${+t.duracao === d ? "selected" : ""}>${seg(d)}</option>`).join("")}</select>
      <button class="remover" title="remover">×</button></div>`;
  }).join("");
}
$("#titulos").addEventListener("input", e => {
  const item = e.target.closest(".item-titulo"); if (!item) return;
  const t = S.proj.titulos[+item.dataset.k];
  if (e.target.dataset.campo === "texto") t.texto = e.target.value;
  if (e.target.dataset.campo === "duracao") t.duracao = +e.target.value;
  mudou({ transcricao: e.target.dataset.campo !== "texto" });
});
$("#titulos").addEventListener("click", e => {
  if (!e.target.matches(".remover")) return;
  S.proj.titulos.splice(+e.target.closest(".item-titulo").dataset.k, 1);
  desenharTitulos(); mudou();
});
$("#t-novo").onclick = () => {
  const t = video.currentTime;
  const p = S.proj.palavras.find(p => p.fim > t && !p.cortada) || S.proj.palavras[0];
  if (!p) return;
  S.proj.titulos = (S.proj.titulos || []).filter(x => x.palavra !== p.i);
  S.proj.titulos.push({ palavra: p.i, texto: "novo título", duracao: 2 });
  S.proj.titulos.sort((a, b) => a.palavra - b.palavra);
  desenharTitulos(); mudou();
  const k = S.proj.titulos.findIndex(x => x.palavra === p.i);
  const inp = document.querySelector(`.item-titulo[data-k="${k}"] input`);
  if (inp) { inp.focus(); inp.select(); }
};

/* ============================================================ eventos dos controles */
$$(".aba").forEach(b => b.onclick = () => irPara(b.dataset.aba));
function irPara(aba) {
  $$(".aba").forEach(x => x.classList.toggle("ativa", x.dataset.aba === aba));
  $$(".conteudo").forEach(x => x.classList.toggle("ativa", x.dataset.conteudo === aba));
  if (aba === "estilo") desenharEstilos();
  if (aba === "exportar") listarExportados();
  if (aba === "texto") desenharTitulos();
  scrollTo({ top: 0, behavior: "smooth" });
}
$("#btn-exportar-topo").onclick = () => irPara("exportar");

$("#ritmos").onclick = e => {
  const r = e.target.dataset.ritmo; if (!r) return;
  Object.assign(S.proj.ajustes, { ritmo: r }, RITMOS[r]); mudou();
};
$("#r-pausa").oninput = e => { S.proj.ajustes.pausa_max = +e.target.value; S.proj.ajustes.ritmo = "personalizado"; mudou(); };
$("#r-folga").oninput = e => { S.proj.ajustes.folga = +e.target.value; S.proj.ajustes.ritmo = "personalizado"; mudou(); };
$("#c-pausas").onchange = e => { S.proj.ajustes.cortar_pausas = e.target.checked; mudou(); };
$("#modos").onclick = e => { const m = e.target.closest(".pilula")?.dataset.modo; if (!m) return; S.modo = m; desenharControles(); desenharTranscricao(); };
$("#cortes-claude").onclick = e => {
  const m = e.target.dataset.desfazer; if (m === undefined) return;
  for (const p of S.proj.palavras) if (p.cortada && p.origem !== "voce" && (p.motivo || "claude") === m) { p.cortada = false; delete p.motivo; p.origem = "voce"; }
  aviso(`os cortes de ${m} voltaram pro vídeo`); mudou();
};

$("#g-ativo").onchange = e => { S.proj.gancho.ativo = e.target.checked; mudou({ transcricao: false }); };
$("#g-texto").oninput = e => { S.proj.gancho.texto = e.target.value; S.proj.gancho.ativo = !!e.target.value.trim(); $("#g-ativo").checked = S.proj.gancho.ativo; mudou({ transcricao: false }); };
$("#g-dur").oninput = e => { S.proj.gancho.duracao = +e.target.value; mudou({ transcricao: false }); };
$("#g-pos").oninput = e => { S.proj.gancho.posicao = +e.target.value; mudou({ transcricao: false }); };
$("#sugestoes").onclick = e => {
  const k = e.target.dataset.k; if (k === undefined) return;
  S.proj.gancho.texto = S.proj.sugestoes.ganchos[+k]; S.proj.gancho.ativo = true;
  $("#g-texto").value = S.proj.gancho.texto;
  video.currentTime = S.plano?.segmentos?.[0]?.ini || 0;
  mudou({ transcricao: false });
};
$("#l-ativa").onchange = e => { S.proj.legenda.ativa = e.target.checked; mudou({ transcricao: false }); };
$("#l-pal").oninput = e => { S.proj.legenda.palavras = +e.target.value; mudou({ transcricao: false }); };
$("#l-pos").oninput = e => { S.proj.legenda.posicao = +e.target.value; mudou({ transcricao: false }); };
$("#caixa-alta").onclick = e => { const v = e.target.dataset.ca; if (v === undefined) return; S.proj.legenda.caixa_alta = v === "" ? null : v === "1"; mudou({ transcricao: false }); };
$("#l-pont").onchange = e => { S.proj.legenda.sem_pontuacao = e.target.checked; mudou({ transcricao: false }); };

$("#estilos").onclick = e => {
  const c = e.target.closest(".estilo-card"); if (!c) return;
  S.proj.legenda.estilo = c.dataset.estilo; S.proj.legenda.palavras = null;
  $$(".estilo-card").forEach(x => x.classList.toggle("ativa", x === c));
  mudou({ transcricao: false });
};
$("#m-texto").oninput = e => { S.proj.marca.texto = e.target.value.toUpperCase(); mudou({ transcricao: false }); desenharEstilosDepois(); };
$("#m-destaque").oninput = e => { S.proj.marca.destaque = e.target.value.toUpperCase(); mudou({ transcricao: false }); desenharEstilosDepois(); };
$("#amostras").onclick = e => { const c = e.target.dataset.cor; if (!c) return; S.proj.marca.destaque = c; mudou({ transcricao: false }); desenharEstilos(); };
let tEst; function desenharEstilosDepois() { clearTimeout(tEst); tEst = setTimeout(desenharEstilos, 150); }
$("#enquadramento").onclick = e => { const v = e.target.dataset.enq; if (!v) return; S.proj.formato.enquadramento = v; mudou({ transcricao: false }); };
$("#f-volume").onchange = e => { S.proj.formato.volume = e.target.checked; mudou({ transcricao: false }); };
$("#salvar-marca").onclick = async () => {
  await salvar();
  const r = await api("POST", "/api/marca");
  aviso(r.ok ? "padrão da marca salvo pros próximos vídeos" : "não consegui salvar o padrão");
};
$("#ver-zonas").onchange = e => { $("#zonas").hidden = !e.target.checked; };

/* ============================================================ exportar */
async function exportar(previa) {
  await salvar();
  const r = await api("POST", "/api/exportar", { previa });
  if (!r.ok) { aviso(r.dados.erro || "não deu pra exportar agora"); return; }
  $("#progresso").hidden = false; $("#erro").hidden = true;
  $("#progresso-txt").textContent = previa ? "gerando a prévia" : "exportando o vídeo final";
  $("#progresso-barra").style.width = "2%";
}
$("#exp-previa").onclick = () => exportar(true);
$("#exp-final").onclick = () => exportar(false);

async function listarExportados() {
  const r = await api("GET", "/api/exportados");
  const itens = r.dados.itens || [];
  $("#exportados").innerHTML = itens.map(it => `
    <div class="exportado">
      <div><div class="nome">${esc(it.nome)}</div>
      <div class="info">${(it.tamanho / 1048576).toFixed(1).replace(".", ",")} MB · ${new Date(it.quando * 1000).toLocaleString("pt-BR")}</div></div>
      <div class="acoes">
        <a class="btn borda pequeno" href="/exportados/${encodeURIComponent(it.nome)}" target="_blank" rel="noopener">assistir</a>
        <button class="btn escuro pequeno" data-caminho="${esc(it.caminho)}">copiar caminho</button>
      </div>
    </div>`).join("");
}
$("#exportados").onclick = async e => {
  const c = e.target.dataset.caminho; if (!c) return;
  try { await navigator.clipboard.writeText(c); aviso("caminho do arquivo copiado"); } catch { aviso(c); }
};

/* ============================================================ estado (o que está rolando) */
async function vigiar() {
  try {
    const r = await api("GET", "/api/estado");
    const e = r.dados.estado || {};
    const st = $("#status");
    st.classList.remove("trabalhando", "erro");
    let txt = "tudo salvo";
    if (e.tarefa) { st.classList.add("trabalhando"); txt = e.mensagem || "trabalhando"; }
    else if (e.claude?.trabalhando) { st.classList.add("trabalhando"); txt = "claude: " + (e.claude.mensagem || "trabalhando"); }
    else if (e.erro) { st.classList.add("erro"); txt = e.mensagem || "algo deu errado"; }
    else if (S.sujo || S.salvando) txt = "salvando";
    $("#status-txt").textContent = txt;
    S.estadoMsg = e.mensagem;
    const carregando = $("#carregando"); if (carregando && e.mensagem) carregando.textContent = e.mensagem;

    if (e.tarefa === "exportando") {
      $("#progresso").hidden = false;
      $("#progresso-txt").textContent = e.mensagem;
      $("#progresso-barra").style.width = Math.round((e.progresso || 0) * 100) + "%";
    } else if (!$("#progresso").hidden) {
      $("#progresso-barra").style.width = "100%";
      setTimeout(() => { $("#progresso").hidden = true; }, 700);
    }
    if (!e.tarefa && e.erro) { $("#erro").hidden = false; $("#erro").textContent = e.erro; }
    if (e.ultimo_export && e.ultimo_export !== S.ultimoExport && !e.tarefa) {
      if (S.ultimoExport !== null) aviso(e.mensagem === "prévia pronta" ? "prévia pronta" : "vídeo exportado, tá na lista");
      S.ultimoExport = e.ultimo_export;
      listarExportados();
    }
    if (S.ultimoExport === null) S.ultimoExport = e.ultimo_export || "";
    if (!S.sujo && !S.salvando && r.dados.mtime !== S.mtime) await recarregar();
  } catch (err) {
    $("#status-txt").textContent = "sem conexão com o claude code";
    $("#status").classList.add("erro");
  }
  setTimeout(vigiar, 1000);
}

/* ============================================================ início */
(async function iniciar() {
  S.estilos = (await api("GET", "/api/estilos")).dados;
  const r = await api("GET", "/api/projeto");
  S.proj = r.dados.projeto; S.mtime = r.dados.mtime;
  video.src = "/video"; fundo.src = "/video";
  video.addEventListener("loadeddata", () => { setTimeout(capturarQuadro, 300); }, { once: true });
  video.addEventListener("seeked", () => { if (!S.quadro) capturarQuadro(); }, { once: true });
  await document.fonts.ready;
  tudo();
  addEventListener("resize", () => desenharQuadro(true));
  requestAnimationFrame(laco);
  vigiar();
})();
