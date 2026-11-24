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
  const DUR_ENTRADA = { pop: .38, desliza: .4, fade: .28, fadelento: 1.1, escreve: .6, nenhuma: .001, esquerda: .45, direita: .45, cai: .5 };
  function envelope(c, t, entrada) {
    const din = Math.min(DUR_ENTRADA[entrada] ?? .35, Math.max(.05, (c.fim_out - c.ini_out) / 2.2));
    const pin = c01((t - c.ini_out) / din);
    const dout = entrada === "fadelento" ? Math.min(1.1, (c.fim_out - c.ini_out) / 2.2) : .22;
    const pout = c.ate_o_fim ? 0 : c01((t - (c.fim_out - dout)) / dout);
    let op = 1, sc = 1, ty = 0, tx = 0, clip = "";
    if (entrada === "pop") { sc = .35 + .65 * ease.back(pin); op = c01(pin * 4); }
    else if (entrada === "desliza") { ty = (1 - ease.out(pin)) * 80; op = ease.out(pin); }
    else if (entrada === "fade" || entrada === "fadelento") { op = ease.inout(pin); }
    else if (entrada === "esquerda" || entrada === "direita") { tx = (1 - ease.out(pin)) * (entrada === "esquerda" ? -760 : 760); op = c01(pin * 3); }
    else if (entrada === "cai") { ty = -(1 - ease.back(pin)) * 260; op = c01(pin * 4); }
    else if (entrada === "escreve") { clip = `inset(-20% ${r3((1 - ease.inout(pin)) * 100)}% -20% -10%)`; op = c01(pin * 6); }
    op *= entrada === "fadelento" ? 1 - ease.inout(pout) : 1 - pout;
    if (entrada !== "fadelento") sc *= 1 - .08 * pout;
    op *= c.opacidade ?? 1;
    return { op: r3(op), sc: r3(sc), ty: r3(ty), tx: r3(tx), clip, pin };
  }
  function posicionar(el, c, env, extra = "") {
    const x = (c.x ?? .5) * W, y = (c.y ?? .5) * H;
    el.style.left = x + "px"; el.style.top = y + "px";
    el.style.transform = `translate(-50%,-50%) translate(${env.tx || 0}px, ${env.ty}px) rotate(${c.rot ?? 0}deg) scale(${env.sc})${extra}`;
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
    el.style.letterSpacing = (((f.tracking || 0) + (v.espacamento || 0)) / 100) + "em";
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

  function itemLegenda(b, k, v0, ctx) {
    const leg = ctx.proj.legenda;
    let v = v0;
    if (b.destaque) {
      const segunda = b.alt === 1 && v0.fonte_destaque2;
      v = { ...v0, fonte: (segunda ? v0.fonte_destaque2 : v0.fonte_destaque) || v0.fonte,
            cor: (b.alt === 1 ? (v0.cor_destaque2 || v0.cor_destaque) : v0.cor_destaque) || v0.cor,
            tamanho: v0.tamanho * (v0.escala_destaque || 1.8), modo_ativa: "nenhum" };
    }
    const comFundo = v.fundo && v.fundo !== "nenhum";
    const chave = "leg" + hash(JSON.stringify(v) + b.ini_out + (b.destaque ? "D" : "") + b.palavras.map(w => w.t + (w.destaque ? "*" : "")).join(" ") + leg.posicao);
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
        if (v.animacao === "fade") el.style.opacity = r3(p * c01((b.fim_out - t) / .12));
        let ativa = -1;
        if (v.modo_ativa !== "nenhum") b.palavras.forEach((w, j) => { if (t >= w.ini_out && t < w.fim_out) ativa = j; });
        el.querySelectorAll("span").forEach((sp, j) => {
          const w = b.palavras[j];
          const marcada = j === ativa || (w.destaque && !b.destaque);
          if (v.modo_ativa === "fundo" && j === ativa) {
            sp.style.background = v.cor_destaque; sp.style.color = v.cor;
            if (!comFundo) { sp.style.padding = ".02em .2em"; sp.style.borderRadius = ".12em"; sp.style.webkitTextStroke = "0"; }
          } else {
            sp.style.background = comFundo ? v.cor_fundo : "transparent";
            sp.style.color = marcada && !b.destaque ? v.cor_destaque : v.cor;
            if (!comFundo) { sp.style.padding = ""; sp.style.webkitTextStroke = ""; }
          }
        });
        return "a" + ativa;
      },
    };
  }

  /* -------------------------------------------------------- gancho escrito (modelos de abertura)
     caixa: caixa colorida | texto: só texto, com etiqueta opcional | rosto: na frente do rosto
     imagens: linha pequena + título, fotos atrás da pessoa (as fotos são camadas do plano)
     icones: linha pequena + palavra gigante com ícones em volta | palavras: a fala, uma por vez
     *palavra* no texto marca o destaque; | quebra a linha. */
  const ICONES = {
    "estrela": `<polygon points="50,4 62,37 97,38 69,59 79,93 50,73 21,93 31,59 3,38 38,37" fill="C"/>`,
    "estrela-contorno": `<polygon points="50,6 62,37 95,38 69,59 78,91 50,72 22,91 31,59 5,38 38,37" fill="none" stroke="C" stroke-width="6" stroke-linejoin="round"/>`,
    "brilho": `<path d="M50 2C54 36 64 46 98 50C64 54 54 64 50 98C46 64 36 54 2 50C36 46 46 36 50 2Z" fill="C"/>`,
    "coracao": `<path d="M50 88C20 66 4 50 4 31C4 17 15 7 28 7C38 7 46 13 50 21C54 13 62 7 72 7C85 7 96 17 96 31C96 50 80 66 50 88Z" fill="C"/>`,
    "nuvem": `<path d="M24 78C11 78 3 69 3 58C3 47 12 39 23 39C25 24 37 13 52 13C66 13 77 23 80 36C91 37 98 46 98 57C98 69 89 78 77 78Z" fill="C"/>`,
    "raio": `<polygon points="58,3 18,56 46,56 38,97 82,40 53,40" fill="C"/>`,
    "seta": `<path d="M12 80C30 40 55 26 84 24M84 24L66 12M84 24L70 42" fill="none" stroke="C" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>`,
    "circulo": `<circle cx="50" cy="50" r="40" fill="none" stroke="C" stroke-width="7"/>`,
  };
  // (x, deslocamento em y a partir do título, tamanho em px, giro) fora da área do rosto
  const LUGARES_ICONES = [[.12, -.1, 118, -12], [.88, -.11, 128, 10], [.19, .08, 92, 8], [.83, .07, 104, -8],
    [.06, .0, 72, 0], [.94, -.01, 74, 0], [.33, -.16, 62, 0], [.67, -.15, 66, 0], [.09, .2, 84, -6], [.91, .2, 88, 6],
    [.5, -.19, 58, 0], [.27, .17, 54, 0]];
  function textoComDestaque(texto, estiloDest) {
    return String(texto || "").split("|").map(l => l.trim()).filter(Boolean)
      .map(l => esc(l).replace(/\*([^*]+)\*/g, (_, x) => `<span style="${estiloDest}">${x}</span>`)).join("<br>");
  }
  function itemGancho(g, v, ctx) {
    const modelo = g.modelo || "caixa";
    const pl = ctx.plano || {};
    const ftx = E.fontes[pl.gancho_fonte_texto] || fonteDe(v);
    const fd2 = E.fontes[pl.gancho_fonte_destaque2] || fonteDe(v);
    const c = { ...g, x: .5, y: g.posicao, rot: 0 };
    const sec = (el, escala, fonte) => {
      aplicarVisual(el, { ...v, fundo: "nenhum", caixa_alta: false, contorno: false }, escala);
      el.style.fontFamily = fonte.familia; el.style.fontWeight = fonte.peso;
      el.style.letterSpacing = ((fonte.tracking || 0) / 100) + "em";
    };
    const sai = t => 1 - c01((t - (g.fim_out - .14)) / .14);
    if (modelo === "caixa") {
      return {
        k: "gancho" + hash(JSON.stringify(v) + g.texto + g.posicao), z: 80,
        criar() {
          const el = document.createElement("div"); el.className = "m-txt";
          aplicarVisual(el, v); conteudo(el, g.texto.replace(/\*/g, ""), v);
          el.style.maxWidth = (W - 180) + "px"; return el;
        },
        atualizar(el, t) { posicionar(el, c, envelope(c, t, "pop")); return ""; },
      };
    }
    if (modelo === "palavras") {
      const pals = g.palavras || [];
      return {
        k: "ganchop" + hash(JSON.stringify(v) + JSON.stringify(pals) + g.posicao), z: 80,
        criar() { const el = document.createElement("div"); el.className = "m-imp"; return el; },
        atualizar(el, t) {
          let w = null;
          for (const p of pals) if (t >= p.ini_out - .02) w = p;
          if (!w || (pals.indexOf(w) === pals.length - 1 && t > w.fim_out + .4)) { el.style.opacity = 0; return ""; }
          const chave = w.ini_out + w.t;
          if (el._w !== chave) {
            el._w = chave;
            aplicarVisual(el, v, w.destaque ? 1.8 : 1);
            if (w.destaque) { const f = fonteDe({ ...v, fonte: pl.gancho_fonte_destaque2 }); el.style.fontFamily = f.familia; el.style.fontWeight = f.peso; }
            el.textContent = w.t;
          }
          const pin = c01((t - w.ini_out) / .09);
          posicionar(el, c, { op: r3(c01(pin * 3) * sai(t)), sc: r3(.85 + .15 * ease.back(pin)), ty: 0, tx: 0 });
          return chave;
        },
      };
    }
    const destEstilo = modelo === "icones"
      ? `font-size:2.3em;line-height:.9;letter-spacing:-.04em;display:inline-block`
      : `font-family:${fd2.familia};font-weight:${fd2.peso};${v.cor_destaque ? "color:" + v.cor_destaque + ";" : ""}`;
    const icones = (g.icones && g.icones.length ? g.icones : ["estrela", "brilho", "estrela-contorno", "nuvem", "brilho", "estrela", "estrela-contorno", "brilho", "nuvem", "estrela"]).slice(0, LUGARES_ICONES.length);
    const cores = g.cor_icones ? [g.cor_icones] : ["#FB76B2", "#FFFFFF", "#FFD84D"];
    return {
      k: "ganchom" + modelo + hash(JSON.stringify(v) + JSON.stringify(g)), z: 80,
      criar() {
        const el = document.createElement("div");
        el.style.cssText = `left:0;top:0;width:${W}px;height:${H}px;pointer-events:none`;
        if (modelo === "icones") {
          icones.forEach((nome, i) => {
            const [x, dy, tam, rot] = LUGARES_ICONES[i];
            const d = document.createElement("div"); d.className = "g-icone";
            d.style.cssText = `position:absolute;width:${tam}px;height:${tam}px;filter:drop-shadow(0 6px 12px rgba(0,0,0,.25))`;
            d.dataset.x = x; d.dataset.y = (g.posicao ?? .2) + dy; d.dataset.rot = rot; d.dataset.i = i;
            d.innerHTML = /\.(png|jpe?g|webp|gif|svg)$/i.test(nome)
              ? `<img src="${(ctx.base || "") + "/insertos/" + encodeURIComponent(nome)}" style="width:100%;height:100%;object-fit:contain">`
              : `<svg viewBox="0 0 100 100" width="100%" height="100%">${(ICONES[nome] || ICONES.estrela).replace(/C/g, cores[i % cores.length])}</svg>`;
            el.appendChild(d);
          });
        }
        if (g.linha_pequena && modelo !== "rosto") {
          const d = document.createElement("div"); d.className = "m-txt g-pequena";
          if (modelo === "imagens") { sec(d, 1.05, fd2); d.style.fontStyle = "italic"; d.style.paddingRight = ".15em"; }
          else sec(d, modelo === "icones" ? .62 : .5, ftx);
          d.textContent = g.linha_pequena;
          el.appendChild(d);
        }
        const tit = document.createElement("div"); tit.className = "m-txt g-titulo";
        aplicarVisual(tit, v);
        tit.innerHTML = textoComDestaque(g.texto, destEstilo);
        if (v.fundo === "pilula") { tit.style.background = v.cor_fundo; tit.style.padding = ".42em .95em"; tit.style.borderRadius = "999px"; }
        tit.style.maxWidth = (W - 120) + "px";
        el.appendChild(tit);
        if (g.etiqueta && modelo === "texto") {
          const d = document.createElement("div"); d.className = "m-txt g-etiqueta";
          sec(d, 1, ftx);
          d.style.cssText += ";font-size:34px;text-transform:uppercase;letter-spacing:.16em;color:#2B2B2B;background:#F3EBDD;padding:.5em 1.1em;border-radius:999px;text-shadow:none;box-shadow:0 8px 24px rgba(0,0,0,.18)";
          d.textContent = g.etiqueta;
          el.appendChild(d);
        }
        return el;
      },
      atualizar(el, t) {
        const op = sai(t);
        const tit = el.querySelector(".g-titulo"), peq = el.querySelector(".g-pequena"), etq = el.querySelector(".g-etiqueta");
        const hT = tit.offsetHeight || v.tamanho;
        let yT = g.posicao;
        if (modelo === "imagens") {
          // linha manuscrita se escreve, o título entra logo depois
          if (peq) {
            const hP = peq.offsetHeight || v.tamanho;
            const pinP = c01(t / .45);
            posicionar(peq, { x: .5, y: yT - (hT / 2 + hP * .35) / H }, { op: r3(op), sc: 1, ty: 0, tx: 0, clip: `inset(-30% ${r3((1 - ease.inout(pinP)) * 112 - 12)}% -30% -12%)` });
          }
          const pin = c01((t - (peq ? .4 : 0)) / .12);
          posicionar(tit, { x: .5, y: yT }, { op: r3(pin * op), sc: 1, ty: 0, tx: 0 });
          return hash([...el.children].map(d => d.style.cssText).join("|"));
        }
        posicionar(tit, { x: .5, y: yT }, { op: r3(c01(t / .1) * op), sc: 1, ty: 0, tx: 0 });
        if (peq) {
          const hP = peq.offsetHeight || 40;
          posicionar(peq, { x: .5, y: yT - (hT / 2 + hP / 2 + 6) / H }, { op: r3(c01(t / .1) * op), sc: 1, ty: 0, tx: 0 });
        }
        if (etq) {
          const pin = c01((t - 1.4) / .28);
          posicionar(etq, { x: .5, y: yT + (hT / 2 + 70) / H }, { op: r3(c01(pin * 3) * op), sc: r3(.4 + .6 * ease.back(pin)), ty: 0, tx: 0 });
        }
        for (const d of el.querySelectorAll(".g-icone")) {
          const i = +d.dataset.i, pin = c01((t - .04 * i) / .3);
          const bob = Math.sin((t * 1.6 + i) * 1.3) * 6;
          posicionar(d, { x: +d.dataset.x, y: +d.dataset.y, rot: +d.dataset.rot }, { op: r3(c01(pin * 3) * op), sc: r3(.3 + .7 * ease.back(pin)), ty: r3(bob), tx: 0 });
        }
        return hash([...el.children].map(d => d.style.cssText).join("|"));
      },
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
  /* meia tela: o inserto ocupa a metade de cima (ou de baixo) com a borda de dentro esfumada */
  function caixaMetade(el, c) {
    const alt = Math.round(H * .54), esf = Math.round(H * .08), baixo = c.lado === "baixo";
    el.style.left = "0px"; el.style.width = W + "px"; el.style.height = alt + "px";
    el.style.top = (baixo ? H - alt : 0) + "px";
    const m = `linear-gradient(${baixo ? "to top" : "to bottom"}, #000 ${alt - esf}px, transparent ${alt}px)`;
    el.style.webkitMaskImage = m; el.style.maskImage = m;
  }

  function itemImagem(c, ctx) {
    const src = (ctx.base || "") + "/insertos/" + encodeURIComponent(c.arquivo || "");
    if (c.modo === "metade") {
      return {
        k: "imgm" + c.id + hash(src + c.lado), z: 12, id: c.id,
        criar() { const el = document.createElement("div"); el.className = "m-metade"; el.innerHTML = `<img src="${src}" alt="">`; caixaMetade(el, c); return el; },
        atualizar(el, t) {
          const prog = c01((t - c.ini_out) / Math.max(.1, c.fim_out - c.ini_out));
          el.style.opacity = c.entrada === "nenhuma" ? (c.opacidade ?? 1) : envelope(c, t, c.entrada === "fadelento" ? "fadelento" : "nenhuma").op;
          el.firstChild.style.transform = c.movimento === "parado" ? "" : `scale(${r3(1 + .06 * prog)})`;
          return "";
        },
      };
    }
    if (c.modo === "tela") {
      return {
        k: "imgt" + c.id + hash(src + (c.esfumar || 0)), z: 10, id: c.id,
        criar() {
          const el = document.createElement("div"); el.className = "m-tela-cheia";
          el.innerHTML = `<img src="${src}" alt="">`;
          esfumar(el, c);
          return el;
        },
        atualizar(el, t) {
          const env = envelope(c, t, c.entrada === "fadelento" ? "fadelento" : "fade");
          const prog = c01((t - c.ini_out) / Math.max(.1, c.fim_out - c.ini_out));
          el.style.opacity = c.entrada === "nenhuma" ? (c.opacidade ?? 1) : env.op;
          el.firstChild.style.transform = `scale(${r3(1 + .08 * prog)})`;
          return "";
        },
      };
    }
    return {
      k: "img" + c.id + hash(src + (c.proporcao || "") + (c.moldura || "") + (c.esfumar || 0)), z: 30, id: c.id,
      criar() {
        const el = document.createElement("div"); el.className = "m-cartao moldura-" + (c.moldura || "polaroid");
        el.innerHTML = `<img src="${src}" alt="">`;
        esfumar(el, c);
        if (c.proporcao) { el.firstChild.style.aspectRatio = c.proporcao; el.firstChild.style.objectFit = "cover"; }
        return el;
      },
      atualizar(el, t) {
        el.style.width = ((c.tamanho || .34) * W) + "px";
        posicionar(el, c, envelope(c, t, c.entrada || "pop"), movimento(c, t));
        return "";
      },
    };
  }

  /* movimento enquanto o inserto está na tela */
  /* bordas esfumadas: a foto some aos poucos nas pontas */
  function esfumar(el, c) {
    const e = c.esfumar || 0;
    const m = e ? `radial-gradient(ellipse at center, #000 ${Math.round(62 - e * 50)}%, transparent ${Math.round(100 - e * 18)}%)` : "";
    el.style.webkitMaskImage = m; el.style.maskImage = m;
  }

  function movimento(c, t) {
    const d = t - c.ini_out, total = Math.max(.1, c.fim_out - c.ini_out);
    if (c.movimento === "flutua") return ` translateY(${r3(Math.sin(d * 2.2) * 10)}px) rotate(${r3(Math.sin(d * 1.6) * 1.4)}deg)`;
    if (c.movimento === "aproxima") return ` scale(${r3(1 + .08 * c01(d / total))})`;
    if (c.movimento === "gira") return ` rotate(${r3(d * 6)}deg)`;
    return "";
  }

  function itemVideo(c, ctx) {
    const src = (ctx.base || "") + "/insertos/" + encodeURIComponent(c.arquivo || "");
    const tela = c.modo !== "cartao";
    const metade = c.modo === "metade";
    return {
      k: "vid" + c.id + hash(src + c.modo + c.lado), z: tela ? 12 : 31, id: c.id,
      criar() {
        const el = document.createElement("div"); el.className = metade ? "m-metade" : tela ? "m-tela-cheia" : "m-cartao";
        el.innerHTML = `<video src="${src}" muted playsinline preload="auto"></video>`;
        if (metade) caixaMetade(el, c);
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
        if (c.entrada === "nenhuma" && (tela || metade)) { el.style.opacity = 1; }
        else if (metade) { el.style.opacity = envelope(c, t, "nenhuma").op; }
        else if (tela) { el.style.opacity = envelope(c, t, "fade").op; }
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

  /* -------------------------------------------------------- cascata
     palavras-chave entrando uma a uma, empilhadas, e saindo juntas */
  function itemCascata(c, ctx) {
    const v = c.visual, linhas = c.linhas || [];
    // centro de cada linha: empilha pela altura da letra de cada uma (espaco 1 = linhas
    // quase encostando). Camadas antigas com "passo" fixo continuam iguais.
    const altura = i => (v.tamanho || 100) * (linhas[i]?.tamanho || c.tamanho || 1) * (v.entrelinhas || 1);
    const centros = [0];
    for (let i = 1; i < linhas.length; i++)
      centros.push(c.passo != null && c.espaco == null ? i * c.passo * H
        : centros[i - 1] + (altura(i - 1) + altura(i)) / 2 * .92 * (c.espaco ?? 1));
    const passo = JSON.stringify(centros);
    const variadas = ["desliza", "esquerda", "direita", "pop"];
    return {
      k: "cas" + c.id + hash(JSON.stringify(v) + JSON.stringify(linhas) + c.tamanho + passo + (c.y ?? .35)), z: 65, id: c.id,
      criar() {
        const el = document.createElement("div"); el.className = "m-cascata";
        el.style.left = "0px"; el.style.top = "0px"; el.style.width = W + "px"; el.style.height = H + "px";
        linhas.forEach((ln, i) => {
          const d = document.createElement("div"); d.className = "m-imp";
          aplicarVisual(d, v, (ln.tamanho || c.tamanho || 1));
          d.style.position = "absolute";
          conteudo(d, ln.texto, v);
          el.appendChild(d);
        });
        return el;
      },
      atualizar(el, t) {
        const pout = c01((t - (c.fim_out - .2)) / .2);
        [...el.children].forEach((d, i) => {
          const ln = linhas[i];
          const ent = ln.entrada || (c.variar ? variadas[i % variadas.length] : c.entrada);
          const env = envelope({ ini_out: ln.ini_out, fim_out: c.fim_out + 1, opacidade: 1 }, t, ent);
          env.op = r3(env.op * (1 - pout) * (t >= ln.ini_out ? 1 : 0));
          posicionar(d, { x: ln.x ?? c.x ?? .5, y: (c.y ?? .35) + centros[i] / H, rot: ln.rot ?? c.rot ?? 0 }, env);
        });
        return "";
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

  /* -------------------------------------------------------- efeitos */
  function itemFlash(c) {
    return {
      k: "fla" + c.id + (c.cor || ""), z: 95, id: null,
      criar() { const el = document.createElement("div"); el.className = "m-flash"; el.style.background = c.cor || "#FFFFFF"; return el; },
      atualizar(el, t) { const p = c01((t - c.ini_out) / Math.min(.35, c.fim_out - c.ini_out)); el.style.opacity = r3((1 - ease.out(p)) * (c.intensidade ?? .9)); return ""; },
    };
  }

  /* zoom rápido e tremida no vídeo de baixo; mesma conta do FFmpeg (render.py, _expr_efeitos) */
  function efeitoBase(camadas, t) {
    let z = 1, fx = .5, fy = .5, sx = 0, sy = 0;
    for (const c of camadas || []) {
      if (c.tipo !== "efeito" || (c.efeito !== "zoom" && c.efeito !== "tremida")) continue;
      const d = c.efeito === "zoom" && c.estilo === "seco" ? .001 : .14;
      const r = c01(Math.min((t - c.ini_out) / d, (c.fim_out - t) / d));
      if (!r) continue;
      if (c.efeito === "zoom") {
        z += ((c.intensidade ?? 1.18) - 1) * r;
        fx += ((c.x ?? .5) - .5) * r; fy += ((c.y ?? .45) - .5) * r;
      } else {
        const amp = (c.intensidade ?? 1) * .012;
        z += .05 * r; sx += amp * r * Math.sin(t * 71); sy += amp * r * Math.cos(t * 59);
      }
    }
    return { z, fx, fy, sx, sy };
  }

  /* -------------------------------------------------------- cena */
  function itens(ctx, t) {
    const { plano } = ctx;
    const lista = [];
    let visiveis = (plano.camadas || []).filter(c => t >= c.ini_out && t < c.fim_out);
    if (ctx.camada === "atras-nada") return [];
    if (ctx.camada === "atras") visiveis = visiveis.filter(c => c.atras);
    else if (ctx.camada === "frente") visiveis = visiveis.filter(c => !c.atras);
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
      else if (c.tipo === "cascata") lista.push(itemCascata(c, ctx));
      else if (c.tipo === "efeito" && c.efeito === "flash") lista.push(itemFlash(c));
    }
    if (ctx.camada === "atras") return lista;
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
    for (const f of [ctx.plano.gancho_fonte_texto, ctx.plano.gancho_fonte_destaque2]) if (f) vis.push({ fonte: f }, { fonte: f, italico: true });
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
    efeitoBase,
  };
})(window);
