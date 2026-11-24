"""Correção de cor automática.

Olha um quadro por segundo do vídeo (bem pequeno) e calcula:
- ganho por canal (balanço de branco pelo método do "mundo cinza": a média
  das cores de uma cena tende ao cinza, então o canal que sobra é dominante);
- brilho: puxa a luz média pra perto de 47%;
- contraste: estica um pouco quando a imagem está lavada.

Os limites são conservadores pra não estragar vídeo que já está bom.
"""

import subprocess

FILTROS = {
    "nenhum":  {"brilho": 0.0, "contraste": 1.0, "saturacao": 1.0, "temperatura": 0.0, "nitidez": 0.0},
    "quente_nitido": {"brilho": 0.01, "contraste": 1.06, "saturacao": 1.1, "temperatura": 0.35, "nitidez": 0.6},
    "quente":  {"brilho": 0.01, "contraste": 1.03, "saturacao": 1.08, "temperatura": 0.55},
    "frio":    {"brilho": 0.0, "contraste": 1.04, "saturacao": 0.95, "temperatura": -0.45},
    "vivo":    {"brilho": 0.01, "contraste": 1.1, "saturacao": 1.3, "temperatura": 0.05},
    "suave":   {"brilho": 0.035, "contraste": 0.9, "saturacao": 0.88, "temperatura": 0.15},
    "filme":   {"brilho": -0.01, "contraste": 1.08, "saturacao": 0.82, "temperatura": 0.25},
    "pb":      {"brilho": 0.0, "contraste": 1.15, "saturacao": 0.0, "temperatura": 0.0},
}


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
