/* Seu Editor · motion
   Desenha tudo que fica por cima do vídeo (legenda, gancho, palavras de
   impacto, insertos, desenhos e textos) num quadro de 1080x1920, para um
   instante t do vídeo editado.

   A prévia da interface e a exportação usam este mesmo arquivo. Nenhuma
   animação depende do relógio do navegador: tudo é calculado a partir de
   t, então o mesmo t sempre gera o mesmo quadro, e o vídeo exportado sai
   igual ao que aparece na prévia. */
(function (raiz) {
  const W = 1080, H = 1920;
  let E = null;

  const c01 = v => Math.max(0, Math.min(1, v));
  const ease = {
    out: p => 1 - Math.pow(1 - p, 3),
    back: p => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); },
    inout: p => (p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
  };
  const r3 = v => Math.round(v * 1000) / 1000;

  function hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); }
  function semente(s) { let x = parseInt(hash(String(s)), 36) % 2147483647 || 7; return () => (x = (x * 16807) % 2147483647) / 2147483647; }

  function cor(v) { return v && v.startsWith("#") ? v : "#FB76B2"; }
  function rgba(hex, a) {
    const h = hex.replace("#", "");
    return `rgba(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)},${a})`;
  }
  const esc = t => String(t).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const quebras = t => esc(t).split("|").map(l => l.trim()).join("<br>");

  /* -------------------------------------------------------- entrada e saída */
  const DUR_ENTRADA = { pop: .38, desliza: .4, fade: .28, escreve: .6, nenhuma: .001 };
  function envelope(c, t, entrada) {
    const din = DUR_ENTRADA[entrada] ?? .35;
    const pin = c01((t - c.ini_out) / din);
    const pout = c.ate_o_fim ? 0 : c01((t - (c.fim_out - .22)) / .22);
    let op = 1, sc = 1, ty = 0, clip = "";
    if (entrada === "pop") { sc = .35 + .65 * ease.back(pin); op = c01(pin * 4); }
    else if (entrada === "desliza") { ty = (1 - ease.out(pin)) * 80; op = ease.out(pin); }
    else if (entrada === "fade") { op = pin; }
    else if (entrada === "escreve") { clip = `inset(-20% ${r3((1 - ease.inout(pin)) * 100)}% -20% -10%)`; op = c01(pin * 6); }
    op *= 1 - pout; sc *= 1 - .08 * pout;
    return { op: r3(op), sc: r3(sc), ty: r3(ty), clip, pin };
  }
  function posicionar(el, c, env, extra = "") {
    const x = (c.x ?? .5) * W, y = (c.y ?? .5) * H;
    el.style.left = x + "px"; el.style.top = y + "px";
    el.style.transform = `translate(-50%,-50%) translateY(${env.ty}px) rotate(${c.rot ?? 0}deg) scale(${env.sc})${extra}`;
    el.style.opacity = env.op;
    el.style.clipPath = env.clip || "";
  }

  /* -------------------------------------------------------- visual de texto
     o mesmo para legenda, gancho, palavra de impacto e textos fixos */
  function fonteDe(v) { return E.fontes[v.fonte] || E.fontes.helvetica; }
  function aplicarVisual(el, v, escala = 1) {
    const f = fonteDe(v);
    el.style.fontFamily = f.familia;
    el.style.fontWeight = f.peso;
    el.style.fontStyle = v.italico ? "italic" : "normal";
    el.style.fontSize = (v.tamanho * escala) + "px";
    el.style.lineHeight = v.entrelinhas ?? 1.14;
    el.style.letterSpacing = ((v.espacamento || 0) / 100) + "em";
    el.style.color = v.cor;
    el.style.textTransform = v.caixa_alta ? "uppercase" : "none";
    const fundo = v.fundo && v.fundo !== "nenhum";
    if (v.contorno && !fundo) {
      el.style.webkitTextStroke = `${(v.espessura || 6) * 2 * escala}px ${v.cor_contorno || "#000"}`;
      el.style.paintOrder = "stroke fill";
      el.style.wordSpacing = `${(v.espessura || 6) * 1.4 * escala}px`;
    } else { el.style.webkitTextStroke = ""; el.style.wordSpacing = ""; }
    const sombras = [];
    if (v.brilho) sombras.push(`0 0 16px ${rgba(v.cor, .8)}`, `0 0 42px ${rgba(v.cor, .5)}`);
    if (v.sombra && !fundo) sombras.push(`0 ${4 * escala}px ${16 * escala}px rgba(0,0,0,.5)`, `0 1px 2px rgba(0,0,0,.35)`);
    el.style.textShadow = sombras.join(", ");
  }
  /* fundo por linha (caixa) ou um só (pílula) */
  function conteudo(el, texto, v) {
    const linhas = String(texto || "").split("|").map(l => l.trim()).filter(l => l.length);
    if (v.fundo === "caixa") {
      el.innerHTML = linhas.map(l => `<span class="caixa" style="background:${v.cor_fundo};padding:.06em .3em">${esc(l)}</span>`).join("<br>");
    } else {
      el.innerHTML = linhas.map(esc).join("<br>");
      if (v.fundo === "pilula") { el.style.background = v.cor_fundo; el.style.padding = ".42em .95em"; el.style.borderRadius = "999px"; el.style.boxShadow = "0 10px 30px rgba(0,0,0,.25)"; }
    }
  }

  function itemLegenda(b, k, v, ctx) {
    const leg = ctx.proj.legenda;
    const comFundo = v.fundo && v.fundo !== "nenhum";
    const chave = "leg" + hash(JSON.stringify(v) + b.ini_out + b.palavras.map(w => w.t + (w.destaque ? "*" : "")).join(" ") + leg.posicao);
    return {
      k: chave, z: 90,
      criar() {
        const el = document.createElement("div");
        el.className = "m-leg";
        aplicarVisual(el, v);
        el.style.top = (leg.posicao * H) + "px";
        b.palavras.forEach((w, j) => {
          const sp = document.createElement("span");
          sp.textContent = w.t;
          if (comFundo) { sp.className = "caixa"; sp.style.padding = ".06em .22em"; sp.style.background = v.cor_fundo; }
          el.appendChild(sp);
          if (j < b.palavras.length - 1) el.appendChild(document.createTextNode(" "));
        });
        return el;
      },
      atualizar(el, t) {
        const p = c01((t - b.ini_out) / (v.animacao === "pop" ? .11 : .16));
        if (v.animacao === "pop") el.style.scale = r3(.78 + .22 * p);
        if (v.animacao === "fade") el.style.opacity = r3(p);
        let ativa = -1;
        if (v.modo_ativa !== "nenhum") b.palavras.forEach((w, j) => { if (t >= w.ini_out && t < w.fim_out) ativa = j; });
        el.querySelectorAll("span").forEach((sp, j) => {
          const w = b.palavras[j];
          const marcada = j === ativa || w.destaque;
          if (v.modo_ativa === "fundo" && j === ativa) {
            sp.style.background = v.cor_destaque; sp.style.color = v.cor;
            if (!comFundo) { sp.style.padding = ".02em .2em"; sp.style.borderRadius = ".12em"; sp.style.webkitTextStroke = "0"; }
          } else {
            sp.style.background = comFundo ? v.cor_fundo : "transparent";
            sp.style.color = marcada ? v.cor_destaque : v.cor;
            if (!comFundo) { sp.style.padding = ""; sp.style.webkitTextStroke = ""; }
          }
        });
        return "a" + ativa;
      },
    };
  }

  function itemGancho(g, v, ctx) {
    const c = { ...g, x: .5, y: g.posicao, rot: 0 };
    return {
      k: "gancho" + hash(JSON.stringify(v) + g.texto + g.posicao), z: 80,
      criar() {
        const el = document.createElement("div");
        el.className = "m-txt";
        aplicarVisual(el, v);
        conteudo(el, g.texto, v);
        el.style.maxWidth = (W - 180) + "px";
        return el;
      },
      atualizar(el, t) { posicionar(el, c, envelope(c, t, "pop")); return ""; },
    };
  }

  /* -------------------------------------------------------- palavra de impacto */
  function itemImpacto(c, ctx) {
    const v = c.visual;
    return {
      k: "imp" + c.id + hash(JSON.stringify(c.visual) + c.texto + c.tamanho), z: 60, id: c.id,
      criar() {
        const el = document.createElement("div");
        el.className = "m-imp";
        aplicarVisual(el, v, c.tamanho || 1);
        conteudo(el, c.texto, v);
        return el;
      },
      atualizar(el, t) { posicionar(el, c, envelope(c, t, c.entrada)); return ""; },
    };
  }

  /* linhas ligando a palavra de impacto aos cartões que estão na tela */
  function itemLigacoes(c, cartoes, ctx) {
    const col = c.visual?.cor || "#FB76B2";
    const alvos = cartoes.map(o => [o.x ?? .5, o.y ?? .5]);
    return {
      k: "lig" + c.id + hash(JSON.stringify(alvos) + col), z: 55,
      criar() {
        const ns = "http://www.w3.org/2000/svg";
        const svg = document.createElementNS(ns, "svg");
        svg.setAttribute("class", "m-svg-cheio"); svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
        for (const [x, y] of alvos) {
          const l = document.createElementNS(ns, "line");
          l.setAttribute("x1", (c.x ?? .5) * W); l.setAttribute("y1", (c.y ?? .5) * H);
          l.setAttribute("x2", x * W); l.setAttribute("y2", y * H);
          l.setAttribute("stroke", col); l.setAttribute("stroke-width", 4); l.setAttribute("stroke-linecap", "round");
          l.setAttribute("pathLength", 1); l.setAttribute("stroke-dasharray", "1 1");
          svg.appendChild(l);
        }
        svg.style.filter = `drop-shadow(0 0 6px ${rgba(col, .6)})`;
        return svg;
      },
      atualizar(el, t) {
        const p = ease.inout(c01((t - c.ini_out - .15) / .5));
        const pout = c.ate_o_fim ? 0 : c01((t - (c.fim_out - .22)) / .22);
        el.querySelectorAll("line").forEach(l => l.setAttribute("stroke-dashoffset", r3(1 - p)));
        el.style.opacity = r3(.85 * (1 - pout));
        return "p" + r3(p);
      },
    };
  }

  /* -------------------------------------------------------- insertos */
  function itemImagem(c, ctx) {
    const src = (ctx.base || "") + "/insertos/" + encodeURIComponent(c.arquivo || "");
    if (c.modo === "tela") {
      return {
        k: "imgt" + c.id + hash(src), z: 10, id: c.id,
        criar() {
          const el = document.createElement("div"); el.className = "m-tela-cheia";
          el.innerHTML = `<img src="${src}" alt="">`;
          return el;
        },
        atualizar(el, t) {
          const env = envelope(c, t, "fade");
          const prog = c01((t - c.ini_out) / Math.max(.1, c.fim_out - c.ini_out));
          el.style.opacity = env.op;
          el.firstChild.style.transform = `scale(${r3(1 + .08 * prog)})`;
          return "";
        },
      };
    }
    return {
      k: "img" + c.id + hash(src + (c.proporcao || "")), z: 30, id: c.id,
      criar() {
        const el = document.createElement("div"); el.className = "m-cartao";
        el.innerHTML = `<img src="${src}" alt="">`;
        if (c.proporcao) { el.firstChild.style.aspectRatio = c.proporcao; el.firstChild.style.objectFit = "cover"; }
        return el;
      },
      atualizar(el, t) {
        el.style.width = ((c.tamanho || .34) * W) + "px";
        posicionar(el, c, envelope(c, t, c.entrada || "pop"));
        return "";
      },
    };
  }

  function itemVideo(c, ctx) {
    const src = (ctx.base || "") + "/insertos/" + encodeURIComponent(c.arquivo || "");
    const tela = c.modo !== "cartao";
    return {
      k: "vid" + c.id + hash(src + c.modo), z: tela ? 12 : 31, id: c.id,
      criar() {
        const el = document.createElement("div"); el.className = tela ? "m-tela-cheia" : "m-cartao";
        el.innerHTML = `<video src="${src}" muted playsinline preload="auto"></video>`;
        return el;
      },
      atualizar(el, t) {
        const v = el.firstChild;
        const alvo = (c.inicio_clip || 0) + (t - c.ini_out);
        if (ctx.tocando) {
          if (v.paused) v.play().catch(() => {});
          if (Math.abs(v.currentTime - alvo) > .3) v.currentTime = alvo;
        } else {
          if (!v.paused) v.pause();
          if (Math.abs(v.currentTime - alvo) > .04) v.currentTime = alvo;
        }
        if (tela) { el.style.opacity = envelope(c, t, "fade").op; }
        else { el.style.width = ((c.tamanho || .34) * W) + "px"; posicionar(el, c, envelope(c, t, "fade")); }
        return "";
      },
    };
  }

  /* -------------------------------------------------------- desenhos à mão */
  const ASPECTO = { circulo: .8, seta: .55, sublinhado: .22, x: 1, brilho: 1 };
  function caminhos(forma, id) {
    const r = semente(id);
    const h = 100 * ASPECTO[forma];
    const pts = a => "M" + a.map(p => p.map(v => v.toFixed(2)).join(" ")).join(" L");
    if (forma === "circulo") {
      const a0 = -Math.PI * .62 + r() * .3, volta = Math.PI * 2 * 1.13, n = 110;
      const f1 = r() * 6, f2 = r() * 6, l = [];
      for (let i = 0; i <= n; i++) {
        const a = a0 + volta * i / n;
        const k = 1 + .035 * Math.sin(2 * a + f1) + .02 * Math.sin(5 * a + f2) + .05 * (i / n);
        l.push([50 + 45 * k * Math.cos(a), h / 2 + (h / 2 - 5) * k * Math.sin(a)]);
      }
      return [pts(l)];
    }
    if (forma === "seta") {
      const p0 = [6, h * .85], p1 = [38, h * .02], p2 = [90, h * .42];
      const l = [];
      for (let i = 0; i <= 40; i++) { const s = i / 40, u = 1 - s; l.push([u * u * p0[0] + 2 * u * s * p1[0] + s * s * p2[0], u * u * p0[1] + 2 * u * s * p1[1] + s * s * p2[1]]); }
      const ang = Math.atan2(p2[1] - p1[1], p2[0] - p1[0]), tam = 16;
      const cab = [[p2[0] - tam * Math.cos(ang - .55), p2[1] - tam * Math.sin(ang - .55)], p2, [p2[0] - tam * Math.cos(ang + .55), p2[1] - tam * Math.sin(ang + .55)]];
      return [pts(l), pts(cab)];
    }
    if (forma === "sublinhado") {
      const l = [];
      for (let i = 0; i <= 50; i++) { const x = 3 + 94 * i / 50; l.push([x, h * .55 + Math.sin(i / 50 * Math.PI * 3 + r()) * h * .12 - i / 50 * h * .15]); }
      return [pts(l)];
    }
    if (forma === "x") return [pts([[14, 12], [50, 52], [88, 90]]), pts([[86, 14], [52, 48], [12, 88]])];
    if (forma === "brilho") {
      const l = [];
      for (let i = 0; i < 4; i++) { const a = i * Math.PI / 4; l.push(pts([[50 + 16 * Math.cos(a), 50 + 16 * Math.sin(a)], [50 + 46 * Math.cos(a), 50 + 46 * Math.sin(a)]])); l.push(pts([[50 - 16 * Math.cos(a), 50 - 16 * Math.sin(a)], [50 - 46 * Math.cos(a), 50 - 46 * Math.sin(a)]])); }
      return l;
    }
    return [];
  }
  function itemDesenho(c, ctx) {
    const forma = c.forma || "circulo";
    const col = cor(c.cor);
    const larg = (c.tamanho || .6) * W;
    return {
      k: "des" + c.id + hash(JSON.stringify(c) + col), z: 50, id: c.id,
      criar() {
        const ns = "http://www.w3.org/2000/svg";
        const svg = document.createElementNS(ns, "svg");
        const h = 100 * (ASPECTO[forma] || 1);
        svg.setAttribute("viewBox", `-4 -4 108 ${h + 8}`);
        svg.setAttribute("class", "m-desenho");
        svg.style.width = larg + "px";
        const esp = (c.espessura || 12) / (larg / 108);
        for (const d of caminhos(forma, c.id)) {
          const p = document.createElementNS(ns, "path");
          p.setAttribute("d", d); p.setAttribute("fill", "none"); p.setAttribute("stroke", col);
          p.setAttribute("stroke-width", esp); p.setAttribute("stroke-linecap", "round"); p.setAttribute("stroke-linejoin", "round");
          p.setAttribute("pathLength", 1); p.setAttribute("stroke-dasharray", "1 1");
          svg.appendChild(p);
        }
        svg.style.filter = `drop-shadow(0 0 8px ${rgba(col, .55)}) drop-shadow(0 2px 2px rgba(0,0,0,.3))`;
        return svg;
      },
      atualizar(el, t) {
        const p = ease.inout(c01((t - c.ini_out) / .6));
        const ps = el.querySelectorAll("path"), n = ps.length;
        ps.forEach((path, i) => path.setAttribute("stroke-dashoffset", r3(1 - c01(p * n - i))));
        const env = envelope(c, t, "nenhuma");
        posicionar(el, c, env);
        return "p" + r3(p);
      },
    };
  }

  /* -------------------------------------------------------- textos fixos */
  function itemTexto(c, ctx) {
    const v = c.visual;
    return {
      k: "txt" + c.id + hash(JSON.stringify(v) + c.texto + c.tamanho + c.largura), z: 70, id: c.id,
      criar() {
        const el = document.createElement("div");
        el.className = "m-txt";
        aplicarVisual(el, v, c.tamanho || 1);
        el.style.maxWidth = ((c.largura || .84) * W) + "px";
        conteudo(el, c.texto, v);
        return el;
      },
      atualizar(el, t) { posicionar(el, c, envelope(c, t, c.entrada)); return ""; },
    };
  }

  /* -------------------------------------------------------- cena */
  function itens(ctx, t) {
    const { plano } = ctx;
    const lista = [];
    const visiveis = (plano.camadas || []).filter(c => t >= c.ini_out && t < c.fim_out);
    for (const c of visiveis) {
      if (c.tipo === "imagem") lista.push(itemImagem(c, ctx));
      else if (c.tipo === "video") { if (ctx.videos) lista.push(itemVideo(c, ctx)); }
      else if (c.tipo === "impacto") {
        lista.push(itemImpacto(c, ctx));
        if (c.ligar) {
          const cartoes = visiveis.filter(o => (o.tipo === "imagem" || o.tipo === "video") && o.modo !== "tela");
          if (cartoes.length) lista.push(itemLigacoes(c, cartoes, ctx));
        }
      }
      else if (c.tipo === "desenho") lista.push(itemDesenho(c, ctx));
      else if (c.tipo === "texto") lista.push(itemTexto(c, ctx));
    }
    if (plano.gancho && t < plano.gancho.fim_out) lista.push(itemGancho(plano.gancho, plano.gancho_visual, ctx));
    const k = plano.blocos.findIndex(b => t >= b.ini_out && t < b.fim_out);
    if (k >= 0) lista.push(itemLegenda(plano.blocos[k], k, plano.legenda, ctx));
    return lista;
  }

  function cena(tela, ctx, t) {
    const mapa = tela._mapa || (tela._mapa = new Map());
    const vistos = new Set();
    const assinatura = [];
    for (const it of itens(ctx, t)) {
      let el = mapa.get(it.k);
      if (!el) { el = it.criar(); el.dataset.k = it.k; if (it.id) el.dataset.id = it.id; tela.appendChild(el); mapa.set(it.k, el); }
      el.style.zIndex = it.z;
      const extra = it.atualizar(el, t) || "";
      el.classList.toggle("m-selecionada", !!(ctx.selecionada && it.id === ctx.selecionada));
      vistos.add(it.k);
      assinatura.push(it.k + ":" + (el.style.cssText.length < 400 ? el.style.cssText : hash(el.style.cssText)) + extra);
    }
    for (const [k, el] of mapa) if (!vistos.has(k)) { el.remove(); mapa.delete(k); }
    return assinatura.join("|");
  }

  async function preparar(ctx) {
    const vis = [ctx.plano.legenda, ctx.plano.gancho_visual, ...(ctx.plano.camadas || []).map(c => c.visual).filter(Boolean)];
    const pedidos = vis.map(v => { const f = fonteDe(v); return `${v.italico ? "italic " : ""}${f.peso} 40px ${f.familia}`; });
    await Promise.all([...new Set(pedidos)].map(p => document.fonts.load(p).catch(() => {})));
    const imgs = (ctx.plano.camadas || []).filter(c => c.tipo === "imagem").map(c => {
      const i = new Image(); i.src = (ctx.base || "") + "/insertos/" + encodeURIComponent(c.arquivo || "");
      return i.decode().catch(() => {});
    });
    await Promise.all(imgs);
    await document.fonts.ready;
  }

  raiz.Motion = {
    W, H,
    configurar(estilos) {
      E = estilos;
      for (const [id, f] of Object.entries(E.fontes)) {
        if (!f.arquivos || f._registrada) continue;
        for (const a of f.arquivos) {
          try {
            const face = new FontFace(f.nome, `url(/fontes-pessoa/${encodeURIComponent(a.arquivo)})`,
              { weight: f.variavel ? "100 900" : String(a.peso || 400), style: a.italico ? "italic" : "normal" });
            document.fonts.add(face);
          } catch (e) { /* arquivo inválido, segue com as outras */ }
        }
        f._registrada = true;
      }
    },
    cena, preparar, aplicarVisual: (el, v, e) => aplicarVisual(el, v, e),
    aspectoDesenho: f => ASPECTO[f] || 1,
  };
})(window);
