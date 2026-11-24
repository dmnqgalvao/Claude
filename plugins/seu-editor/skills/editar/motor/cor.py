"""Correção de cor automática.

Olha um quadro por segundo do vídeo (bem pequeno) e calcula:
- ganho por canal (balanço de branco pelo método do "mundo cinza": a média
  das cores de uma cena tende ao cinza, então o canal que sobra é dominante);
- brilho: puxa a luz média pra perto de 47%;
- contraste: estica um pouco quando a imagem está lavada.

Os limites são conservadores pra não estragar vídeo que já está bom.
"""

import subprocess

# Filtros (looks). Cada um é uma curva de tons por canal: contraste em S, cor nas sombras,
# cor nas luzes, preto desbotado e um ganho por canal, mais a saturação. A mesma curva vira
# o filtro "curves" do FFmpeg na exportação e uma tabela do SVG na prévia.
#   sombras / luzes: quanto somar em (vermelho, verde, azul) nas partes escuras / claras
#   desbota: quanto o preto sobe (ar de filme)      s: força do contraste em S
#   ganho: multiplicador por canal (temperatura)    sat: saturação
LOOKS = {
    "nenhum":  {"nome": "original"},
    "natural": {"nome": "natural", "s": .18, "sat": 1.06},
    "dourado": {"nome": "dourado", "s": .22, "sat": 1.1, "ganho": (1.04, 1.0, .94),
                "luzes": (.09, .045, -.06), "sombras": (.035, .005, -.035)},
    "pessego": {"nome": "pêssego", "s": .04, "sat": .95, "brilho": .05, "desbota": .05,
                "luzes": (.08, .02, .035), "sombras": (.05, 0, .02)},
    "verao":   {"nome": "verão", "s": .35, "sat": 1.28, "ganho": (1.05, 1.01, .95),
                "luzes": (.06, .045, -.05)},
    "frio":    {"nome": "frio limpo", "s": .26, "sat": .92, "ganho": (.97, 1.0, 1.05),
                "sombras": (-.025, .015, .08), "luzes": (-.02, 0, .035)},
    "cinema":  {"nome": "cinema", "s": .34, "sat": 1.05,
                "sombras": (-.05, .035, .09), "luzes": (.08, .03, -.065)},
    "filme":   {"nome": "filme", "s": .12, "sat": .78, "desbota": .09, "teto": .93,
                "sombras": (0, .035, .02), "luzes": (.03, .03, -.02)},
    "suave":   {"nome": "suave", "s": -.2, "sat": .85, "brilho": .06, "desbota": .06,
                "luzes": (.03, 0, .035)},
    "pb":      {"nome": "preto e branco", "s": .35, "sat": 0},
}
APELIDOS = {"quente": "dourado", "quente_nitido": "dourado", "vivo": "verao"}
# compatibilidade com o comando antigo `cor --filtro`
FILTROS = {k: {} for k in list(LOOKS) + list(APELIDOS)}


def _s(x):
    return x * x * (3 - 2 * x)


def curvas(cor, pontos=17):
    """Curva final (r, g, b) com o filtro, a intensidade e os ajustes da pessoa."""
    cor = cor or {}
    nome = APELIDOS.get(cor.get("look") or "nenhum", cor.get("look") or "nenhum")
    lk = LOOKS.get(nome, LOOKS["nenhum"])
    k = max(0.0, min(1.0, float(cor.get("intensidade", 1.0))))
    ganho_auto = cor.get("ganhos") if cor.get("auto") else (1, 1, 1)
    t = float(cor.get("temperatura", 0))
    ganho_t = (1 + .08 * t, 1 + .012 * t, 1 - .08 * t)
    s_extra = (float(cor.get("contraste", 1)) - 1) * 1.2 + ((cor.get("auto_contraste", 1) - 1) * 1.2 if cor.get("auto") else 0)
    brilho = float(cor.get("brilho", 0)) + (cor.get("auto_brilho", 0) if cor.get("auto") else 0)
    saida = []
    for ch in range(3):
        linha = []
        for i in range(pontos):
            x = i / (pontos - 1)
            # o filtro
            y = x * (lk.get("ganho") or (1, 1, 1))[ch]
            y = y + lk.get("s", 0) * (_s(min(1, max(0, y))) - y)
            if lk.get("brilho"):
                y = max(0, y) ** (1 / (1 + 1.6 * lk["brilho"]))
            w_s, w_l = (1 - y) ** 2, y ** 2
            y += (lk.get("sombras") or (0, 0, 0))[ch] * w_s + (lk.get("luzes") or (0, 0, 0))[ch] * w_l
            y = lk.get("desbota", 0) + y * (lk.get("teto", 1) - lk.get("desbota", 0))
            y = x + k * (y - x)
            # correção automática e ajustes da pessoa, por cima
            y *= ganho_auto[ch] * ganho_t[ch]
            y = min(1, max(0, y))
            if s_extra:
                y = y + s_extra * (_s(y) - y)
            if brilho:
                y = max(0, y) ** (1 / (1 + 1.6 * brilho))
            linha.append(round(min(1, max(0, y)), 4))
        saida.append(linha)
    sat_look = lk.get("sat", 1)
    sat = (1 + k * (sat_look - 1)) * float(cor.get("saturacao", 1))
    return {"r": saida[0], "g": saida[1], "b": saida[2], "saturacao": round(sat, 4)}


def looks_para_interface():
    return {nome: {"nome": lk["nome"], **curvas({"look": nome})} for nome, lk in LOOKS.items()}


def analisar(video, maximo_quadros=40):
    duracao = 0.0
    try:
        duracao = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                        "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip())
    except ValueError:
        pass
    fps = min(1.0, maximo_quadros / duracao) if duracao > 0 else 1.0
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps={fps:.4f},scale=48:-2,format=rgb24",
                            "-f", "rawvideo", "-"], capture_output=True).stdout
    if not bruto:
        return {"ganhos": [1.0, 1.0, 1.0], "auto_brilho": 0.0, "auto_contraste": 1.0}
    n = len(bruto) // 3
    passo = max(1, n // 60000)
    soma = [0.0, 0.0, 0.0]
    lum, lum2, conta = 0.0, 0.0, 0
    for i in range(0, n, passo):
        r, g, b = bruto[3 * i], bruto[3 * i + 1], bruto[3 * i + 2]
        soma[0] += r; soma[1] += g; soma[2] += b
        y = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
        lum += y; lum2 += y * y; conta += 1
    medias = [s / conta for s in soma]
    cinza = sum(medias) / 3
    ganhos = [max(0.82, min(1.22, cinza / max(1.0, m))) for m in medias]
    media = lum / conta
    desvio = max(1e-3, (lum2 / conta - media * media) ** 0.5)
    brilho = max(-0.1, min(0.1, (0.47 - media) * 0.6))
    contraste = max(0.94, min(1.2, 0.21 / desvio))
    return {"ganhos": [round(g, 4) for g in ganhos], "auto_brilho": round(brilho, 4),
            "auto_contraste": round(contraste, 4)}
