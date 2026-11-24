"""Transforma o projeto num plano de edição.

O plano diz quais trechos do vídeo original ficam (segmentos), onde cada
bloco de legenda aparece no vídeo editado e quando entram gancho e títulos.
A interface usa o plano pra prévia e o render usa o mesmo plano pra
exportar, então o que a pessoa vê é o que sai.
"""

import re

from . import estilos as E

PONTUACAO_FINAL = re.compile(r"[.!?…]$")
PONTUACAO_PAUSA = re.compile(r"[,;:]$")


def limpar_texto(t, sem_pontuacao=True, caixa_alta=False):
    t = t.strip()
    if sem_pontuacao:
        # tira pontuação das pontas, mantém interrogação (muda o sentido da frase)
        t = re.sub(r"^[\"'“”‘’(\[«»\-–—]+", "", t)
        t = re.sub(r"[\"'“”‘’)\]«».,;:!…\-–—]+$", "", t)
    if caixa_alta:
        t = t.upper()
    return t


def cor_final(cor):
    """Curvas por canal + saturação + nitidez. Prévia (SVG) e exportação (FFmpeg) usam os mesmos números."""
    from . import cor as C
    cv = C.curvas(cor)
    identidade = [round(i / 16, 4) for i in range(17)]
    cv["nitidez"] = round(float((cor or {}).get("nitidez", 0) or 0), 3)
    from . import projeto as P
    lut = C.luts(P.dados_dir()).get((cor or {}).get("look") or "")
    cv["lut"] = ({"id": cor["look"], "arquivo": lut["arquivo"], "url": lut["url"],
                  "intensidade": max(0.0, min(1.0, float(cor.get("intensidade", 1.0))))} if lut else None)
    cv["neutra"] = (cv["r"] == identidade and cv["g"] == identidade and cv["b"] == identidade
                    and abs(cv["saturacao"] - 1) < 1e-3)
    return cv


def calcular_segmentos(proj):
    palavras = proj.get("palavras", [])
    aj = proj.get("ajustes", {})
    folga = float(aj.get("folga", 0.10))
    pausa_max = float(aj.get("pausa_max", 0.40))
    cortar_pausas = bool(aj.get("cortar_pausas", True))
    duracao = float(proj.get("info", {}).get("duracao", 0)) or (palavras[-1]["fim"] + 1 if palavras else 0)


    segs = []
    atual = None
    anterior = None
    corte_ini = None   # início da primeira palavra cortada depois da anterior
    corte_fim = None   # fim da última palavra cortada antes da atual

    def folga_depois(p):
        extra = 0.08 if PONTUACAO_FINAL.search(p["t"].strip()) else 0.0
        return folga + extra

    for p in palavras:
        if p.get("cortada"):
            if anterior is not None and corte_ini is None:
                corte_ini = p["ini"]
            corte_fim = p["fim"]
            continue
        if atual is None:
            inicio = p["ini"] - folga
            if corte_fim is not None:
                inicio = max(inicio, corte_fim)
            atual = [max(0.0, min(inicio, p["ini"])), p["fim"]]
            anterior = p
            corte_ini = corte_fim = None
            continue

        pausa = p["ini"] - anterior["fim"]
        tem_corte = corte_ini is not None
        if tem_corte or (cortar_pausas and pausa > pausa_max):
            fim = anterior["fim"] + folga_depois(anterior)
            inicio = p["ini"] - folga
            if tem_corte:
                fim = max(anterior["fim"], min(fim, corte_ini))
                inicio = min(p["ini"], max(inicio, corte_fim))
            else:
                # se a folga das duas pontas encostar, a pausa fica inteira
                meio = (anterior["fim"] + p["ini"]) / 2
                fim = min(fim, meio)
                inicio = max(inicio, meio)
            if inicio <= fim + 0.02:
                atual[1] = p["fim"]
            else:
                atual[1] = fim
                segs.append(atual)
                atual = [inicio, p["fim"]]
        else:
            atual[1] = p["fim"]
        anterior = p
        corte_ini = corte_fim = None

    if atual is not None:
        fim = anterior["fim"] + folga_depois(anterior)
        if corte_ini is not None:
            fim = min(fim, corte_ini)
        atual[1] = min(duracao, max(fim, anterior["fim"]))
        segs.append(atual)
    if not palavras and duracao:
        segs = [[0.0, duracao]]

    # cortes feitos direto na linha do tempo (tempo do vídeo original)
    for c in sorted(proj.get("cortes_tempo", []), key=lambda c: c["ini"]):
        novos = []
        for ini, fim in segs:
            if c["fim"] <= ini or c["ini"] >= fim:
                novos.append([ini, fim])
                continue
            if c["ini"] > ini:
                novos.append([ini, c["ini"]])
            if c["fim"] < fim:
                novos.append([c["fim"], fim])
        segs = novos

    segs = encaixar_arquivos(proj, segs)
    vel = max(0.5, min(2.0, float(aj.get("velocidade", 1.0))))
    saida = []
    acumulado = 0.0
    for ini, fim in segs:
        if fim - ini < 0.04:
            continue
        arq = arquivo_de(proj, (ini + fim) / 2)
        saida.append({"ini": round(ini, 3), "fim": round(fim, 3), "out": round(acumulado, 4), "vel": vel, "zoom": 1.0,
                      "arq": arq})
        acumulado += (fim - ini) / vel
    zoom_nos_cortes(saida, aj.get("zoom_cortes") or {})
    return saida


