"""Energia do áudio (volume em dB a cada 10 ms) pra acertar as emendas pela onda.

Guardada em _previa/energia.json na pasta do projeto; o caminho fica em
proj["energia_arquivo"] pra o plano achar sem saber a pasta.
"""

import json
import os
import subprocess

PASSO = 0.01        # 10 ms por valor
_cache = {}


def calcular(pasta, proj):
    from . import projeto as P
    midia = P.midia_previa(proj)
    destino = os.path.join(pasta, "_previa", "energia.json")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    import numpy as np
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-i", midia, "-vn", "-ac", "1", "-ar", "16000",
                            "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(bruto, np.int16).astype(np.float32) / 32768.0
    n = int(16000 * PASSO)
    k = len(x) // n
    rms = np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(axis=1) + 1e-10)
    db = np.round(20 * np.log10(rms + 1e-9)).astype(int).tolist()
    piso = float(np.percentile(db, 10)) if db else -60.0
    with open(destino, "w") as f:
        json.dump({"passo": PASSO, "db": db, "piso": piso, "midia": midia}, f)
    proj["energia_arquivo"] = destino
    return destino


def carregar(proj):
    arq = proj.get("energia_arquivo")
    if not arq or not os.path.exists(arq):
        return None
    m = os.path.getmtime(arq)
    if arq not in _cache or _cache[arq][0] != m:
        with open(arq) as f:
            _cache[arq] = (m, json.load(f))
    return _cache[arq][1]


def voz(e, t0, t1, acima=12.0):
    """Primeiro e último instante com voz entre t0 e t1 (None se não tiver)."""
    if not e:
        return None
    db, passo, limiar = e["db"], e["passo"], e["piso"] + acima
    i0, i1 = max(0, int(t0 / passo)), min(len(db), int(t1 / passo) + 1)
    com = [i for i in range(i0, i1) if db[i] >= limiar]
    if not com:
        return None
    return com[0] * passo, (com[-1] + 1) * passo


def media(e, t0, t1):
    if not e:
        return None
    db, passo = e["db"], e["passo"]
    trecho = db[max(0, int(t0 / passo)):int(t1 / passo) + 1]
    return sum(trecho) / len(trecho) if trecho else None
