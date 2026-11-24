"""Recorte da pessoa, pra colocar fotos, vídeos e textos ATRÁS dela.

Usa o MODNet (recorte de retrato, licença Apache 2.0), que roda no próprio
computador. O modelo (25 MB) é baixado na primeira vez em ~/.seu-editor/modelos.

Pra cada trecho em que existe camada "atrás", decodifica os quadros, calcula a
máscara da pessoa, suaviza no tempo (evita tremedeira na borda) e grava um
vídeo só com a pessoa e fundo transparente. Na exportação esse vídeo vai por
cima das camadas de trás; na prévia, um webm com transparência faz o mesmo.
"""

import os
import subprocess
import urllib.request

from . import projeto as P

URL_MODELO = "https://huggingface.co/Xenova/modnet/resolve/main/onnx/model.onnx"
_sessao = None


def _modelo():
    global _sessao
    if _sessao is None:
        import onnxruntime as ort
        pasta = os.path.join(P.dados_dir(), "modelos")
        os.makedirs(pasta, exist_ok=True)
        caminho = os.path.join(pasta, "modnet.onnx")
        if not os.path.exists(caminho):
            tmp = caminho + ".baixando"
            with urllib.request.urlopen(URL_MODELO, timeout=120) as r, open(tmp, "wb") as f:
                f.write(r.read())
            os.replace(tmp, caminho)
        opcoes = ort.SessionOptions()
        opcoes.intra_op_num_threads = max(1, (os.cpu_count() or 4) - 1)
        provedores = [p for p in ("CoreMLExecutionProvider", "CUDAExecutionProvider") if p in ort.get_available_providers()]
        _sessao = ort.InferenceSession(caminho, opcoes, providers=provedores + ["CPUExecutionProvider"])
    return _sessao


def _tamanho_modelo(largura, altura, lado=384):
    esc = lado / min(largura, altura)
    return max(32, int(round(largura * esc / 32)) * 32), max(32, int(round(altura * esc / 32)) * 32)


def recortar(video, ini, dur, largura, altura, fps, saida, previa=False, aviso=None):
    """Gera `saida` com a pessoa recortada do trecho [ini, ini+dur] de `video`.

    previa=False: .mov com canal alfa (qtrle), do tamanho largura x altura.
    previa=True:  .webm VP9 com alfa, leve, pra tocar no navegador.
    """
    import numpy as np
    sessao = _modelo()
    mw, mh = _tamanho_modelo(largura, altura)
    leitura = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-ss", f"{ini:.3f}", "-t", f"{dur:.3f}", "-i", video,
         "-vf", f"fps={fps},scale={mw}:{mh}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    if previa:
        codec = ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "34", "-deadline", "realtime",
                 "-cpu-used", "8", "-auto-alt-ref", "0"]
    else:
        codec = ["-c:v", "qtrle", "-pix_fmt", "argb"]
    escrita = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y",
         "-ss", f"{ini:.3f}", "-t", f"{dur:.3f}", "-i", video,
         "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{mw}x{mh}", "-framerate", str(fps), "-i", "pipe:0",
         "-filter_complex",
         f"[0:v]fps={fps},scale={largura}:{altura},format=rgba[c];"
         f"[1:v]scale={largura}:{altura}:flags=bicubic,format=gray[m];[c][m]alphamerge,format=rgba[o]",
         "-map", "[o]", "-shortest", *codec, saida],
        stdin=subprocess.PIPE)
    tam = mw * mh * 3
    anterior = None
    n = 0
    try:
        while True:
            bruto = leitura.stdout.read(tam)
            if len(bruto) < tam:
                break
            x = np.frombuffer(bruto, np.uint8).reshape(mh, mw, 3).astype(np.float32) / 127.5 - 1.0
            m = sessao.run(None, {"input": x.transpose(2, 0, 1)[None]})[0][0, 0]
            m = np.clip(m, 0, 1)
            if anterior is not None:
                m = 0.55 * m + 0.45 * anterior   # suaviza no tempo
            anterior = m
            # endurece um pouco a borda pra não ficar fantasma
            m = np.clip((m - 0.12) / 0.76, 0, 1)
            escrita.stdin.write((m * 255).astype(np.uint8).tobytes())
            n += 1
            if aviso and n % 15 == 0:
                aviso(n)
    finally:
        escrita.stdin.close()
        escrita.wait()
        leitura.stdout.close()
        leitura.wait()
    if escrita.returncode != 0 or not os.path.exists(saida):
        raise RuntimeError("não consegui recortar a pessoa nesse trecho")
    return n


def faixas_atras(plano, folga=0.08):
    """Trechos (tempo do vídeo editado) em que existe alguma camada atrás da pessoa."""
    fx = sorted([max(0.0, c["ini_out"] - folga), c["fim_out"] + folga]
                for c in plano.get("camadas", []) if c.get("atras"))
    juntas = []
    for a, b in fx:
        if juntas and a <= juntas[-1][1] + 0.3:
            juntas[-1][1] = max(juntas[-1][1], b)
        else:
            juntas.append([a, b])
    total = plano.get("duracao_saida", 0)
    return [(round(a, 3), round(min(b, total), 3)) for a, b in juntas if min(b, total) - a > 0.05]


def faixas_origem(plano, faixas):
    """Converte trechos do vídeo editado em trechos do vídeo original (pra prévia)."""
    saida = []
    for a, b in faixas:
        for s in plano["segmentos"]:
            d = s["fim"] - s["ini"]
            ia, ib = max(a, s["out"]), min(b, s["out"] + d)
            if ib - ia > 0.04:
                saida.append((round(s["ini"] + ia - s["out"], 3), round(s["ini"] + ib - s["out"], 3)))
    return saida