def arquivo_de(proj, t):
    arqs = proj.get("arquivos") or []
    for k, a in enumerate(arqs):
        if a["ini"] - 1e-3 <= t < a["fim"] + 1e-3:
            return k
    return 0


def encaixar_arquivos(proj, segs):
    """Arquivos só de imagem (clipe de vlog sem fala, paisagem) entram pelo trecho "manter",
    não pelos cortes da fala. Depois tudo é quebrado na emenda entre um arquivo e outro."""
    arqs = proj.get("arquivos") or []
    if not arqs:
        return segs
    imagem = [a for a in arqs if a.get("modo") == "imagem"]
    for a in imagem:
        novos = []
        for ini, fim in segs:
            if fim <= a["ini"] or ini >= a["fim"]:
                novos.append([ini, fim])
                continue
            if ini < a["ini"]:
                novos.append([ini, a["ini"]])
            if fim > a["fim"]:
                novos.append([a["fim"], fim])
        segs = novos
        dur = a["fim"] - a["ini"]
        m = a.get("manter") or [max(0.0, dur / 2 - 1.25), min(dur, dur / 2 + 1.25)]
        m0, m1 = max(0.0, float(m[0])), min(dur, float(m[1]))
        if m1 - m0 > 0.1:
            segs.append([a["ini"] + m0, a["ini"] + m1])
    segs.sort()
    quebrados = []
    for ini, fim in segs:
        for a in arqs:
            ia, ib = max(ini, a["ini"]), min(fim, a["fim"])
            if ib - ia > 0.04:
                quebrados.append([ia, ib])
    return quebrados


def zoom_nos_cortes(segs, cfg):
    """Punch-in pela escala do corte, sem animação: alterna plano normal e plano fechado,
    espalhado de forma regular, nunca dois seguidos (como na edição de referência)."""
    if not cfg.get("ativo") or len(segs) < 3:
        return
    freq = max(0.0, min(0.5, float(cfg.get("frequencia", 0.35))))
    forte = float(cfg.get("intensidade", 1.3))
    leve = 1 + (forte - 1) * 0.72
    n = 0
    for k, s in enumerate(segs):
        if k == 0 or (s["fim"] - s["ini"]) < 0.45 or segs[k - 1]["zoom"] > 1:
            continue
        if int((k + 1) * freq) > int(k * freq):
            s["zoom"] = round(forte if n % 2 == 0 else leve, 3)
            n += 1


