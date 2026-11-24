"""Vai e volta entre o chat e a interface.

entregar: o Claude terminou a edição e passa a vez pra pessoa (guarda uma foto do projeto).
A pessoa confere na interface, clica em "confirmar alterações" (com recado opcional) e
avisa no chat que conferiu. Aí o Claude roda resumo(): o que ela mudou desde a entrega.
"""

import json
import os
import shutil
import time

from . import projeto as P


def _foto(pasta):
    return os.path.join(pasta, "_previa", "entregue.json")


def entregar(pasta):
    os.makedirs(os.path.join(pasta, "_previa"), exist_ok=True)
    shutil.copyfile(os.path.join(pasta, "projeto.json"), _foto(pasta))
    agora = time.time()
    P.escrever_estado(pasta, revisao="com a pessoa", entregue=agora, confirmado=None, recado=None,
                      mensagem="sua vez: confira, ajuste e clique em confirmar alterações")
    return agora


def _txt(pal, idx):
    return " ".join(pal[i]["t"].strip() for i in idx if i < len(pal))


def _faixas(idx):
    """[3,4,5,9] -> [[3,5],[9,9]]"""
    out = []
    for i in sorted(idx):
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def _nome_camada(c):
    tipo = c.get("tipo")
    if tipo in ("impacto", "texto"):
        return f"{tipo} \"{c.get('texto', '')}\""
    if tipo == "cascata":
        return "cascata \"" + " / ".join(l.get("texto", "") for l in c.get("linhas") or []) + "\""
    if tipo in ("imagem", "video"):
        return f"{tipo} {c.get('arquivo')}"
    return f"{tipo} {c.get('efeito') or c.get('som') or ''}".strip()


def _dif_dict(a, b, ignora=()):
    a, b = a or {}, b or {}
    return {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if k not in ignora and a.get(k) != b.get(k)}


def resumo(pasta, recado=None):
    try:
        with open(_foto(pasta), encoding="utf-8") as f:
            antes = json.load(f)
    except (OSError, ValueError):
        antes = None
    depois = P.carregar(pasta)
    linhas = []
    if recado and recado.strip():
        linhas.append(f"RECADO DA PESSOA: {recado.strip()}")
    if antes is None:
        linhas.append("(sem foto da entrega pra comparar; leia texto e camadas de novo)")
        return "\n".join(linhas)

    pa, pd = antes.get("palavras", []), depois.get("palavras", [])
    if len(pa) == len(pd):
        cortou = [i for i in range(len(pd)) if pd[i].get("cortada") and not pa[i].get("cortada")]
        voltou = [i for i in range(len(pd)) if pa[i].get("cortada") and not pd[i].get("cortada")]
        dest = [i for i in range(len(pd)) if pd[i].get("destaque") != pa[i].get("destaque")]
        for a, b in _faixas(cortou):
            linhas.append(f"cortou {a}-{b}: {_txt(pd, range(a, b + 1))}")
        for a, b in _faixas(voltou):
            linhas.append(f"trouxe de volta {a}-{b}: {_txt(pd, range(a, b + 1))}")
        if dest:
            linhas.append("mudou destaque em: " + ", ".join(f"{i}:{pd[i]['t'].strip()}" for i in dest[:20]))
    else:
        linhas.append("a transcrição mudou de tamanho; leia o texto de novo")
    if antes.get("cortes_tempo") != depois.get("cortes_tempo"):
        linhas.append("mexeu nos cortes feitos na linha do tempo")

    ca = {c["id"]: c for c in antes.get("camadas", []) if c.get("id")}
    cd = {c["id"]: c for c in depois.get("camadas", []) if c.get("id")}
    for i in cd.keys() - ca.keys():
        linhas.append(f"camada nova: {_nome_camada(cd[i])} ({i})")
    for i in ca.keys() - cd.keys():
        linhas.append(f"apagou camada: {_nome_camada(ca[i])} ({i})")
    for i in ca.keys() & cd.keys():
        d = _dif_dict(ca[i], cd[i])
        if d:
            linhas.append(f"mudou {_nome_camada(cd[i])} ({i}): " + ", ".join(sorted(d)))

    g = _dif_dict(antes.get("gancho"), depois.get("gancho"), ignora=("visual",))
    if g:
        linhas.append("gancho: " + "; ".join(f"{k} {v[0]!r} -> {v[1]!r}" for k, v in sorted(g.items())))
    if (antes.get("gancho") or {}).get("visual") != (depois.get("gancho") or {}).get("visual"):
        linhas.append("mudou o visual do gancho")
    lv = _dif_dict((antes.get("legenda") or {}).get("visual"), (depois.get("legenda") or {}).get("visual"))
    if lv:
        linhas.append("legenda: " + "; ".join(f"{k} {v[0]!r} -> {v[1]!r}" for k, v in sorted(lv.items())))
    leg = _dif_dict(antes.get("legenda"), depois.get("legenda"), ignora=("visual",))
    if leg:
        linhas.append("legenda: " + "; ".join(f"{k} {v[0]!r} -> {v[1]!r}" for k, v in sorted(leg.items())))
    for chave, nome in (("fontes", "fontes"), ("cor", "cor"), ("ajustes", "ajustes"), ("formato", "formato"),
                        ("trilha", "trilha")):
        d = _dif_dict(antes.get(chave), depois.get(chave))
        if d:
            linhas.append(f"{nome}: " + "; ".join(f"{k} {v[0]!r} -> {v[1]!r}" for k, v in sorted(d.items())))
    qa = {a["id"]: a.get("quadro") for a in antes.get("arquivos") or []}
    for a in depois.get("arquivos") or []:
        if a.get("quadro") != qa.get(a["id"]):
            linhas.append(f"enquadramento de {a['nome']}: {a.get('quadro')}")
    if len(linhas) == (1 if recado and recado.strip() else 0):
        linhas.append("não mudou nada: aprovou do jeito que estava")
    return "\n".join(linhas)
