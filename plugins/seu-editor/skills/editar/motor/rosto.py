"""Onde está o rosto da pessoa em cada arquivo (pra centralizar zoom e enquadramento).

Usa o mesmo modelo que recorta a pessoa (MODNet): em alguns quadros espalhados pelo
arquivo, acha o topo da cabeça e a largura da cabeça, e estima a altura dos olhos.
Como a pessoa grava de tripé, a mediana dos quadros basta: um ponto fixo por arquivo,
e o vídeo não fica mexendo.
"""

import subprocess

from . import recorte as R


def _quadro(video, t, mw, mh):
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                            "-vf", f"scale={mw}:{mh}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           capture_output=True).stdout
    return bruto if len(bruto) == mw * mh * 3 else None


def achar(video, ini, fim, largura, altura, n=11):
    """Devolve {"x", "y", "largura"} em fração do quadro do arquivo, ou None."""
    import numpy as np
    sessao = R._modelo()
    mw, mh = R._tamanho_modelo(largura, altura, lado=320)
    xs, ys, ls = [], [], []
    dur = max(0.1, fim - ini)
    for k in range(n):
        t = ini + dur * (k + 0.5) / n
        bruto = _quadro(video, t, mw, mh)
        if bruto is None:
            continue
        x = np.frombuffer(bruto, np.uint8).reshape(mh, mw, 3).astype(np.float32) / 127.5 - 1.0
        m = sessao.run(None, {"input": x.transpose(2, 0, 1)[None]})[0][0, 0] > 0.5
        linhas = np.where(m.sum(axis=1) > max(3, 0.02 * mw))[0]
        if len(linhas) < mh * 0.1 or m.sum() < 0.05 * mw * mh:
            continue      # sem pessoa de verdade nesse quadro
        topo = int(linhas[0])
        # largura da cabeça: mede numa faixa abaixo do topo proporcional à própria
        # cabeça (repete 3 vezes pra convergir, sem pegar os ombros)
        lc = 0.1 * mw
        larguras, centros = [], []
        for _ in range(3):
            faixa = range(topo + int(0.35 * lc), min(mh, topo + max(int(0.35 * lc) + 2, int(0.75 * lc))))
            larguras, centros = [], []
            for r in faixa:
                cols = np.where(m[r])[0]
                if len(cols):
                    larguras.append(cols[-1] - cols[0])
                    centros.append((cols[-1] + cols[0]) / 2)
            if not larguras:
                break
            lc = float(np.median(larguras))
        if not larguras:
            continue
        lc = float(np.median(larguras))
        xs.append(float(np.median(centros)) / mw)
        ys.append((topo + 0.8 * lc) / mh)       # altura aproximada dos olhos (cabelo incluso)
        ls.append(lc / mw)
    if len(xs) < 2:
        return None
    # fica com os quadros que concordam com a maioria (descarta quadro sem a pessoa
    # ou com outra coisa recortada)
    perto = lambda a, b: abs(xs[a] - xs[b]) < 0.07 and abs(ys[a] - ys[b]) < 0.07
    centro = max(range(len(xs)), key=lambda a: sum(perto(a, b) for b in range(len(xs))))
    bons = [k for k in range(len(xs)) if perto(centro, k)]
    if len(bons) < max(2, (n + 1) // 3):
        return None
    pega = lambda v: round(float(np.median([v[k] for k in bons])), 4)
    return {"x": pega(xs), "y": pega(ys), "largura": pega(ls)}


def marcar_arquivos(proj, log=print):
    """Acha o rosto em cada arquivo de vídeo que ainda não tem. Falha em silêncio."""
    mudou = False
    for a in proj.get("arquivos") or []:
        if a.get("tipo") != "video" or a.get("rosto") is not None:
            continue
        inf = a.get("info") or {}
        try:
            dur = a["fim"] - a["ini"]
            r = achar(a["arquivo"], 0.0, dur, int(inf.get("largura", 1080)), int(inf.get("altura", 1920)))
        except Exception as e:     # sem modelo, sem rede: segue sem centralizar
            log(f"não consegui achar o rosto em {a.get('nome')}: {e}")
            r = None
        a["rosto"] = r or False
        mudou = True
    return mudou
