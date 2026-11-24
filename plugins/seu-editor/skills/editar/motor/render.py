"""Exportação.

1. O FFmpeg monta a base: corta os trechos, enquadra em 9:16 e coloca os
   vídeos inseridos (b-roll em tela cheia ou em cartão).
2. Um navegador invisível abre app/render.html, desenha a camada de cima
   (legenda, gancho, palavras de impacto, fotos, desenhos e textos) com o
   mesmo motion.js da prévia e fotografa cada quadro com fundo transparente.
3. Os quadros entram direto no FFmpeg, que junta tudo num mp4.

Quadros iguais ao anterior não são fotografados de novo, o que deixa a
exportação bem mais rápida (a legenda só muda a cada palavra).
"""

import json
import math
import os
import re
import subprocess
import threading
import time

from . import estilos as E
from . import plano as PL
from . import projeto as P

LARGURA, ALTURA = 1080, 1920


def _tem_audio(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                          "stream=index", "-of", "csv=p=0", video], capture_output=True, text=True).stdout
    return bool(out.strip())


def _versao_ffmpeg():
    try:
        out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout
        m = re.search(r"ffmpeg version n?(\d+)", out)
        return int(m.group(1)) if m else 6
    except Exception:
        return 6


def montar_filtro(plano, proj, largura, altura, fps, com_audio, videos, idx_quadros):
    """videos: [(indice_da_entrada, camada)]; idx_quadros: entrada dos quadros transparentes."""
    segs = plano["segmentos"]
    partes, entradas = [], []
    for k, s in enumerate(segs):
        dur = s["fim"] - s["ini"]
        partes.append(f"[0:v]trim=start={s['ini']:.3f}:end={s['fim']:.3f},setpts=PTS-STARTPTS[v{k}]")
        entradas.append(f"[v{k}]")
        if com_audio:
            f = min(0.012, dur / 4)
            partes.append(
                f"[0:a]atrim=start={s['ini']:.3f}:end={s['fim']:.3f},asetpts=PTS-STARTPTS,"
                f"afade=t=in:d={f:.3f},afade=t=out:st={max(0, dur - f):.3f}:d={f:.3f}[a{k}]")
            entradas.append(f"[a{k}]")
    partes.append("".join(entradas) + f"concat=n={len(segs)}:v=1:a={1 if com_audio else 0}"
                  + ("[vc][ac]" if com_audio else "[vc]"))

    if proj.get("formato", {}).get("enquadramento") == "ajustar":
        partes.append(
            f"[vc]split[f1][f2];"
            f"[f1]scale={largura}:{altura}:force_original_aspect_ratio=increase,crop={largura}:{altura},"
            f"boxblur=40:2,eq=brightness=-0.06[fundo];"
            f"[f2]scale={largura}:{altura}:force_original_aspect_ratio=decrease[frente];"
            f"[fundo][frente]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={fps},format=yuv420p[b0]")
    else:
        partes.append(f"[vc]scale={largura}:{altura}:force_original_aspect_ratio=increase,"
                      f"crop={largura}:{altura},setsar=1,fps={fps},format=yuv420p[b0]")

    atual = "b0"
    esc = largura / LARGURA
    for n, (idx, c) in enumerate(videos):
        ini, fim = c["ini_out"], c["fim_out"]
        dur = fim - ini
        cadeia = f"[{idx}:v]trim=duration={dur:.3f},setpts=PTS-STARTPTS,fps={fps},"
        if c.get("modo") == "cartao":
            w = int(round((c.get("tamanho") or .34) * largura / 2)) * 2
            borda = max(2, int(round(14 * esc)))
            rot = float(c.get("rot") or 0) * math.pi / 180
            cadeia += (f"scale={w - 2 * borda}:-2,pad=iw+{2 * borda}:ih+{2 * borda}:{borda}:{borda}:white,"
                       f"format=rgba,rotate={rot:.4f}:c=none:ow=rotw({rot:.4f}):oh=roth({rot:.4f}),")
            pos = f"x={(c.get('x') or .5) * largura:.1f}-w/2:y={(c.get('y') or .5) * altura:.1f}-h/2"
        else:
            cadeia += f"scale={largura}:{altura}:force_original_aspect_ratio=increase,crop={largura}:{altura},format=rgba,"
            pos = "x=0:y=0"
        cadeia += (f"fade=t=in:d=0.18:alpha=1,fade=t=out:st={max(0, dur - 0.2):.3f}:d=0.2:alpha=1,"
                   f"setpts=PTS+{ini:.3f}/TB[ins{n}]")
        partes.append(cadeia)
        partes.append(f"[{atual}][ins{n}]overlay={pos}:eof_action=pass:enable='between(t,{ini:.3f},{fim:.3f})'[b{n + 1}]")
        atual = f"b{n + 1}"

    partes.append(f"[{idx_quadros}:v]format=rgba[q];[{atual}][q]overlay=0:0:format=auto:eof_action=pass,format=yuv420p[vout]")
    if com_audio:
        if proj.get("formato", {}).get("volume", True):
            partes.append("[ac]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
        else:
            partes.append("[ac]aresample=48000[aout]")
    return ";\n".join(partes)


def nome_arquivo(t):
    t = re.sub(r"[^\w\-]+", "-", t.lower()).strip("-")
    return t or "video"


def _abrir_navegador(pw):
    caminho = os.environ.get("SEU_EDITOR_CHROMIUM")
    opcoes = {"executable_path": caminho} if caminho else {}
    return pw.chromium.launch(**opcoes)


def exportar(pasta, previa=False, log=lambda *_: None):
    from playwright.sync_api import sync_playwright
    from . import servidor

    proj = P.carregar(pasta)
    plano = PL.montar_plano(proj)
    if not plano["segmentos"]:
        raise RuntimeError("nada pra exportar: todos os trechos foram cortados")

    largura, altura = (540, 960) if previa else (LARGURA, ALTURA)
    fps = min(60, max(24, round(float(proj.get("info", {}).get("fps", 30)))))
    if previa:
        fps = min(fps, 30)
    total = max(0.1, plano["duracao_saida"])
    n_quadros = int(math.ceil(total * fps))

    videos = [c for c in plano.get("camadas", []) if c.get("tipo") == "video" and c.get("arquivo")]
    com_audio = _tem_audio(proj["video"])
    entradas = ["-i", proj["video"]]
    lista_videos = []
    for k, c in enumerate(videos):
        arq = os.path.join(pasta, "insertos", c["arquivo"])
        if not os.path.exists(arq):
            continue
        entradas += ["-ss", f"{float(c.get('inicio_clip') or 0):.3f}", "-i", arq]
        lista_videos.append((len(lista_videos) + 1, c))
    idx_quadros = len(lista_videos) + 1
    entradas += ["-f", "image2pipe", "-framerate", str(fps), "-c:v", "png", "-i", "pipe:0"]

    with open(os.path.join(pasta, "filtro.txt"), "w", encoding="utf-8") as f:
        f.write(montar_filtro(plano, proj, largura, altura, fps, com_audio, lista_videos, idx_quadros))

    os.makedirs(os.path.join(pasta, "exportados"), exist_ok=True)
    if previa:
        saida = os.path.join("exportados", "previa.mp4")
    else:
        saida = os.path.join("exportados", f"{nome_arquivo(proj.get('nome', 'video'))}-{time.strftime('%Y%m%d-%H%M%S')}.mp4")

    opc_filtro = ["-/filter_complex", "filtro.txt"] if _versao_ffmpeg() >= 7 else ["-filter_complex_script", "filtro.txt"]
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostats", *entradas, *opc_filtro, "-map", "[vout]"]
    if com_audio:
        cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "128k" if previa else "192k"]
    cmd += ["-c:v", "libx264", "-r", str(fps)]
    cmd += ["-preset", "ultrafast", "-crf", "28"] if previa else ["-preset", "medium", "-crf", "18", "-profile:v", "high"]
    cmd += ["-t", f"{total:.3f}", "-movflags", "+faststart", saida]

    rotulo = "gerando a prévia" if previa else "exportando o vídeo final"
    P.escrever_estado(pasta, tarefa="exportando", progresso=0.0, mensagem=f"{rotulo}: preparando", erro=None)

    srv, url = servidor.iniciar_em_segundo_plano(pasta)
    erro_log = open(os.path.join(pasta, "ffmpeg.log"), "w", encoding="utf-8")
    proc = None
    try:
        with sync_playwright() as pw:
            nav = _abrir_navegador(pw)
            pag = nav.new_page(viewport={"width": largura, "height": altura})
            pag.goto(url + "render", wait_until="load")
            estilos = E.estilos_para_interface(P.dados_dir())
            pag.evaluate("d => preparar(d)", {"estilos": estilos, "proj": proj, "plano": plano, "largura": largura})

            proc = subprocess.Popen(cmd, cwd=pasta, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=erro_log)
            anterior, png = None, None
            ultimo_aviso = 0.0
            fotografados = 0
            for k in range(n_quadros):
                t = k / fps
                assinatura = pag.evaluate("t => quadro(t)", t)
                if assinatura != anterior or png is None:
                    png = pag.screenshot(omit_background=True, type="png")
                    anterior = assinatura
                    fotografados += 1
                try:
                    proc.stdin.write(png)
                except BrokenPipeError:
                    break
                agora = time.time()
                if agora - ultimo_aviso > 0.5:
                    prog = min(0.99, (k + 1) / n_quadros)
                    P.escrever_estado(pasta, progresso=round(prog, 3), mensagem=f"{rotulo} ({int(prog * 100)}%)")
                    ultimo_aviso = agora
            nav.close()
        proc.stdin.close()
        proc.wait()
    finally:
        srv.shutdown()
        erro_log.close()
        if proc and proc.poll() is None:
            proc.kill()

    if proc.returncode != 0:
        with open(os.path.join(pasta, "ffmpeg.log"), encoding="utf-8") as f:
            erro = f.read()[-2000:]
        P.escrever_estado(pasta, tarefa=None, mensagem="a exportação falhou", erro=erro)
        raise RuntimeError(erro)
    P.escrever_estado(pasta, tarefa=None, progresso=1.0, erro=None,
                      mensagem=("prévia pronta" if previa else "vídeo exportado"),
                      ultimo_export=saida.replace(os.sep, "/"))
    log(f"{fotografados} de {n_quadros} quadros desenhados")
    return os.path.join(pasta, saida)
