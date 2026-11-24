/* seu editor · interface
   Lê e grava o projeto pelo servidor local. O Claude mexe no mesmo arquivo
   pela linha de comando, e a interface recarrega sozinha quando percebe a
   mudança. O que aparece por cima do vídeo é desenhado por motion.js, o
   mesmo arquivo que a exportação usa. */

const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

const RITMOS = {
  calmo: { pausa_max: 0.70, folga: 0.16 },
  natural: { pausa_max: 0.40, folga: 0.10 },
  acelerado: { pausa_max: 0.18, folga: 0.06 },
};
const NOMES_TIPO = { impacto: "palavra de impacto", imagem: "foto", video: "vídeo", desenho: "desenho", texto: "texto", efeito: "efeito", som: "efeito sonoro" };
const NOMES_EFEITO = { zoom: "zoom rápido", tremida: "tremida", flash: "flash" };

const S = {
  proj: null, mtime: null, plano: null, estilos: null,
  modo: "ouvir", aba: "cortes", sujo: false, salvando: false,
  selIni: null, selFim: null, arrastando: false,
  sel: null, insertos: [], ultimoExport: null, estadoMsg: "",
};

const video = $("#video");
const fundo = $("#fundo");

/* ============================================================ oncinha do site */
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

/* ============================================================ utilidades */
const fmt = t => { t = Math.max(0, t || 0); const m = Math.floor(t / 60); const s = t - m * 60; return `${m}:${s.toFixed(1).padStart(4, "0")}`; };
const fmtCurto = t => { t = Math.max(0, t || 0); const m = Math.floor(t / 60); const s = Math.floor(t - m * 60); return `${m}:${String(s).padStart(2, "0")}`; };
const seg = n => `${(+n).toFixed(1).replace(".", ",")}s`;
const esc = t => String(t ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const limpa = t => String(t || "").replace(/^[\s"'“”(]+|[\s"'“”).,;:!?…]+$/g, "");
const novoId = p => p + Math.random().toString(36).slice(2, 7);

let tAviso;
function aviso(txt) {
  const el = $("#aviso"); el.textContent = txt; el.classList.add("mostra");
  clearTimeout(tAviso); tAviso = setTimeout(() => el.classList.remove("mostra"), 3200);
}

async function api(metodo, rota, corpo, bruto) {
  const r = await fetch(rota, {
    method: metodo,
    headers: corpo && !bruto ? { "Content-Type": "application/json" } : {},
    body: bruto ? corpo : (corpo ? JSON.stringify(corpo) : undefined),
  });
  const dados = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, dados };
}

/* ============================================================ salvar e plano */
let tSalvar, tPlano;
function mudou({ transcricao = false, controles = true } = {}) {
  S.sujo = true;
  registrar();
  clearTimeout(tSalvar); tSalvar = setTimeout(salvar, 450);
  clearTimeout(tPlano); tPlano = setTimeout(atualizarPlano, 50);
  if (transcricao) desenharTranscricao();
  if (controles) desenharControles();
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
  desenharResumo();
  desenharTrilhas();
  desenharOnda();
  if (S.sel) desenharEditorCamada(false);
}

async function recarregar() {
  const r = await api("GET", "/api/projeto");
  S.proj = r.dados.projeto; S.mtime = r.dados.mtime;
  tudo();
  registrar();
}

function tudo() {
  desenharControles();
  desenharTranscricao();
  desenharKits();
  desenharPaleta();
  desenharVisuais();
  desenharCor();
  desenharTrilhaFundo();
  atualizarPlano();
  if (S.sel && !camada(S.sel)) { S.sel = null; $("#editor-camada").hidden = true; }
  else if (S.sel) desenharEditorCamada(true);
}

/* ============================================================ tempo: original <-> editado */
function segDe(t) {
  for (const s of S.plano?.segmentos || []) if (t >= s.ini - 0.0005 && t < s.fim) return s;
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
function palavraAtual() {
  const t = video.currentTime;
  const pal = S.proj.palavras.filter(p => !p.cortada);
  return pal.find(p => p.fim > t) || pal[pal.length - 1] || null;
}
function palavraMaisPerto(out) {
  let melhor = null, dist = 1e9;
  for (const p of S.proj.palavras) {
    if (p.cortada) continue;
    const d = Math.abs(paraSaida(p.ini) - out);
    if (d < dist) { dist = d; melhor = p; }
  }
  return melhor;
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
function irParaSaida(out) { video.currentTime = paraOriginal(out); }

function laco() {
  const segs = S.plano?.segmentos || [];
  const t = video.currentTime;
  if (!video.paused && segs.length && !segDe(t)) {
    const prox = segs.find(s => s.ini > t - 0.001);
    if (prox) video.currentTime = prox.ini; else { video.pause(); video.currentTime = segs[0].ini; }
  }
  if (S.proj?.formato?.enquadramento === "ajustar") {
    if (Math.abs(fundo.currentTime - video.currentTime) > 0.2) fundo.currentTime = video.currentTime;
    if (video.paused !== fundo.paused) video.paused ? fundo.pause() : fundo.play().catch(() => {});
  }
  desenharQuadro();
  efeitosPrevia();
  requestAnimationFrame(laco);
}

video.addEventListener("play", () => { $("#celular").classList.add("tocando"); $("#btn-play").textContent = "❚❚"; });
video.addEventListener("pause", () => { $("#celular").classList.remove("tocando"); $("#btn-play").textContent = "▶"; });
$("#btn-play").onclick = alternar;
$("#play-grande").onclick = tocar;
$("#celular").addEventListener("click", e => { if (e.target.id !== "play-grande" && !e.target.closest("[data-id]")) alternar(); });
$("#linha-tempo").addEventListener("click", e => {
  const r = e.currentTarget.getBoundingClientRect();
  irParaSaida((e.clientX - r.left) / r.width * (S.plano?.duracao_saida || 0));
});
document.addEventListener("keydown", e => {
  if (e.target.matches("input, textarea, select")) return;
  if (e.code === "Space") { e.preventDefault(); alternar(); }
  if ((e.key === "Delete" || e.key === "Backspace") && S.sel && S.aba === "camadas") { apagarCamada(S.sel); }
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? refazer() : desfazer(); }
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "y") { e.preventDefault(); refazer(); }
});

/* ============================================================ quadro (motion.js) */
let escalaAtual = 1;
function desenharQuadro() {
  if (!S.plano || !S.estilos) return;
  const tela = $("#tela");
  const w = $("#sobreposicao").clientWidth;
  escalaAtual = w / 1080;
  tela.style.transform = `scale(${escalaAtual})`;
  const out = paraSaida(video.currentTime);
  const total = S.plano.duracao_saida || 0;
  $("#tempo").textContent = `${fmtCurto(out)} / ${fmtCurto(total)}`;
  $("#preenchido").style.width = total ? `${Math.min(100, out / total * 100)}%` : "0";
  const temAtras = (S.plano.camadas || []).some(c => c.atras);
  const ctx = { proj: S.proj, plano: S.plano, base: "", videos: true, tocando: !video.paused,
                selecionada: S.aba === "camadas" ? S.sel : null };
  const telaAtras = $("#tela-atras");
  telaAtras.style.transform = `scale(${escalaAtual})`;
  Motion.cena(telaAtras, { ...ctx, camada: temAtras ? "atras" : "atras-nada" }, out);
  Motion.cena(tela, { ...ctx, camada: temAtras ? "frente" : null }, out);
  sincronizarRecortes(temAtras);
  const ag = $("#trilhas .agulha");
  if (ag && total) ag.style.left = (out / total * 100) + "%";
  marcarPalavraAtual();
}

let palavraAgora = null;
function marcarPalavraAtual() {
  const t = video.currentTime;
  let achada = null;
  for (const p of S.proj?.palavras || []) { if (t >= p.ini && t < p.fim + 0.05) { achada = p.i; break; } if (p.ini > t) break; }
  if (achada === palavraAgora) return;
  if (palavraAgora !== null) document.querySelector(`.w[data-i="${palavraAgora}"]`)?.classList.remove("agora");
  palavraAgora = achada;
  const el = achada !== null ? document.querySelector(`.w[data-i="${achada}"]`) : null;
  if (el) {
    el.classList.add("agora");
    if (!video.paused && S.aba === "cortes") {
      const r = el.getBoundingClientRect();
      if (r.top < 140 || r.bottom > innerHeight - 40) el.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }
}

/* arrastar camadas direto na prévia */
let arrasteTela = null;
for (const sel of ["#tela", "#tela-atras"]) $(sel).addEventListener("pointerdown", e => {
  const el = e.target.closest("[data-id]"); if (!el || S.aba !== "camadas") return;
  e.preventDefault(); e.stopPropagation();
  const c = camada(el.dataset.id); if (!c) return;
  video.pause();
  selecionar(c.id);
  arrasteTela = { c, x0: e.clientX, y0: e.clientY, cx: c.x ?? .5, cy: c.y ?? .5 };
});
document.addEventListener("pointermove", e => {
  if (!arrasteTela) return;
  const { c, x0, y0, cx, cy } = arrasteTela;
  c.x = Math.round(Math.min(1, Math.max(0, cx + (e.clientX - x0) / escalaAtual / 1080)) * 1000) / 1000;
  c.y = Math.round(Math.min(1, Math.max(0, cy + (e.clientY - y0) / escalaAtual / 1920)) * 1000) / 1000;
  mudou({ controles: false });
});
document.addEventListener("pointerup", () => { if (arrasteTela) { arrasteTela = null; desenharEditorCamada(true); } });

/* ============================================================ resumo */
function desenharResumo() {
  const p = S.plano; if (!p) return;
  const economia = Math.max(0, p.duracao_original - p.duracao_saida);
  $("#economia-txt").textContent = "−" + seg(economia);
  $("#resumo-corte").textContent = `${seg(p.duracao_original)} viraram ${seg(p.duracao_saida)} · ${p.cortes} ${p.cortes === 1 ? "corte" : "cortes"}`;
}

/* ============================================================ componentes de controle */
function controleCor(valor, aoMudar) {
  const caixa = document.createElement("div");
  caixa.className = "cor-ctrl";
  const desenhar = v => {
    caixa.innerHTML = (S.proj.marca.cores || []).map(c =>
      `<button type="button" class="amostra${c.toUpperCase() === (v || "").toUpperCase() ? " ativa" : ""}" style="background:${c}" data-cor="${c}" title="${c}"></button>`).join("")
      + `<label class="espectro" title="qualquer cor"><input type="color" value="${/^#[0-9a-f]{6}$/i.test(v) ? v : "#ffffff"}"></label>`;
  };
  desenhar(valor);
  caixa.addEventListener("click", e => { const c = e.target.dataset.cor; if (c) { desenhar(c); aoMudar(c); } });
  caixa.addEventListener("input", e => { if (e.target.type === "color") { aoMudar(e.target.value.toUpperCase()); } });
  caixa.addEventListener("change", e => { if (e.target.type === "color") desenhar(e.target.value.toUpperCase()); });
  return caixa;
}

function campoFaixa(rotulo, min, max, passo, valor, formato, aoMudar, largo) {
  const l = document.createElement("label");
  l.className = "campo" + (largo ? " largo" : "");
  l.innerHTML = `<span>${rotulo} <output>${formato(valor)}</output></span><input type="range" min="${min}" max="${max}" step="${passo}" value="${valor}">`;
  l.querySelector("input").addEventListener("input", e => { l.querySelector("output").textContent = formato(+e.target.value); aoMudar(+e.target.value); });
  return l;
}
function campoChave(rotulo, valor, aoMudar) {
  const l = document.createElement("label");
  l.className = "interruptor";
  l.innerHTML = `<input type="checkbox" ${valor ? "checked" : ""}><span></span> ${rotulo}`;
  l.querySelector("input").addEventListener("change", e => aoMudar(e.target.checked));
  return l;
}
function campoPilulas(opcoes, valor, aoMudar) {
  const d = document.createElement("div");
  d.className = "pilulas";
  d.innerHTML = opcoes.map(([v, nome]) => `<button type="button" class="pilula${v === valor ? " ativa" : ""}" data-v="${v}">${esc(nome)}</button>`).join("");
  d.addEventListener("click", e => {
    const b = e.target.closest(".pilula"); if (!b) return;
    d.querySelectorAll(".pilula").forEach(x => x.classList.toggle("ativa", x === b));
    aoMudar(b.dataset.v);
  });
  return d;
}
function linha(rotulo, conteudo) {
  const d = document.createElement("div"); d.className = "linha-opcoes largo";
  d.innerHTML = `<span class="mini-rotulo">${rotulo}</span>`; d.appendChild(conteudo); return d;
}

function opcoesFonte(valor, comPapeis = true) {
  const F = S.estilos.fontes, f = S.proj.fontes;
  let html = "";
  if (comPapeis) {
    html += `<optgroup label="do estilo">
      <option value="@destaque" ${valor === "@destaque" ? "selected" : ""}>fonte de destaque (${esc(F[f.destaque]?.nome || f.destaque)})</option>
      <option value="@texto" ${valor === "@texto" ? "selected" : ""}>fonte de texto (${esc(F[f.texto]?.nome || f.texto)})</option></optgroup>`;
  }
  const da = Object.entries(F).filter(([, x]) => x.da_pessoa), nossas = Object.entries(F).filter(([, x]) => !x.da_pessoa);
  const opt = ([id, x]) => `<option value="${id}" ${valor === id ? "selected" : ""} style="font-family:${esc(x.familia)};font-weight:${x.peso}">${esc(x.nome)}</option>`;
  if (da.length) html += `<optgroup label="suas fontes">${da.map(opt).join("")}</optgroup>`;
  html += `<optgroup label="fontes">${nossas.map(opt).join("")}</optgroup>`;
  return html;
}

/* editor completo de visual de texto: fonte, tamanho, cor, contorno, sombra,
   brilho, fundo, entrelinhas e espaçamento */
function editorVisual(alvo, visual, aoMudar, { tamanho = [20, 220], fonteComPapeis = true } = {}) {
  alvo.innerHTML = "";
  const v = visual;
  const grade = document.createElement("div"); grade.className = "vis";
  const set = (k, val, redesenhar) => { aoMudar(k, val); if (redesenhar) editorVisual(alvo, { ...v, [k]: val }, aoMudar, { tamanho, fonteComPapeis }); };

  const lf = document.createElement("label"); lf.className = "campo";
  lf.innerHTML = `fonte <select>${opcoesFonte(v.fonte, fonteComPapeis)}</select>`;
  lf.querySelector("select").onchange = e => set("fonte", e.target.value);
  grade.appendChild(lf);
  grade.appendChild(campoFaixa("tamanho", tamanho[0], tamanho[1], 1, v.tamanho, x => x + "px", x => set("tamanho", x)));
  grade.appendChild(linha("cor do texto", controleCor(v.cor, c => set("cor", c))));

  const estilos = document.createElement("div"); estilos.className = "largo linha-opcoes";
  estilos.appendChild(campoChave("caixa alta", v.caixa_alta, x => set("caixa_alta", x)));
  estilos.appendChild(campoChave("itálico", v.italico, x => set("italico", x)));
  estilos.appendChild(campoChave("sombra", v.sombra, x => set("sombra", x)));
  estilos.appendChild(campoChave("brilho", v.brilho, x => set("brilho", x)));
  grade.appendChild(estilos);

  const cont = document.createElement("div"); cont.className = "largo linha-opcoes";
  cont.appendChild(campoChave("contorno", v.contorno, x => set("contorno", x, true)));
  if (v.contorno) {
    cont.appendChild(campoFaixa("espessura", 1, 18, 1, v.espessura || 6, x => x + "px", x => set("espessura", x)));
    cont.appendChild(controleCor(v.cor_contorno || "#000000", c => set("cor_contorno", c)));
  }
  grade.appendChild(cont);

  grade.appendChild(linha("fundo", campoPilulas([["nenhum", "sem fundo"], ["caixa", "caixa por linha"], ["pilula", "pílula"]], v.fundo || "nenhum", x => set("fundo", x, true))));
  if (v.fundo && v.fundo !== "nenhum") grade.appendChild(linha("cor do fundo", controleCor(v.cor_fundo || "#FFFFFF", c => set("cor_fundo", c))));

  grade.appendChild(campoFaixa("espaço entre linhas", 0.7, 2.2, 0.02, v.entrelinhas ?? 1.14, x => x.toFixed(2).replace(".", ","), x => set("entrelinhas", x)));
  grade.appendChild(campoFaixa("espaço entre letras", -10, 40, 1, v.espacamento || 0, x => (x > 0 ? "+" : "") + x, x => set("espacamento", x)));
  alvo.appendChild(grade);
}

function desenharVisuais() {
  const leg = S.proj.legenda.visual;
  editorVisual($("#visual-legenda"), leg, (k, val) => { leg[k] = val; mudou({ controles: false }); }, { tamanho: [24, 160] });
  const g = S.proj.gancho.visual;
  editorVisual($("#visual-gancho"), g, (k, val) => { g[k] = val; mudou({ controles: false }); }, { tamanho: [24, 160] });
  const cd = $("#l-cor-destaque"); cd.innerHTML = "";
  cd.appendChild(controleCor(leg.cor_destaque, c => { leg.cor_destaque = c; mudou({ controles: false }); }));
}

/* ============================================================ controles gerais */
function desenharControles() {
  const pj = S.proj; if (!pj) return;
  const aj = pj.ajustes;
  $$("#ritmos .pilula").forEach(b => b.classList.toggle("ativa", b.dataset.ritmo === aj.ritmo));
  $("#r-pausa").value = aj.pausa_max; $("#o-pausa").textContent = seg(aj.pausa_max);
  $("#r-folga").value = aj.folga; $("#o-folga").textContent = seg(aj.folga);
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
  $("#g-dur").value = g.duracao; $("#o-gdur").textContent = seg(g.duracao);
  $("#g-pos").value = g.posicao ?? 0.2; $("#o-gpos").textContent = Math.round((g.posicao ?? 0.2) * 100) + "%";
  const sug = pj.sugestoes?.ganchos || [];
  $("#sugestoes").innerHTML = sug.length ? `<p>sugestões do claude, clique pra usar</p>` + sug.map((t, k) => `<button class="sugestao" data-k="${k}">${esc(t)}</button>`).join("") : "";

  const l = pj.legenda, lv = l.visual;
  $("#l-ativa").checked = l.ativa !== false;
  $("#l-pal").value = lv.palavras || 3; $("#o-lpal").textContent = lv.palavras || 3;
  $("#l-pos").value = l.posicao; $("#o-lpos").textContent = Math.round(l.posicao * 100) + "%";
  $$("#l-ativa-modo .pilula").forEach(b => b.classList.toggle("ativa", b.dataset.v === (lv.modo_ativa || "cor")));
  $$("#l-anim .pilula").forEach(b => b.classList.toggle("ativa", b.dataset.v === (lv.animacao || "pop")));
  $("#l-pont").checked = l.sem_pontuacao !== false;

  $$("#enquadramento .pilula").forEach(b => b.classList.toggle("ativa", b.dataset.enq === pj.formato.enquadramento));
  $("#celular").classList.toggle("ajustar", pj.formato.enquadramento === "ajustar");
  $("#f-volume").checked = pj.formato.volume !== false;

  const grupos = {};
  for (const p of pj.palavras) if (p.cortada && p.origem !== "voce") (grupos[p.motivo || "claude"] ||= []).push(p.i);
  const chaves = Object.keys(grupos);
  $("#cortes-claude").hidden = !chaves.length;
  $("#cortes-claude").innerHTML = chaves.length ? `<p class="rotulo">o que já saiu</p>` + chaves.map(m =>
    `<div class="linha"><span><span class="motivo">${esc(m)}</span> ${grupos[m].length} ${grupos[m].length === 1 ? "palavra" : "palavras"}</span>
     <button class="btn borda pequeno" data-desfazer="${esc(m)}">trazer de volta</button></div>`).join("") : "";
}

/* ============================================================ transcrição */
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
  const partes = ['<p class="paragrafo">'];
  let motivoAnterior = null;
  pj.palavras.forEach((p, k) => {
    if (k) {
      const gap = p.ini - pj.palavras[k - 1].fim;
      if (gap > 1.4) partes.push('</p><p class="paragrafo">');
      if (gap > 0.25) partes.push(`<span class="pausa${aj.cortar_pausas && gap > aj.pausa_max ? " cortada" : ""}">${seg(gap)}</span>`);
    }
    const m = p.cortada ? (p.motivo || "") : null;
    if (m && m !== motivoAnterior && m !== "você") partes.push(`<span class="motivo${p.origem === "auto" ? " auto" : ""}">${esc(m)}</span>`);
    motivoAnterior = m;
    const cls = ["w"];
    if (p.cortada) cls.push("cortada");
    if (p.destaque) cls.push("destaque");
    partes.push(`<span class="${cls.join(" ")}" data-i="${p.i}" title="${fmt(p.ini)}">${esc(p.t)}</span> `);
  });
  partes.push("</p>");
  el.innerHTML = partes.join("");
  palavraAgora = null;
}

$("#transcricao").addEventListener("pointerdown", e => {
  const w = e.target.closest(".w"); if (!w) return;
  const i = +w.dataset.i;
  if (S.modo === "ouvir") { video.currentTime = S.proj.palavras[i].ini; tocar(); return; }
  S.arrastando = true; S.selIni = S.selFim = i; marcarSelecao();
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
  mudou({ transcricao: true });
});
function marcarSelecao() {
  $$(".w.sel").forEach(el => el.classList.remove("sel"));
  const a = Math.min(S.selIni, S.selFim), b = Math.max(S.selIni, S.selFim);
  for (let i = a; i <= b; i++) document.querySelector(`.w[data-i="${i}"]`)?.classList.add("sel");
}

/* ============================================================ estilo: duplas de fontes */
function desenharKits() {
  const F = S.estilos.fontes, f = S.proj.fontes;
  $("#kits").innerHTML = S.estilos.kits.map(k => {
    const d = F[k.destaque], t = F[k.texto];
    return `<button class="kit${f.kit === k.id ? " ativa" : ""}" data-kit="${k.id}">
      <span class="kit-nome">${esc(k.nome)}</span>
      <span class="kit-destaque" style="font-family:${esc(d.familia)};font-weight:${d.peso}">seu gancho aqui</span>
      <span class="kit-texto" style="font-family:${esc(t.familia)};font-weight:${t.peso}">e a legenda acompanha a fala assim</span>
      <span class="kit-fontes">${esc(d.nome)} + ${esc(t.nome)}</span></button>`;
  }).join("");
  $("#f-destaque").innerHTML = opcoesFonte(f.destaque, false);
  $("#f-texto").innerHTML = opcoesFonte(f.texto, false);
}
$("#kits").onclick = e => {
  const b = e.target.closest(".kit"); if (!b) return;
  const k = S.estilos.kits.find(x => x.id === b.dataset.kit);
  Object.assign(S.proj.fontes, { kit: k.id, destaque: k.destaque, texto: k.texto });
  desenharKits(); desenharVisuais(); mudou();
};
$("#f-destaque").onchange = e => { Object.assign(S.proj.fontes, { destaque: e.target.value, kit: "personalizado" }); desenharKits(); desenharVisuais(); mudou(); };
$("#f-texto").onchange = e => { Object.assign(S.proj.fontes, { texto: e.target.value, kit: "personalizado" }); desenharKits(); desenharVisuais(); mudou(); };
$("#enviar-fonte").onchange = async e => {
  const arq = e.target.files[0]; if (!arq) return;
  const nome = (prompt("nome dessa fonte:", arq.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ")) || "").trim();
  if (!nome) return;
  const r = await api("POST", `/api/fontes?arquivo=${encodeURIComponent(arq.name)}&nome=${encodeURIComponent(nome)}`, arq, true);
  e.target.value = "";
  if (!r.ok) { aviso(r.dados.erro || "não consegui instalar a fonte"); return; }
  S.estilos = (await api("GET", "/api/estilos")).dados;
  Motion.configurar(S.estilos);
  desenharKits(); desenharVisuais();
  aviso(`fonte ${nome} instalada, ela já aparece nas listas`);
};

function desenharPaleta() {
  const cores = S.proj.marca.cores;
  $("#paleta-marca").innerHTML = cores.map((c, k) =>
    `<span class="cor-marca" style="background:${c}" title="${c}"><input type="color" value="${c}" data-k="${k}"><button data-tirar="${k}" title="tirar">×</button></span>`).join("")
    + `<button class="mais" id="mais-cor" title="acrescentar cor">+</button>`;
}
$("#paleta-marca").addEventListener("input", e => {
  const k = e.target.dataset.k; if (k === undefined) return;
  S.proj.marca.cores[+k] = e.target.value.toUpperCase();
  e.target.parentElement.style.background = e.target.value;
  mudou({ controles: false });
});
$("#paleta-marca").addEventListener("change", () => { desenharVisuais(); if (S.sel) desenharEditorCamada(true); });
$("#paleta-marca").addEventListener("click", e => {
  if (e.target.id === "mais-cor") { S.proj.marca.cores.push("#FB76B2"); desenharPaleta(); desenharVisuais(); mudou({ controles: false }); }
  const k = e.target.dataset.tirar;
  if (k !== undefined) { e.preventDefault(); S.proj.marca.cores.splice(+k, 1); desenharPaleta(); desenharVisuais(); mudou({ controles: false }); }
});

/* ============================================================ camadas */
const camada = id => (S.proj.camadas || []).find(c => c.id === id);
const camadaNoPlano = id => (S.plano?.camadas || []).find(c => c.id === id);

async function listarInsertos() {
  const r = await api("GET", "/api/insertos");
  S.insertos = r.dados.itens || [];
  $("#insertos").innerHTML = S.insertos.map(it => {
    const src = "/insertos/" + encodeURIComponent(it.nome);
    const midia = it.tipo === "video" ? `<video src="${src}#t=0.5" muted preload="metadata"></video>`
      : it.tipo === "audio" ? `<span class="icone-audio">♫</span>` : `<img src="${src}" alt="" loading="lazy">`;
    return `<button class="inserto" data-nome="${esc(it.nome)}" data-tipo="${it.tipo}" title="${esc(it.nome)}">${midia}<span class="selo-tipo">${{ video: "vídeo", audio: "música", imagem: "foto" }[it.tipo]}</span></button>`;
  }).join("");
}

async function enviarInsertos(arquivos) {
  let n = 0;
  for (const f of arquivos) {
    aviso(`enviando ${f.name}`);
    const r = await api("POST", `/api/insertos?nome=${encodeURIComponent(f.name)}`, f, true);
    if (r.ok) n++; else aviso(r.dados.erro || `não deu pra enviar ${f.name}`);
  }
  await listarInsertos();
  desenharTrilhaFundo();
  if (n) aviso(`${n} ${n === 1 ? "arquivo enviado" : "arquivos enviados"}. clique pra colocar no vídeo`);
}
$("#enviar-insertos").onchange = e => { enviarInsertos([...e.target.files]); e.target.value = ""; };
const cartaoInsertos = $("#insertos").closest(".cartao");
cartaoInsertos.addEventListener("dragover", e => { e.preventDefault(); cartaoInsertos.classList.add("solta-aqui"); });
cartaoInsertos.addEventListener("dragleave", () => cartaoInsertos.classList.remove("solta-aqui"));
cartaoInsertos.addEventListener("drop", e => { e.preventDefault(); cartaoInsertos.classList.remove("solta-aqui"); enviarInsertos([...e.dataTransfer.files]); });

$("#buscar-link").onclick = async () => {
  const link = $("#link-insertos").value.trim(); if (!link) { aviso("cole o link primeiro"); return; }
  const r = await api("POST", "/api/insertos-link", { link });
  if (!r.ok) { aviso(r.dados.erro || "não deu"); return; }
  $("#link-insertos").value = "";
  aviso("trazendo os insertos, eles aparecem aqui quando chegarem");
};

let ladoCartao = 1;
$("#insertos").onclick = e => {
  const b = e.target.closest(".inserto"); if (!b) return;
  if (b.dataset.tipo === "audio") {
    Object.assign(S.proj.trilha, { arquivo: b.dataset.nome });
    desenharTrilhaFundo(); mudou(); aviso("música colocada como trilha de fundo");
    return;
  }
  const p = palavraAtual(); if (!p) return;
  ladoCartao *= -1;
  const c = b.dataset.tipo === "video"
    ? { id: novoId("vid"), tipo: "video", arquivo: b.dataset.nome, modo: "tela", palavra: p.i, duracao: 3, inicio_clip: 0, x: .5, y: .4, tamanho: .5, rot: 0 }
    : { id: novoId("img"), tipo: "imagem", arquivo: b.dataset.nome, modo: "cartao", palavra: p.i, duracao: 2.5, x: ladoCartao > 0 ? .7 : .3, y: .3, tamanho: .36, rot: ladoCartao * 6, entrada: "pop" };
  adicionarCamada(c);
};

$$(".adicionar [data-novo]").forEach(b => b.onclick = () => {
  const p = palavraAtual(); if (!p) { aviso("espere a transcrição terminar"); return; }
  const tipo = b.dataset.novo;
  let c;
  if (tipo === "impacto") c = { id: novoId("imp"), tipo: "impacto", estilo: "pincel", texto: limpa(p.t) || "uau", palavra: p.i, duracao: 1.6, x: .5, y: .42, tamanho: 1 };
  if (tipo === "desenho") c = { id: novoId("des"), tipo: "desenho", forma: "circulo", cor: "#E8352E", palavra: p.i, duracao: 2, x: .5, y: .45, tamanho: .7, espessura: 12, rot: 0 };
  if (tipo === "texto") c = { id: novoId("txt"), tipo: "texto", estilo: "frase", texto: "seu texto aqui", palavra: p.i, duracao: 3, x: .5, y: .3, tamanho: 1 };
  if (tipo === "cta") c = { id: novoId("txt"), tipo: "texto", estilo: "cta", texto: "comenta EU QUERO", ini: 0, ate_o_fim: true, x: .5, y: .8, tamanho: 1 };
  if (tipo === "efeito") c = { id: novoId("efe"), tipo: "efeito", efeito: "zoom", palavra: p.i, duracao: 1.2, intensidade: 1.18, x: .5, y: .42 };
  if (tipo === "som") c = { id: novoId("som"), tipo: "som", som: "whoosh", palavra: p.i, volume: .8 };
  adicionarCamada(c);
});

function adicionarCamada(c) {
  (S.proj.camadas ||= []).push(c);
  video.pause();
  selecionar(c.id);
  mudou();
}
function apagarCamada(id) {
  S.proj.camadas = S.proj.camadas.filter(c => c.id !== id);
  S.sel = null; $("#editor-camada").hidden = true;
  mudou();
}
function selecionar(id) {
  S.sel = id;
  desenharEditorCamada(true);
  desenharTrilhas();
}

/* linha do tempo */
function desenharTrilhas() {
  const alvo = $("#trilhas"); if (!alvo || !S.plano) return;
  const total = S.plano.duracao_saida || 1;
  const lista = [...(S.plano.camadas || [])].sort((a, b) => a.ini_out - b.ini_out);
  const faixas = [];
  for (const c of lista) {
    let f = faixas.findIndex(fim => fim <= c.ini_out + 0.01);
    if (f < 0) { faixas.push(0); f = faixas.length - 1; }
    faixas[f] = c.fim_out; c._faixa = f;
  }
  const passo = total > 60 ? 10 : total > 20 ? 5 : 2;
  let regua = "";
  for (let t = 0; t <= total; t += passo) regua += `<span style="left:${t / total * 100}%">${fmtCurto(t)}</span>`;
  let html = `<div class="regua" id="regua">${regua}</div><div class="agulha"></div>`;
  for (let f = 0; f < Math.max(1, faixas.length); f++) {
    html += `<div class="faixa">` + lista.filter(c => c._faixa === f).map(c => {
      const nome = c.texto || c.arquivo || (S.estilos.desenhos[c.forma]?.nome) || NOMES_EFEITO[c.efeito] || (c.tipo === "som" ? "♪ " + c.som : NOMES_TIPO[c.tipo]);
      return `<div class="barra-camada ${c.tipo}${c.id === S.sel ? " sel" : ""}" data-id="${c.id}"
        style="left:${c.ini_out / total * 100}%;width:${(c.fim_out - c.ini_out) / total * 100}%" title="${esc(nome)}">${esc(String(nome).replace(/\|/g, " "))}<span class="ponta"></span></div>`;
    }).join("") + `</div>`;
  }
  alvo.innerHTML = html;
}

let arrasteBarra = null;
$("#trilhas").addEventListener("pointerdown", e => {
  const alvo = $("#trilhas");
  const total = S.plano?.duracao_saida || 1;
  const r = alvo.getBoundingClientRect();
  if (e.target.closest("#regua")) { irParaSaida((e.clientX - r.left) / r.width * total); return; }
  const barra = e.target.closest(".barra-camada"); if (!barra) return;
  const c = camada(barra.dataset.id), cp = camadaNoPlano(barra.dataset.id); if (!c || !cp) return;
  e.preventDefault();
  selecionar(c.id);
  video.pause();
  irParaSaida(cp.ini_out + 0.05);
  arrasteBarra = { c, cp, ponta: !!e.target.closest(".ponta"), x0: e.clientX, largura: r.width, total };
});
document.addEventListener("pointermove", e => {
  if (!arrasteBarra) return;
  const { c, cp, ponta, x0, largura, total } = arrasteBarra;
  const dt = (e.clientX - x0) / largura * total;
  if (ponta) {
    c.duracao = Math.max(0.3, Math.round((cp.fim_out - cp.ini_out + dt) * 10) / 10);
    delete c.ate_o_fim;
  } else {
    const novo = Math.max(0, cp.ini_out + dt);
    if (c.palavra !== undefined && c.palavra !== null) {
      const p = palavraMaisPerto(novo); if (p) { c.palavra = p.i; delete c.atraso; }
    } else c.ini = Math.round(novo * 10) / 10;
  }
  mudou({ controles: false });
});
document.addEventListener("pointerup", () => { if (arrasteBarra) { arrasteBarra = null; desenharEditorCamada(true); } });

/* editor da camada selecionada */
function desenharEditorCamada(forcar) {
  const ed = $("#editor-camada");
  const c = S.sel && camada(S.sel);
  if (!c) { ed.hidden = true; return; }
  if (!forcar && ed.dataset.id === c.id) return;
  ed.hidden = false; ed.dataset.id = c.id;
  const cp = camadaNoPlano(c.id);
  const mexe = (k, v) => { if (v === null) delete c[k]; else c[k] = v; mudou({ controles: false }); };
  ed.innerHTML = `<div class="topo-editor">
      <p class="rotulo" style="margin:0">${NOMES_TIPO[c.tipo]}${cp ? ` · entra em ${fmtCurto(cp.ini_out)}` : ""}</p>
      <div class="acoes"><button class="btn borda pequeno" data-acao="ir">ver na prévia</button>
      <button class="btn borda pequeno" data-acao="duplicar">duplicar</button>
      <button class="btn escuro pequeno" data-acao="apagar">apagar</button></div></div>`;
  const corpo = document.createElement("div"); corpo.className = "vis";

  if (c.tipo === "impacto" || c.tipo === "texto") {
    const ta = document.createElement("textarea"); ta.rows = 2; ta.value = c.texto || ""; ta.className = "largo";
    ta.placeholder = "texto ( | quebra a linha)";
    ta.oninput = () => mexe("texto", ta.value);
    corpo.appendChild(ta);
    const tabela = c.tipo === "impacto" ? S.estilos.impacto : S.estilos.textos;
    corpo.appendChild(linha(c.tipo === "impacto" ? "jeito" : "tipo", campoPilulas(Object.entries(tabela).map(([k, d]) => [k, d.nome]), c.estilo,
      v => { c.estilo = v; delete c.visual; delete c.entrada; delete c.rot; mudou({ controles: false }); setTimeout(() => desenharEditorCamada(true), 80); })));
  }
  if (c.tipo === "imagem" || c.tipo === "video") {
    const sel = document.createElement("label"); sel.className = "campo largo";
    sel.innerHTML = `arquivo <select>${S.insertos.filter(i => i.tipo === c.tipo).map(i => `<option ${i.nome === c.arquivo ? "selected" : ""}>${esc(i.nome)}</option>`).join("")}</select>`;
    sel.querySelector("select").onchange = e => mexe("arquivo", e.target.value);
    corpo.appendChild(sel);
    corpo.appendChild(linha("jeito", campoPilulas([["cartao", "cartão flutuando"], ["tela", "tela inteira"]], c.modo || "cartao", v => { mexe("modo", v); setTimeout(() => desenharEditorCamada(true), 80); })));
    if (c.tipo === "imagem" && c.modo !== "tela") {
      corpo.appendChild(linha("moldura", campoPilulas([["polaroid", "borda polaroid"], ["fita", "polaroid com fita"], ["arredondada", "cantos arredondados"], ["celular", "tela de celular"], ["sombra", "só a foto com sombra"], ["nenhuma", "só a foto"], ["sem", "png recortado"]], c.moldura || "polaroid", v => mexe("moldura", v))));
      corpo.appendChild(linha("movimento", campoPilulas([["", "parado"], ["flutua", "flutuando"], ["aproxima", "aproximando devagar"], ["gira", "girando devagar"]], c.movimento || "", v => mexe("movimento", v || null))));
    }
    if (c.tipo === "imagem" && c.modo !== "tela") corpo.appendChild(linha("formato", campoPilulas([["", "original"], ["4/5", "4:5"], ["1/1", "quadrado"], ["9/16", "9:16"]], c.proporcao || "", v => mexe("proporcao", v || null))));
    if (c.tipo === "imagem") {
      corpo.appendChild(campoFaixa("transparência", .1, 1, .05, c.opacidade ?? 1, x => Math.round((1 - x) * 100) + "%", v => mexe("opacidade", v)));
      corpo.appendChild(campoFaixa("bordas esfumadas", 0, 1, .05, c.esfumar || 0, x => x ? Math.round(x * 100) + "%" : "sem", v => mexe("esfumar", v || null)));
    }
    if (c.tipo === "video") corpo.appendChild(campoFaixa("começar o clipe no segundo", 0, 60, 0.1, c.inicio_clip || 0, seg, v => mexe("inicio_clip", v)));
  }
  if (c.tipo === "desenho") {
    corpo.appendChild(linha("forma", campoPilulas(Object.entries(S.estilos.desenhos).map(([k, d]) => [k, d.nome]), c.forma, v => mexe("forma", v))));
    corpo.appendChild(linha("cor", controleCor(c.cor || "#E8352E", v => mexe("cor", v))));
    corpo.appendChild(campoFaixa("espessura do traço", 3, 30, 1, c.espessura || 12, x => x + "px", v => mexe("espessura", v)));
  }
  if (c.tipo === "efeito") {
    corpo.appendChild(linha("efeito", campoPilulas(Object.entries(NOMES_EFEITO), c.efeito, v => { mexe("efeito", v); setTimeout(() => desenharEditorCamada(true), 80); })));
    if (c.efeito === "zoom") {
      corpo.appendChild(linha("jeito", campoPilulas([["suave", "suave"], ["seco", "seco, de uma vez"]], c.estilo || "suave", v => mexe("estilo", v))));
      corpo.appendChild(campoFaixa("quanto aproxima", 1.05, 1.6, .01, c.intensidade ?? 1.18, x => "+" + Math.round((x - 1) * 100) + "%", v => mexe("intensidade", v)));
      corpo.appendChild(campoFaixa("ponto de foco na horizontal", 0, 1, .01, c.x ?? .5, x => Math.round(x * 100) + "%", v => mexe("x", v)));
      corpo.appendChild(campoFaixa("ponto de foco na vertical", 0, 1, .01, c.y ?? .42, x => Math.round(x * 100) + "%", v => mexe("y", v)));
    } else if (c.efeito === "tremida") {
      corpo.appendChild(campoFaixa("força", .3, 3, .1, c.intensidade ?? 1, x => x.toFixed(1).replace(".", ","), v => mexe("intensidade", v)));
    } else {
      corpo.appendChild(linha("cor", controleCor(c.cor || "#FFFFFF", v => mexe("cor", v))));
      corpo.appendChild(campoFaixa("força", .2, 1, .05, c.intensidade ?? .9, x => Math.round(x * 100) + "%", v => mexe("intensidade", v)));
    }
  }
  if (c.tipo === "som") {
    corpo.appendChild(linha("som", campoPilulas(Object.keys(S.estilos.sons).map(k => [k, k]), c.som, v => { mexe("som", v); tocarSom(v, c.volume ?? .8); })));
    corpo.appendChild(campoFaixa("volume", .1, 1.5, .05, c.volume ?? .8, x => Math.round(x * 100) + "%", v => mexe("volume", v)));
  } else {
    corpo.appendChild(linha("som na entrada", campoPilulas([["", "nenhum"], ...Object.keys(S.estilos.sons).map(k => [k, k])], c.som || "",
      v => { mexe("som", v || null); if (v) tocarSom(v, c.som_volume ?? .8); })));
  }
  if (c.tipo !== "video" && c.tipo !== "desenho" && c.tipo !== "efeito" && c.tipo !== "som") {
    const ent = cp?.entrada || c.entrada || "pop";
    corpo.appendChild(linha("entrada", campoPilulas([["pop", "pop"], ["desliza", "sobe"], ["cai", "cai do alto"], ["esquerda", "vem da esquerda"], ["direita", "vem da direita"], ["fade", "aparece"], ["fadelento", "esmaece devagar"], ["escreve", "escrevendo"], ["nenhuma", "seco"]], ent, v => mexe("entrada", v))));
  }
  if (c.tipo === "impacto") corpo.appendChild(campoChave("ligar com linhas às fotos que estão na tela", c.ligar, v => mexe("ligar", v)));
  if (["impacto", "texto", "imagem", "video", "desenho"].includes(c.tipo)) {
    const at = campoChave("atrás da pessoa (recorta a pessoa do vídeo)", c.atras, v => { mexe("atras", v || null); if (v) aviso("recortando a pessoa pra prévia, leva alguns segundos"); });
    corpo.appendChild(at);
  }

  const telaInteira = (c.tipo === "imagem" || c.tipo === "video") && c.modo === "tela";
  if (!telaInteira && c.tipo !== "efeito" && c.tipo !== "som") {
    const tamDef = c.tipo === "desenho" || c.tipo === "imagem" || c.tipo === "video" ? [.1, 1.2, .01, c.tamanho ?? .36, x => Math.round(x * 100) + "% da largura"] : [.3, 3, .05, c.tamanho ?? 1, x => Math.round(x * 100) + "%"];
    corpo.appendChild(campoFaixa("tamanho", tamDef[0], tamDef[1], tamDef[2], tamDef[3], tamDef[4], v => mexe("tamanho", v)));
    corpo.appendChild(campoFaixa("inclinação", -30, 30, 1, c.rot ?? cp?.rot ?? 0, x => x + "°", v => mexe("rot", v)));
    corpo.appendChild(campoFaixa("posição na horizontal", 0, 1, .01, c.x ?? .5, x => Math.round(x * 100) + "%", v => mexe("x", v)));
    corpo.appendChild(campoFaixa("posição na vertical", 0, 1, .01, c.y ?? .5, x => Math.round(x * 100) + "%", v => mexe("y", v)));
  }
  if (c.tipo === "texto") corpo.appendChild(campoChave("fica até o fim do vídeo", c.ate_o_fim, v => { mexe("ate_o_fim", v || null); setTimeout(() => desenharEditorCamada(true), 80); }));
  if (!c.ate_o_fim && c.tipo !== "som") corpo.appendChild(campoFaixa("duração", .3, 12, .1, c.duracao ?? 2, seg, v => mexe("duracao", v)));
  ed.appendChild(corpo);

  if (c.tipo === "impacto" || c.tipo === "texto") {
    const tabela = c.tipo === "impacto" ? S.estilos.impacto : S.estilos.textos;
    const def = tabela[c.estilo] || Object.values(tabela)[0];
    const base = Object.assign({}, S.estilos.visual_padrao, def.visual, c.visual || {});
    const det = document.createElement("details"); det.className = "dobra"; det.open = true;
    det.innerHTML = "<summary>fonte, cor e contorno</summary>";
    const alvo = document.createElement("div"); det.appendChild(alvo);
    editorVisual(alvo, base, (k, val) => { (c.visual ||= {})[k] = val; mudou({ controles: false }); }, { tamanho: [20, 300] });
    ed.appendChild(det);
  }
  ed.querySelector("[data-acao=ir]").onclick = () => cp && irParaSaida(cp.ini_out + Math.min(.6, (cp.fim_out - cp.ini_out) / 2));
  ed.querySelector("[data-acao=duplicar]").onclick = () => {
    const n = JSON.parse(JSON.stringify(c)); n.id = novoId(c.tipo.slice(0, 3));
    n.x = Math.min(.95, (n.x ?? .5) + .06); n.y = Math.min(.95, (n.y ?? .5) + .04);
    adicionarCamada(n);
  };
  ed.querySelector("[data-acao=apagar]").onclick = () => apagarCamada(c.id);
}

/* ============================================================ desfazer e refazer */
const H = { pilha: [], pos: -1, t: null, aplicando: false };
function registrar() {
  if (H.aplicando || !S.proj) return;
  clearTimeout(H.t);
  H.t = setTimeout(gravarHistorico, 350);
}
function gravarHistorico() {
  H.t = null;
  const foto = JSON.stringify(S.proj);
  if (H.pilha[H.pos] === foto) return;
  H.pilha = H.pilha.slice(0, H.pos + 1);
  H.pilha.push(foto);
  if (H.pilha.length > 150) H.pilha.shift();
  H.pos = H.pilha.length - 1;
  botoesHistorico();
}
function botoesHistorico() {
  $("#btn-desfazer").disabled = H.pos <= 0;
  $("#btn-refazer").disabled = H.pos >= H.pilha.length - 1;
}
function aplicarHistorico(pos) {
  H.aplicando = true;
  H.pos = pos;
  S.proj = JSON.parse(H.pilha[pos]);
  S.sujo = true;
  clearTimeout(tSalvar); tSalvar = setTimeout(salvar, 200);
  tudo();
  H.aplicando = false;
  botoesHistorico();
}
function desfazer() {
  if (H.t) { clearTimeout(H.t); gravarHistorico(); }
  if (H.pos > 0) { aplicarHistorico(H.pos - 1); aviso("desfeito"); }
}
function refazer() { if (H.pos < H.pilha.length - 1) { aplicarHistorico(H.pos + 1); aviso("refeito"); } }
$("#btn-desfazer").onclick = desfazer;
$("#btn-refazer").onclick = refazer;

/* ============================================================ linha do tempo com a onda do áudio */
let ONDA = null, selOnda = null;
async function carregarOnda() { ONDA = (await api("GET", "/api/onda")).dados; desenharOnda(); }
function larguraOnda() {
  const dur = S.proj?.info?.duracao || 1;
  return Math.max($("#onda-rolagem").clientWidth, Math.round(dur * 36));
}
function desenharOnda() {
  const cv = $("#onda"); if (!cv || !S.plano || !ONDA || !$("#onda-rolagem").clientWidth) return;
  const dur = S.proj.info.duracao || 1, w = larguraOnda(), h = 96, dpr = devicePixelRatio || 1;
  cv.width = w * dpr; cv.height = h * dpr; cv.style.width = w + "px"; cv.style.height = h + "px";
  const g = cv.getContext("2d"); g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
  const ps = ONDA.picos, porS = ONDA.por_segundo;
  const px = t => t / dur * w;
  for (const c of S.proj.cortes_tempo || []) {
    const x0 = px(c.ini), x1 = px(c.fim);
    g.fillStyle = "#ffd0e3"; g.fillRect(x0, 0, x1 - x0, h);
    g.save(); g.beginPath(); g.rect(x0, 0, x1 - x0, h); g.clip();
    g.strokeStyle = "#fb76b2"; g.lineWidth = 1.5;
    for (let x = x0 - h; x < x1; x += 7) { g.beginPath(); g.moveTo(x, h); g.lineTo(x + h, 0); g.stroke(); }
    g.restore();
  }
  const barra = Math.max(1.5, w / (dur * 18));
  for (let x = 0; x < w; x += barra + 1) {
    const t = x / w * dur;
    const i0 = Math.floor(t * porS), i1 = Math.max(i0 + 1, Math.floor((x + barra) / w * dur * porS));
    let pico = 0; for (let i = i0; i < i1 && i < ps.length; i++) pico = Math.max(pico, ps[i]);
    const alt = Math.max(2, Math.min(1, pico * 1.6) * (h - 16));
    g.fillStyle = segDe(t) ? "#2b2b2b" : "#cfcfcf";
    g.fillRect(x, (h - alt) / 2, barra, alt);
  }
  if (selOnda) { g.fillStyle = "rgba(251,118,178,.35)"; g.fillRect(px(Math.min(selOnda.a, selOnda.b)), 0, Math.abs(px(selOnda.b) - px(selOnda.a)), h); }
  g.fillStyle = "#c2366f"; g.fillRect(px(video.currentTime) - 1, 0, 2, h);
}
function tempoOnda(e) {
  const r = $("#onda").getBoundingClientRect();
  return Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)) * (S.proj.info.duracao || 1);
}
$("#onda").addEventListener("pointerdown", e => { selOnda = { a: tempoOnda(e), b: tempoOnda(e) }; $("#onda").setPointerCapture(e.pointerId); });
$("#onda").addEventListener("pointermove", e => { if (selOnda) { selOnda.b = tempoOnda(e); desenharOnda(); } });
$("#onda").addEventListener("pointerup", () => {
  if (!selOnda) return;
  const a = Math.min(selOnda.a, selOnda.b), b = Math.max(selOnda.a, selOnda.b);
  selOnda = null;
  const lista = S.proj.cortes_tempo ||= [];
  if (b - a < 0.08) {
    const k = lista.findIndex(c => a >= c.ini && a <= c.fim);
    if (k >= 0) {
      const c = lista.splice(k, 1)[0];
      for (const p of S.proj.palavras) if (p.motivo === "linha do tempo" && p.ini >= c.ini - .01 && p.fim <= c.fim + .01) { p.cortada = false; delete p.motivo; }
      aviso("esse trecho voltou pro vídeo"); mudou({ transcricao: true }); return;
    }
    video.currentTime = a; desenharOnda(); return;
  }
  lista.push({ ini: Math.round(a * 1000) / 1000, fim: Math.round(b * 1000) / 1000 });
  lista.sort((x, y) => x.ini - y.ini);
  for (let i = lista.length - 1; i > 0; i--) if (lista[i].ini <= lista[i - 1].fim) { lista[i - 1].fim = Math.max(lista[i - 1].fim, lista[i].fim); lista.splice(i, 1); }
  for (const p of S.proj.palavras) { const m = (p.ini + p.fim) / 2; if (m >= a && m <= b && !p.cortada) { p.cortada = true; p.motivo = "linha do tempo"; p.origem = "voce"; } }
  aviso(`${seg(b - a)} cortados. se cortou demais, tem o desfazer`);
  mudou({ transcricao: true });
});

/* ============================================================ cor do vídeo */
function desenharCor() {
  const alvo = $("#cor"); if (!alvo || !S.proj) return;
  const c = S.proj.cor;
  alvo.innerHTML = "";
  const grade = document.createElement("div"); grade.className = "vis";
  const nomes = { nenhum: "original", quente: "quente", frio: "frio", vivo: "vivo", suave: "suave", filme: "filme", pb: "preto e branco" };
  grade.appendChild(linha("filtro", campoPilulas(Object.keys(S.estilos.filtros_cor).map(k => [k, nomes[k] || k]), c.filtro || "nenhum", v => {
    Object.assign(c, S.estilos.filtros_cor[v], { filtro: v }); mudou({ controles: false }); setTimeout(desenharCor, 50);
  })));
  const mexe = (k, v) => { c[k] = v; c.filtro = "personalizado"; mudou({ controles: false }); };
  grade.appendChild(campoFaixa("brilho", -.25, .25, .005, c.brilho || 0, x => (x > 0 ? "+" : "") + Math.round(x * 100), v => mexe("brilho", v)));
  grade.appendChild(campoFaixa("contraste", .6, 1.6, .01, c.contraste ?? 1, x => Math.round(x * 100) + "%", v => mexe("contraste", v)));
  grade.appendChild(campoFaixa("saturação", 0, 2, .01, c.saturacao ?? 1, x => Math.round(x * 100) + "%", v => mexe("saturacao", v)));
  grade.appendChild(campoFaixa("temperatura", -1, 1, .01, c.temperatura || 0, x => x > .02 ? "mais quente" : x < -.02 ? "mais fria" : "neutra", v => mexe("temperatura", v)));
  const auto = campoChave("correção automática ligada", c.auto, v => { c.auto = v; mudou({ controles: false }); });
  auto.classList.add("largo");
  grade.appendChild(auto);
  alvo.appendChild(grade);
}
$("#cor-auto").onclick = async e => {
  const b = e.currentTarget;
  b.disabled = true; b.textContent = "analisando o vídeo";
  const r = await api("POST", "/api/cor-auto");
  b.disabled = false; b.textContent = "corrigir a cor automaticamente";
  if (!r.ok) { aviso("não consegui analisar a cor agora"); return; }
  Object.assign(S.proj.cor, r.dados, { auto: true });
  desenharCor(); mudou({ controles: false });
  aviso("cor corrigida: luz e branco acertados. dá pra ajustar nos controles");
};
function aplicarCorPrevia() {
  const c = S.plano?.cor; const cel = $("#celular");
  if (!c || c.neutra) { cel.classList.remove("cor-ativa"); return; }
  cel.classList.add("cor-ativa");
  $("#fc-ganhos").setAttribute("values", `${c.r} 0 0 0 0  0 ${c.g} 0 0 0  0 0 ${c.b} 0 0  0 0 0 1 0`);
  $("#fc-sat").setAttribute("values", c.saturacao);
  const inter = .5 * (1 - c.contraste) + c.brilho;
  for (const id of ["#fc-r", "#fc-g", "#fc-b"]) { $(id).setAttribute("slope", c.contraste); $(id).setAttribute("intercept", inter); }
}

/* ============================================================ trilha de fundo e sons */
function desenharTrilhaFundo() {
  const alvo = $("#trilha"); if (!alvo || !S.proj) return;
  const tr = S.proj.trilha, musicas = S.insertos.filter(i => i.tipo === "audio");
  alvo.innerHTML = "";
  if (!musicas.length && !tr.arquivo) { alvo.innerHTML = `<p class="mini">nenhuma música enviada ainda.</p>`; return; }
  const grade = document.createElement("div"); grade.className = "vis";
  const sel = document.createElement("label"); sel.className = "campo";
  sel.innerHTML = `música <select><option value="">sem trilha</option>${musicas.map(m => `<option ${m.nome === tr.arquivo ? "selected" : ""}>${esc(m.nome)}</option>`).join("")}</select>`;
  sel.querySelector("select").onchange = e => { tr.arquivo = e.target.value || null; mudou({ controles: false }); };
  grade.appendChild(sel);
  grade.appendChild(campoFaixa("volume da música", .02, .6, .01, tr.volume ?? .14, x => Math.round(x * 100) + "%", v => { tr.volume = v; mudou({ controles: false }); }));
  const ch = campoChave("abaixar a música quando você fala", tr.abaixar_na_fala !== false, v => { tr.abaixar_na_fala = v; mudou({ controles: false }); });
  ch.classList.add("largo"); grade.appendChild(ch);
  alvo.appendChild(grade);
}
const cacheSons = {};
function tocarSom(nome, volume = .8) {
  const src = S.estilos.sons[nome] ? `/sons/${nome}.wav` : `/insertos/${encodeURIComponent(nome)}`;
  const base = cacheSons[src] ||= new Audio(src);
  const a = base.cloneNode(); a.volume = Math.min(1, volume); a.play().catch(() => {});
}
let outAnterior = 0;
function efeitosPrevia() {
  if (!S.plano) return;
  const out = paraSaida(video.currentTime);
  const ef = Motion.efeitoBase(S.plano.camadas, out);
  const tv = $(".tela-video");
  tv.style.transformOrigin = `${ef.fx * 100}% ${ef.fy * 100}%`;
  tv.style.transform = ef.z !== 1 || ef.sx || ef.sy ? `translate(${-ef.sx * 100}%, ${-ef.sy * 100}%) scale(${ef.z})` : "";
  aplicarCorPrevia();
  if (!video.paused && out > outAnterior && out - outAnterior < .3) {
    for (const s of S.plano.sons || []) if (s.ini_out > outAnterior && s.ini_out <= out) tocarSom(s.som, s.volume);
  }
  outAnterior = out;
  const ta = $("#trilha-audio"), tr = S.plano.trilha;
  if (tr && !video.paused) {
    const src = "/insertos/" + encodeURIComponent(tr.arquivo);
    if (!ta.src.endsWith(src)) ta.src = src;
    ta.volume = Math.min(1, (tr.volume ?? .14) * 1.8);
    if (ta.duration && Math.abs(ta.currentTime - out % ta.duration) > .4) ta.currentTime = out % ta.duration;
    if (ta.paused) ta.play().catch(() => {});
  } else if (!ta.paused) ta.pause();
  if (S.aba === "cortes" && !video.paused) desenharOnda();
}

/* ============================================================ pessoa recortada na prévia */
let RECORTES = { chave: null, itens: [] }, pedindoRecorte = false, chaveFaixas = "";
async function carregarRecortes() {
  RECORTES = (await api("GET", "/api/recorte-previa")).dados || { itens: [] };
  const caixa = $("#tela-recorte"); caixa.innerHTML = "";
  for (const it of RECORTES.itens || []) {
    const v = document.createElement("video");
    v.src = "/previa/" + it.arquivo; v.muted = true; v.playsInline = true; v.preload = "auto";
    v.dataset.ini = it.ini; v.dataset.fim = it.fim;
    caixa.appendChild(v);
  }
}
function faixasAtras() {
  const fx = (S.plano?.camadas || []).filter(c => c.atras).map(c => [Math.max(0, c.ini_out - .08), c.fim_out + .08]).sort((a, b) => a[0] - b[0]);
  return JSON.stringify(fx.map(f => f.map(x => Math.round(x * 10) / 10)));
}
let tRecorte;
function sincronizarRecortes(temAtras) {
  const caixa = $("#tela-recorte");
  const tv = $(".tela-video");
  caixa.style.transform = tv.style.transform; caixa.style.transformOrigin = tv.style.transformOrigin;
  if (temAtras) {
    const chave = faixasAtras();
    if (chave !== chaveFaixas) {
      chaveFaixas = chave;
      clearTimeout(tRecorte);
      tRecorte = setTimeout(async () => { await salvar(); api("POST", "/api/recorte-previa"); }, 1500);
    }
  }
  const t = video.currentTime;
  for (const v of caixa.querySelectorAll("video")) {
    const ini = +v.dataset.ini, fim = +v.dataset.fim;
    const dentro = temAtras && t >= ini && t < fim;
    v.style.display = dentro ? "block" : "none";
    if (!dentro) { if (!v.paused) v.pause(); continue; }
    const alvo = t - ini;
    if (!video.paused) { if (v.paused) v.play().catch(() => {}); if (Math.abs(v.currentTime - alvo) > .25) v.currentTime = alvo; }
    else { if (!v.paused) v.pause(); if (Math.abs(v.currentTime - alvo) > .05) v.currentTime = alvo; }
  }
}

/* ============================================================ abas e eventos */
$$(".aba").forEach(b => b.onclick = () => irPara(b.dataset.aba));
function irPara(aba) {
  S.aba = aba;
  $$(".aba").forEach(x => x.classList.toggle("ativa", x.dataset.aba === aba));
  $$(".conteudo").forEach(x => x.classList.toggle("ativa", x.dataset.conteudo === aba));
  document.body.classList.toggle("camadas-ativa", aba === "camadas");
  if (aba === "exportar") listarExportados();
  if (aba === "camadas") { listarInsertos(); desenharTrilhas(); }
  if (aba === "cortes") setTimeout(desenharOnda, 30);
  scrollTo({ top: 0, behavior: "smooth" });
}
$("#btn-exportar-topo").onclick = () => irPara("exportar");

$("#ritmos").onclick = e => { const r = e.target.dataset.ritmo; if (!r) return; Object.assign(S.proj.ajustes, { ritmo: r }, RITMOS[r]); mudou({ transcricao: true }); };
$("#r-pausa").oninput = e => { Object.assign(S.proj.ajustes, { pausa_max: +e.target.value, ritmo: "personalizado" }); mudou({ transcricao: true }); };
$("#r-folga").oninput = e => { Object.assign(S.proj.ajustes, { folga: +e.target.value, ritmo: "personalizado" }); mudou(); };
$("#c-pausas").onchange = e => { S.proj.ajustes.cortar_pausas = e.target.checked; mudou({ transcricao: true }); };
$("#modos").onclick = e => { const m = e.target.closest(".pilula")?.dataset.modo; if (!m) return; S.modo = m; desenharControles(); desenharTranscricao(); };
$("#cortes-claude").onclick = e => {
  const m = e.target.dataset.desfazer; if (m === undefined) return;
  for (const p of S.proj.palavras) if (p.cortada && p.origem !== "voce" && (p.motivo || "claude") === m) { p.cortada = false; delete p.motivo; p.origem = "voce"; }
  aviso(`os cortes de ${m} voltaram pro vídeo`); mudou({ transcricao: true });
};

$("#g-ativo").onchange = e => { S.proj.gancho.ativo = e.target.checked; mudou(); };
$("#g-texto").oninput = e => { S.proj.gancho.texto = e.target.value; S.proj.gancho.ativo = !!e.target.value.trim(); $("#g-ativo").checked = S.proj.gancho.ativo; mudou(); };
$("#g-dur").oninput = e => { S.proj.gancho.duracao = +e.target.value; mudou(); };
$("#g-pos").oninput = e => { S.proj.gancho.posicao = +e.target.value; mudou(); };
$("#sugestoes").onclick = e => {
  const k = e.target.dataset.k; if (k === undefined) return;
  Object.assign(S.proj.gancho, { texto: S.proj.sugestoes.ganchos[+k], ativo: true });
  $("#g-texto").value = S.proj.gancho.texto;
  video.currentTime = S.plano?.segmentos?.[0]?.ini || 0;
  mudou();
};
$("#l-ativa").onchange = e => { S.proj.legenda.ativa = e.target.checked; mudou(); };
$("#l-pal").oninput = e => { S.proj.legenda.visual.palavras = +e.target.value; mudou(); };
$("#l-pos").oninput = e => { S.proj.legenda.posicao = +e.target.value; mudou(); };
$("#l-ativa-modo").onclick = e => { const v = e.target.dataset.v; if (!v) return; S.proj.legenda.visual.modo_ativa = v; mudou(); };
$("#l-anim").onclick = e => { const v = e.target.dataset.v; if (!v) return; S.proj.legenda.visual.animacao = v; mudou(); };
$("#l-pont").onchange = e => { S.proj.legenda.sem_pontuacao = e.target.checked; mudou(); };
$("#enquadramento").onclick = e => { const v = e.target.dataset.enq; if (!v) return; S.proj.formato.enquadramento = v; mudou(); };
$("#f-volume").onchange = e => { S.proj.formato.volume = e.target.checked; mudou(); };
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
  $("#exportados").innerHTML = (r.dados.itens || []).map(it => `
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

/* ============================================================ estado */
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
    if (e.recorte_chave && e.recorte_chave !== RECORTES.chave) carregarRecortes();
    if (e.insertos_novos && e.atualizado !== S.insertosVistos) { S.insertosVistos = e.atualizado; listarInsertos().then(desenharTrilhaFundo); if (!e.tarefa) aviso(e.mensagem); }
    if (!S.sujo && !S.salvando && !arrasteBarra && !arrasteTela && r.dados.mtime !== S.mtime) await recarregar();
  } catch (err) {
    $("#status-txt").textContent = "sem conexão com o claude code";
    $("#status").classList.add("erro");
  }
  setTimeout(vigiar, 1000);
}

/* ============================================================ início */
(async function iniciar() {
  S.estilos = (await api("GET", "/api/estilos")).dados;
  Motion.configurar(S.estilos);
  const r = await api("GET", "/api/projeto");
  S.proj = r.dados.projeto; S.mtime = r.dados.mtime;
  video.src = "/video"; fundo.src = "/video";
  await document.fonts.ready;
  tudo();
  registrar();
  listarInsertos().then(desenharTrilhaFundo);
  carregarOnda();
  carregarRecortes();
  addEventListener("resize", () => { desenharQuadro(); desenharOnda(); });
  requestAnimationFrame(laco);
  vigiar();
})();
