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


def calcular_segmentos(proj):
    palavras = proj.get("palavras", [])
    aj = proj.get("ajustes", {})
    folga = float(aj.get("folga", 0.10))
    pausa_max = float(aj.get("pausa_max", 0.40))
    cortar_pausas = bool(aj.get("cortar_pausas", True))
    duracao = float(proj.get("info", {}).get("duracao", 0)) or (palavras[-1]["fim"] + 1 if palavras else 0)

    if not palavras:
        return [{"ini": 0.0, "fim": duracao, "out": 0.0}] if duracao else []

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

    saida = []
    acumulado = 0.0
    for ini, fim in segs:
        if fim - ini < 0.04:
            continue
        saida.append({"ini": round(ini, 3), "fim": round(fim, 3), "out": round(acumulado, 3)})
        acumulado += fim - ini
    return saida


def _para_saida(t, segs, idx_seg):
    s = segs[idx_seg]
    t = min(max(t, s["ini"]), s["fim"])
    return s["out"] + (t - s["ini"])


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
    total = (segs[-1]["out"] + segs[-1]["fim"] - segs[-1]["ini"]) if segs else 0.0
    leg = proj.get("legenda", {})
    fontes_proj = proj.get("fontes") or {}
    visual = E.resolver_fonte(E.visual_completo(E.LEGENDA_PADRAO, leg.get("visual")), fontes_proj)
    max_palavras = int(visual.get("palavras") or 3)
    max_letras = E.max_letras(visual) * 2   # até duas linhas por bloco
    caixa_alta = bool(visual.get("caixa_alta"))
    sem_pont = bool(leg.get("sem_pontuacao", True))

    # palavras que ficam, já com o tempo no vídeo editado
    mantidas = []
    for p in proj.get("palavras", []):
        if p.get("cortada"):
            continue
        si = _segmento_de(p, segs) if segs else None
        if si is None:
            continue
        texto = limpar_texto(p["t"], sem_pont, caixa_alta)
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
            elif ant["seg"] != w["seg"] and w["ini_out"] - ant["fim_out"] > 0.01:
                quebra = True
            elif w["ini_out"] - ant["fim_out"] > 0.6:
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
        saida_blocos.append({
            "ini_out": round(ini, 3), "fim_out": round(fim, 3),
            "ini_src": b[0]["ini_src"], "fim_src": b[-1]["fim_src"],
            "palavras": palavras,
        })

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
        if c.get("palavra") is not None:
            alvo = por_indice.get(c["palavra"])
            if alvo is None:
                alvo = next((w for w in ordenadas if w["i"] >= c["palavra"]), None)
            if alvo is None:
                continue
            ini = alvo["ini_out"] + float(c.get("atraso", 0))
        else:
            ini = float(c.get("ini", 0))
        ini = max(0.0, min(ini, total))
        fim = total if c.get("ate_o_fim") else min(total, ini + float(c.get("duracao", 2.0)))
        if fim - ini < 0.05:
            continue
        extra = {}
        if c.get("tipo") in ("impacto", "texto"):
            tabela, padrao = (E.IMPACTO, "pincel") if c["tipo"] == "impacto" else (E.TEXTOS, "frase")
            d = tabela.get(c.get("estilo")) or tabela[padrao]
            extra = {"visual": E.resolver_fonte(E.visual_completo(d["visual"], c.get("visual")), fontes_proj),
                     "entrada": c.get("entrada") or d["entrada"],
                     "rot": c.get("rot", d.get("rotacao", 0))}
        camadas.append({**c, **extra, "ini_out": round(ini, 3), "fim_out": round(fim, 3)})

    gancho = None
    g = proj.get("gancho", {})
    if g.get("ativo") and g.get("texto", "").strip():
        gancho = {"texto": g["texto"].strip(), "ini_out": 0.0,
                  "fim_out": round(min(total, float(g.get("duracao", 3.0))), 3),
                  "posicao": float(g.get("posicao", 0.2))}

    duracao_original = float(proj.get("info", {}).get("duracao", 0))
    return {
        "segmentos": segs,
        "blocos": saida_blocos if leg.get("ativa", True) else [],
        "camadas": camadas,
        "gancho": gancho,
        "legenda": visual,
        "gancho_visual": E.resolver_fonte(E.visual_completo(E.GANCHO_PADRAO, proj.get("gancho", {}).get("visual")), fontes_proj),
        "duracao_saida": round(total, 3),
        "duracao_original": round(duracao_original, 3),
        "cortes": max(0, len(segs) - 1),
    }