def _para_saida(t, segs, idx_seg):
    s = segs[idx_seg]
    t = min(max(t, s["ini"]), s["fim"])
    return s["out"] + (t - s["ini"]) / s.get("vel", 1.0)


def _segmento_de(p, segs):
    meio = (p["ini"] + p["fim"]) / 2
    for i, s in enumerate(segs):
        if s["ini"] - 0.001 <= meio <= s["fim"] + 0.001:
            return i
    for i, s in enumerate(segs):
        if s["ini"] < p["fim"] and p["ini"] < s["fim"]:
            return i
    return None


def montar_plano(proj):
    segs = calcular_segmentos(proj)
    total = (segs[-1]["out"] + (segs[-1]["fim"] - segs[-1]["ini"]) / segs[-1]["vel"]) if segs else 0.0
    leg = proj.get("legenda", {})
    fontes_proj = proj.get("fontes") or {}
    visual = E.resolver_fonte(E.visual_completo(E.LEGENDA_PADRAO, leg.get("visual")), fontes_proj)
    for chave in ("fonte_destaque", "fonte_destaque2"):
        if (visual.get(chave) or "").startswith("@"):
            visual[chave] = E.resolver_fonte({"fonte": visual[chave]}, fontes_proj)["fonte"]
    max_palavras = int(visual.get("palavras") or 3)
    max_letras = int(visual.get("max_caracteres") or E.max_letras(visual) * 2)
    caixa_alta = bool(visual.get("caixa_alta"))
    substitui = visual.get("modo_destaque") == "substitui"
    sem_pont = bool(leg.get("sem_pontuacao", True))

    # palavras que ficam, já com o tempo no vídeo editado
    so_imagem = [(a["ini"], a["fim"]) for a in proj.get("arquivos") or [] if a.get("modo") == "imagem"]
    mantidas = []
    for p in proj.get("palavras", []):
        if p.get("cortada"):
            continue
        meio = (p["ini"] + p["fim"]) / 2
        if any(a <= meio < b for a, b in so_imagem):
            continue
        si = _segmento_de(p, segs) if segs else None
        if si is None:
            continue
        texto = limpar_texto(p["t"], sem_pont, caixa_alta)
        if visual.get("minusculas") and not caixa_alta:
            texto = texto.lower()
        mantidas.append({
            "i": p["i"], "t": texto, "bruto": p["t"].strip(),
            "seg": si, "destaque": bool(p.get("destaque")),
            "ini_src": p["ini"], "fim_src": p["fim"],
            "ini_out": round(_para_saida(p["ini"], segs, si), 3),
            "fim_out": round(_para_saida(p["fim"], segs, si), 3),
        })

    blocos = []
    atual = []
    letras = 0
    for w in mantidas:
        if not w["t"]:
            continue
        quebra = False
        if atual:
            ant = atual[-1]
            if len(atual) >= max_palavras:
                quebra = True
            elif letras + 1 + len(w["t"]) > max_letras:
                quebra = True
            elif PONTUACAO_FINAL.search(ant["bruto"]) or PONTUACAO_PAUSA.search(ant["bruto"]):
                quebra = True
            elif ant["seg"] != w["seg"] and (w["ini_out"] - ant["fim_out"] > 0.01
                                              or segs[ant["seg"]].get("arq") != segs[w["seg"]].get("arq")):
                quebra = True
            elif w["ini_out"] - ant["fim_out"] > 0.6:
                quebra = True
            elif substitui and (w["destaque"] != ant["destaque"] or (w["destaque"] and len(atual) >= 2)):
                quebra = True
        if quebra:
            blocos.append(atual)
            atual, letras = [], 0
        atual.append(w)
        letras += len(w["t"]) + (1 if letras else 0)
    if atual:
        blocos.append(atual)

    saida_blocos = []
    for k, b in enumerate(blocos):
        ini = b[0]["ini_out"]
        fim = b[-1]["fim_out"]
        prox = blocos[k + 1][0]["ini_out"] if k + 1 < len(blocos) else None
        if prox is not None and prox - fim < 0.7:
            fim = prox
        else:
            fim = min(total, fim + 0.25)
        palavras = []
        for j, w in enumerate(b):
            ativa_fim = b[j + 1]["ini_out"] if j + 1 < len(b) else fim
            palavras.append({
                "i": w["i"], "t": w["t"], "destaque": w["destaque"],
                "ini_out": w["ini_out"], "fim_out": round(ativa_fim, 3),
                "ini_src": w["ini_src"], "fim_src": w["fim_src"],
            })
        bloco = {
            "ini_out": round(ini, 3), "fim_out": round(fim, 3),
            "ini_src": b[0]["ini_src"], "fim_src": b[-1]["fim_src"],
            "palavras": palavras,
        }
        if substitui and all(w["destaque"] for w in b):
            bloco["destaque"] = True
            bloco["alt"] = sum(1 for x in saida_blocos if x.get("destaque")) % 2
        saida_blocos.append(bloco)

    # camadas: palavras de impacto, insertos, desenhos e textos fixos.
    # Quem tem "palavra" fica preso ao momento em que ela é falada, então
    # continua sincronizado mesmo depois de novos cortes.
    por_indice = {w["i"]: w for w in mantidas}
    ordenadas = sorted(mantidas, key=lambda w: w["i"])
    todas = list(proj.get("camadas", []))
    for k, t in enumerate(proj.get("titulos", [])):   # projetos antigos
        todas.append({"id": f"titulo-{k}", "tipo": "texto", "estilo": "titulo", "texto": t.get("texto", ""),
                      "palavra": t.get("palavra"), "duracao": t.get("duracao", 2.0), "x": 0.5, "y": 0.2})
    camadas = []
    for c in todas:
        if c.get("oculta"):
            continue
        def tempo_da(i):
            alvo = por_indice.get(i)
            if alvo is None:
                alvo = next((w for w in ordenadas if w["i"] >= i), None)
            return None if alvo is None else alvo["ini_out"]

        linhas = None
        if c.get("tipo") == "cascata":
            linhas = []
            for ln in c.get("linhas") or []:
                t0 = tempo_da(ln["palavra"]) if ln.get("palavra") is not None else ln.get("ini")
                if t0 is not None:
                    linhas.append({**ln, "ini_out": round(t0, 3)})
            if not linhas:
                continue
            c = {**c, "palavra": None, "ini": linhas[0]["ini_out"]}
            if c.get("palavra_fim") is not None and tempo_da(c["palavra_fim"]) is not None:
                c["duracao"] = max(0.4, tempo_da(c["palavra_fim"]) - linhas[0]["ini_out"])
            else:
                c.setdefault("duracao", linhas[-1]["ini_out"] - linhas[0]["ini_out"] + 1.3)
        if c.get("palavra") is not None:
            t0 = tempo_da(c["palavra"])
            if t0 is None:
                continue
            ini = t0 + float(c.get("atraso", 0))
        else:
            ini = float(c.get("ini", 0))
        ini = max(0.0, min(ini, total))
        dur_padrao = 0.6 if c.get("tipo") == "som" else 2.0
        fim = total if c.get("ate_o_fim") else min(total, ini + float(c.get("duracao", dur_padrao)))
        if fim - ini < 0.05:
            continue
        extra = {"linhas": linhas} if linhas else {}
        if c.get("tipo") in ("impacto", "texto", "cascata"):
            tabela, padrao = {"impacto": (E.IMPACTO, "pincel"), "texto": (E.TEXTOS, "frase"),
                              "cascata": (E.CASCATA, "padrao")}[c["tipo"]]
            d = tabela.get(c.get("estilo")) or tabela[padrao]
            extra = {**extra, "visual": E.resolver_fonte(E.visual_completo(d["visual"], c.get("visual")), fontes_proj),
                     "entrada": c.get("entrada") or d["entrada"],
                     "rot": c.get("rot", d.get("rotacao", 0))}
        camadas.append({**c, **extra, "ini_out": round(ini, 3), "fim_out": round(fim, 3)})

    for c in camadas:
        if c.get("tipo") == "efeito" and c.get("efeito") == "escada":
            passos = [1.15, 1.3, 1.45, 1.6]
            n = 0
            for s in segs:
                fim_s = s["out"] + (s["fim"] - s["ini"]) / s["vel"]
                if fim_s > c["ini_out"] + 0.05 and s["out"] < c["fim_out"] - 0.05:
                    s["zoom"] = passos[min(n, len(passos) - 1)]
                    n += 1

    gancho = None
    g = proj.get("gancho", {})
    if g.get("ativo") and g.get("texto", "").strip():
        gancho = {"texto": g["texto"].strip(), "ini_out": 0.0,
                  "fim_out": round(min(total, float(g.get("duracao", 3.0))), 3),
                  "posicao": float(g.get("posicao", 0.2))}

    sons = []
    aj = proj.get("ajustes", {})
    auto = bool(aj.get("sons_auto"))
    from .estilos import SONS_MAPA
    mapa = {**SONS_MAPA, **(aj.get("sons_mapa") or {})}
    vol_geral = float(mapa.get("volume", 1.0))

    def som(nome, t, vol, origem=None):
        if nome and nome != "nenhum" and 0 <= t < total:
            sons.append({"som": nome, "ini_out": round(max(0.0, t), 3), "volume": round(vol, 3), "id": origem})

    def auto_som(momento, t, vol, origem=None, alt=0):
        nome = mapa.get(momento)
        if isinstance(nome, list):
            nome = nome[alt % len(nome)] if nome else None
        som(nome, t, vol * vol_geral, origem)

    for c in camadas:
        tipo = c.get("tipo")
        cartao = tipo in ("imagem", "video") and c.get("modo") in ("cartao", "metade")
        adiant = -0.12 if cartao else (-0.08 if tipo in ("impacto", "texto", "cascata") else 0.0)
        if tipo == "som":
            som(c.get("som"), c["ini_out"], float(c.get("volume", 0.6)), c.get("id"))
        elif c.get("som"):
            som(c["som"], c["ini_out"] + float(c.get("som_atraso", adiant)), float(c.get("som_volume", 0.3)), c.get("id"))
        elif auto:
            # o som acompanha o texto e a imagem que entra, nunca o corte
            if tipo == "cascata":
                for ln in c.get("linhas") or []:
                    auto_som("palavra", ln["ini_out"] - 0.08, 0.26, c.get("id"))
            elif tipo == "impacto":
                auto_som("palavra", c["ini_out"] - 0.08, 0.28, c.get("id"))
            elif tipo == "texto":
                cta = c.get("estilo") == "cta"
                auto_som("cta" if cta else "texto", c["ini_out"] - (0 if cta else 0.08), 0.26, c.get("id"))
            elif cartao and c.get("entrada") != "nenhuma":
                auto_som("foto", c["ini_out"] - 0.12, 0.3, c.get("id"))
    if auto:
        for b in saida_blocos if leg.get("ativa", True) else []:
            if b.get("destaque"):
                auto_som("destaque", b["ini_out"] - 0.06, 0.24, alt=b.get("alt", 0))

    duracao_original = float(proj.get("info", {}).get("duracao", 0))
    return {
        "segmentos": segs,
        "blocos": saida_blocos if leg.get("ativa", True) else [],
        "camadas": camadas,
        "sons": sons,
        "cor": cor_final(proj.get("cor")),
        "trilha": proj.get("trilha") if (proj.get("trilha") or {}).get("arquivo") else None,
        "gancho": gancho,
        "legenda": visual,
        "gancho_visual": E.resolver_fonte(E.visual_completo(E.GANCHO_PADRAO, proj.get("gancho", {}).get("visual")), fontes_proj),
        "duracao_saida": round(total, 3),
        "duracao_original": round(duracao_original, 3),
        "cortes": max(0, len(segs) - 1),
        "velocidade": segs[0]["vel"] if segs else 1.0,
    }
