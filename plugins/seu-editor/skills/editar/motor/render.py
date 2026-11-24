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
import shutil
import subprocess
import threading
import time

from . import estilos as E
from . import plano as PL
from . import projeto as P
from . import recorte as R

LARGURA, ALTURA = 1080, 1920
PASTA_SONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sons")


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


def _expr_efeitos(camadas, largura, altura):
    """Zoom rápido e tremida viram expressões de tempo pro scale/crop do FFmpeg.
    A prévia (app.js, efeitoBase) usa as mesmas contas."""
    termos_z, termos_x, termos_y, termos_sx, termos_sy = [], [], [], [], []
    for c in camadas:
        if c.get("tipo") != "efeito" or c.get("efeito") not in ("zoom", "tremida"):
            continue
        a, b = c["ini_out"], c["fim_out"]
        d = 0.001 if c.get("seco", c.get("efeito") == "zoom" and c.get("estilo") == "seco") else 0.14
        r = f"clip(min((t-{a:.3f})/{d},({b:.3f}-t)/{d}),0,1)"
        if c["efeito"] == "zoom":
            k = float(c.get("intensidade", 1.18))
            termos_z.append(f"{k - 1:.4f}*{r}")
            termos_x.append(f"{float(c.get('x', .5)) - .5:.4f}*{r}")
            termos_y.append(f"{float(c.get('y', .45)) - .5:.4f}*{r}")
        else:
            amp = float(c.get("intensidade", 1.0)) * 0.012
            termos_z.append(f"0.05*{r}")
            termos_sx.append(f"{amp:.4f}*{r}*sin(t*71)")
            termos_sy.append(f"{amp:.4f}*{r}*cos(t*59)")
    if not termos_z:
        return ""
    z = "1+" + "+".join(termos_z)
    fx = "0.5" + "".join("+" + t for t in termos_x)
    fy = "0.5" + "".join("+" + t for t in termos_y)
    sx = "+".join(termos_sx) or "0"
    sy = "+".join(termos_sy) or "0"
    return (f"scale=w='2*ceil({largura}*({z})/2)':h='2*ceil({altura}*({z})/2)':eval=frame,"
            f"crop={largura}:{altura}:x='clip((iw-{largura})*({fx})+({sx})*{largura},0,iw-{largura})'"
            f":y='clip((ih-{altura})*({fy})+({sy})*{altura},0,ih-{altura})',")


def _filtro_cor(cor):
    if not cor or cor.get("neutra"):
        return ""
    def pts(v):
        n = len(v) - 1
        return " ".join(f"{k / n:.4f}/{y:.4f}" for k, y in enumerate(v))
    sat = f"eq=saturation={cor['saturacao']:.4f}," if abs(cor.get("saturacao", 1) - 1) > 1e-3 else ""
    return f"curves=r='{pts(cor['r'])}':g='{pts(cor['g'])}':b='{pts(cor['b'])}',{sat}"


def montar_filtro(plano, proj, largura, altura, fps, com_audio, videos, idx_quadros, sons=(), trilha_idx=None,
                  base_idx=None, atras_seqs=(), recortes=(), so_base=False):
    """videos: [(entrada, camada)]; sons: [(entrada, evento)]; idx_quadros: entrada dos quadros transparentes.
    base_idx: entrada com a base já cortada e enquadrada (quando há camadas atrás da pessoa).
    atras_seqs / recortes: [(entrada, ini, fim)] com as camadas de trás e a pessoa recortada."""
    segs = plano["segmentos"]
    info = proj.get("info", {})
    sw, sh = int(info.get("largura", 1080)) // 2 * 2, int(info.get("altura", 1920)) // 2 * 2
    partes, entradas = [], []
    for k, s in enumerate(segs):
        dur = s["fim"] - s["ini"]
        vel = float(s.get("vel", 1.0))
        if base_idx is None:
            z = float(s.get("zoom", 1.0))
            zoom = (f",crop=w=iw/{z:.4f}:h=ih/{z:.4f}:x=(iw-iw/{z:.4f})/2:y=(ih-ih/{z:.4f})*0.42,scale={sw}:{sh}"
                    if z > 1.001 else "")
            velo = f",setpts=PTS/{vel:.4f}" if abs(vel - 1) > 1e-3 else ""
            partes.append(f"[0:v]trim=start={s['ini']:.3f}:end={s['fim']:.3f},setpts=PTS-STARTPTS{zoom}{velo}[v{k}]")
            entradas.append(f"[v{k}]")
        if com_audio:
            f = min(0.012, dur / 4)
            tempo = f",atempo={vel:.4f}" if abs(vel - 1) > 1e-3 else ""
            partes.append(
                f"[0:a]atrim=start={s['ini']:.3f}:end={s['fim']:.3f},asetpts=PTS-STARTPTS,"
                f"afade=t=in:d={f:.3f},afade=t=out:st={max(0, dur - f):.3f}:d={f:.3f}{tempo}[a{k}]")
            entradas.append(f"[a{k}]")
    if base_idx is not None:
        if com_audio:
            partes.append("".join(entradas) + f"concat=n={len(segs)}:v=0:a=1[ac]")
        partes.append(f"[{base_idx}:v]setpts=PTS-STARTPTS,fps={fps},format=yuv420p[b0]")
    else:
        partes.append("".join(entradas) + f"concat=n={len(segs)}:v=1:a={1 if com_audio else 0}"
                      + ("[vc][ac]" if com_audio else "[vc]"))
    if base_idx is not None:
        pass
    elif proj.get("formato", {}).get("enquadramento") == "ajustar":
        partes.append(
            f"[vc]split[f1][f2];"
            f"[f1]scale={largura}:{altura}:force_original_aspect_ratio=increase,crop={largura}:{altura},"
            f"boxblur=40:2,eq=brightness=-0.06[fundo];"
            f"[f2]scale={largura}:{altura}:force_original_aspect_ratio=decrease[frente];"
            f"[fundo][frente]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={fps}[vb]")
    else:
        partes.append(f"[vc]scale={largura}:{altura}:force_original_aspect_ratio=increase,"
                      f"crop={largura}:{altura},setsar=1,fps={fps}[vb]")
    if base_idx is None:
        cor = plano.get("cor") or {}
        nitidez = f"unsharp=5:5:{cor['nitidez']:.2f}:5:5:0," if cor.get("nitidez") else ""
        pb = "".join(f"hue=s=0:enable='between(t,{c['ini_out']:.3f},{c['fim_out']:.3f})',"
                     for c in plano.get("camadas", []) if c.get("tipo") == "efeito" and c.get("efeito") == "pb")
        partes.append(f"[vb]{_filtro_cor(cor)}{nitidez}{pb}{_expr_efeitos(plano.get('camadas', []), largura, altura)}"
                      f"setsar=1,format=yuv420p[b0]")
    if so_base:
        return ";\n".join(partes)

    atual = "b0"
    esc = largura / LARGURA
    passo = [0]

    def sobrepor(rotulo, ini, fim, pos="x=0:y=0"):
        nonlocal atual
        passo[0] += 1
        novo = f"c{passo[0]}"
        partes.append(f"[{atual}][{rotulo}]overlay={pos}:eof_action=pass:enable='between(t,{ini:.3f},{fim:.3f})'[{novo}]")
        atual = novo

    for n, (idx, ini, fim) in enumerate(atras_seqs):
        partes.append(f"[{idx}:v]format=rgba,setpts=PTS-STARTPTS+{ini:.3f}/TB[at{n}]")
        sobrepor(f"at{n}", ini, fim)
    ordem = [(i, c) for i, c in videos if c.get("atras")] + [None] + [(i, c) for i, c in videos if not c.get("atras")]
    for item in ordem:
        if item is None:
            for n, (idx, ini, fim) in enumerate(recortes):
                partes.append(f"[{idx}:v]format=rgba,setpts=PTS-STARTPTS+{ini:.3f}/TB[rc{n}]")
                sobrepor(f"rc{n}", ini, fim)
            continue
        n, (idx, c) = passo[0], item
        ini, fim = c["ini_out"], c["fim_out"]
        dur = fim - ini
        cadeia = f"[{idx}:v]trim=duration={dur:.3f},setpts=PTS-STARTPTS,fps={fps},"
        if c.get("modo") == "metade":
            alt = int(round(altura * 0.54 / 2)) * 2
            esf = int(altura * 0.08)
            embaixo = c.get("lado") == "baixo"
            rampa = f"255*min(1,Y/{esf})" if embaixo else f"255*min(1,({alt}-Y)/{esf})"
            partes.append(f"color=c=black:s={largura}x{alt}:r={fps}:d={dur:.3f},format=gray,geq=lum='{rampa}'[mk{n}]")
            cadeia += f"scale={largura}:{alt}:force_original_aspect_ratio=increase,crop={largura}:{alt},format=rgba[iv{n}];[iv{n}][mk{n}]alphamerge,"
            pos = f"x=0:y={altura - alt if embaixo else 0}"
        elif c.get("modo") == "cartao":
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
        sobrepor(f"ins{n}", ini, fim, pos)

    partes.append(f"[{idx_quadros}:v]format=rgba[q];[{atual}][q]overlay=0:0:format=auto:eof_action=pass,format=yuv420p[vout]")

    # áudio: voz nivelada + efeitos sonoros + trilha que abaixa quando tem fala
    total = plano["duracao_saida"]
    if com_audio:
        nivel = "loudnorm=I=-14:TP=-1.5:LRA=11," if proj.get("formato", {}).get("volume", True) else ""
        partes.append(f"[ac]{nivel}aresample=48000,aformat=channel_layouts=stereo[voz]")
    else:
        partes.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={total:.3f}[voz]")
    mistura = []
    if trilha_idx is not None:
        tr = plano.get("trilha") or {}
        vol = float(tr.get("volume", 0.14))
        partes.append(f"[{trilha_idx}:a]atrim=duration={total:.3f},asetpts=PTS-STARTPTS,aresample=48000,"
                      f"aformat=channel_layouts=stereo,volume={vol:.3f},"
                      f"afade=t=out:st={max(0, total - 1.5):.3f}:d=1.5[tr0]")
        if tr.get("abaixar_na_fala", True) and com_audio:
            partes.append("[voz]asplit[voz][vozc];[tr0][vozc]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[tr]")
        else:
            partes.append("[tr0]anull[tr]")
        mistura.append("[tr]")
    for n, (idx, ev) in enumerate(sons):
        atraso = int(round(ev["ini_out"] * 1000))
        partes.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,"
                      f"adelay={atraso}|{atraso},volume={float(ev.get('volume', .8)):.3f}[s{n}]")
        mistura.append(f"[s{n}]")
    if mistura:
        partes.append(f"[voz]{''.join(mistura)}amix=inputs={1 + len(mistura)}:duration=first:normalize=0,"
                      f"alimiter=limit=0.95[aout]")
    else:
        partes.append("[voz]anull[aout]")
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
    rotulo = "gerando a prévia" if previa else "exportando o vídeo final"
    P.escrever_estado(pasta, tarefa="exportando", progresso=0.0, mensagem=f"{rotulo}: preparando", erro=None)
    opc_filtro = (lambda arq: ["-/filter_complex", arq]) if _versao_ffmpeg() >= 7 else (lambda arq: ["-filter_complex_script", arq])

    # camadas atrás da pessoa: monta a base primeiro, recorta a pessoa nela
    faixas = R.faixas_atras(plano)
    tmp = os.path.join(pasta, "_render")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    arq_recortes = []
    if faixas:
        P.escrever_estado(pasta, mensagem=f"{rotulo}: montando a base pra recortar a pessoa")
        with open(os.path.join(tmp, "base.txt"), "w", encoding="utf-8") as f:
            f.write(montar_filtro(plano, proj, largura, altura, fps, False, [], 0, so_base=True))
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", proj["video"], *opc_filtro("_render/base.txt"),
                            "-map", "[b0]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-r", str(fps),
                            "_render/base.mp4"], cwd=pasta, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-1500:])
        for k, (a_, b_) in enumerate(faixas):
            P.escrever_estado(pasta, mensagem=f"{rotulo}: recortando a pessoa ({k + 1} de {len(faixas)})")
            saida_rc = os.path.join(tmp, f"recorte{k}.mov")
            R.recortar(os.path.join(tmp, "base.mp4"), a_, b_ - a_, largura, altura, fps, saida_rc)
            arq_recortes.append((saida_rc, a_, b_))

    entradas = ["-i", proj["video"]]
    proximo = 1
    base_idx = None
    if faixas:
        entradas += ["-i", os.path.join(tmp, "base.mp4")]
        base_idx = proximo
        proximo += 1
    lista_videos = []
    for k, c in enumerate(videos):
        arq = os.path.join(pasta, "insertos", c["arquivo"])
        if not os.path.exists(arq):
            continue
        entradas += ["-ss", f"{float(c.get('inicio_clip') or 0):.3f}", "-i", arq]
        lista_videos.append((proximo, c))
        proximo += 1
    lista_recortes = []
    for arq, a_, b_ in arq_recortes:
        entradas += ["-i", arq]
        lista_recortes.append((proximo, a_, b_))
        proximo += 1
    lista_atras = []
    for k, (a_, b_) in enumerate(faixas):
        os.makedirs(os.path.join(tmp, f"atras{k}"))
        entradas += ["-framerate", str(fps), "-i", os.path.join(tmp, f"atras{k}", "%05d.png")]
        lista_atras.append((proximo, a_, b_))
        proximo += 1
    lista_sons = []
    for ev in plano.get("sons", []):
        arq = os.path.join(PASTA_SONS, f"{ev['som']}.wav")
        if not os.path.exists(arq):
            arq = os.path.join(pasta, "insertos", ev["som"])
        if os.path.exists(arq) and ev["ini_out"] < total:
            entradas += ["-i", arq]
            lista_sons.append((proximo, ev))
            proximo += 1
    trilha_idx = None
    tr = plano.get("trilha")
    if tr and os.path.exists(os.path.join(pasta, "insertos", tr["arquivo"])):
        entradas += ["-stream_loop", "-1", "-i", os.path.join(pasta, "insertos", tr["arquivo"])]
        trilha_idx = proximo
        proximo += 1
    idx_quadros = proximo
    entradas += ["-f", "image2pipe", "-framerate", str(fps), "-c:v", "png", "-i", "pipe:0"]

    with open(os.path.join(pasta, "filtro.txt"), "w", encoding="utf-8") as f:
        f.write(montar_filtro(plano, proj, largura, altura, fps, com_audio, lista_videos, idx_quadros,
                              lista_sons, trilha_idx, base_idx=base_idx, atras_seqs=lista_atras,
                              recortes=lista_recortes))

    os.makedirs(os.path.join(pasta, "exportados"), exist_ok=True)
    if previa:
        saida = os.path.join("exportados", "previa.mp4")
    else:
        saida = os.path.join("exportados", f"{nome_arquivo(proj.get('nome', 'video'))}-{time.strftime('%Y%m%d-%H%M%S')}.mp4")

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostats", *entradas, *opc_filtro("filtro.txt"), "-map", "[vout]"]
    cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "128k" if previa else "192k"]
    cmd += ["-c:v", "libx264", "-r", str(fps)]
    cmd += ["-preset", "ultrafast", "-crf", "28"] if previa else ["-preset", "medium", "-crf", "18", "-profile:v", "high"]
    cmd += ["-t", f"{total:.3f}", "-movflags", "+faststart", saida]

    srv, url = servidor.iniciar_em_segundo_plano(pasta)
    erro_log = open(os.path.join(pasta, "ffmpeg.log"), "w", encoding="utf-8")
    proc = None
    try:
        with sync_playwright() as pw:
            nav = _abrir_navegador(pw)
            pag = nav.new_page(viewport={"width": largura, "height": altura})
            pag.goto(url + "render", wait_until="load")
            estilos = E.estilos_para_interface(P.dados_dir())
            if faixas:
                # camadas de trás: viram sequências de PNG, uma por trecho
                atr = nav.new_page(viewport={"width": largura, "height": altura})
                atr.goto(url + "render", wait_until="load")
                atr.evaluate("d => preparar(d)", {"estilos": estilos, "proj": proj, "plano": plano,
                                                  "largura": largura, "camada": "atras"})
                for k, (a_, b_) in enumerate(faixas):
                    ant, img = None, None
                    for q in range(int(math.ceil((b_ - a_) * fps)) + 1):
                        assinatura = atr.evaluate("t => quadro(t)", a_ + q / fps)
                        if assinatura != ant or img is None:
                            img = atr.screenshot(omit_background=True, type="png")
                            ant = assinatura
                        with open(os.path.join(tmp, f"atras{k}", f"{q + 1:05d}.png"), "wb") as f:
                            f.write(img)
                atr.close()
            pag.evaluate("d => preparar(d)", {"estilos": estilos, "proj": proj, "plano": plano, "largura": largura,
                                              "camada": "frente" if faixas else None})

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
    shutil.rmtree(tmp, ignore_errors=True)
    P.escrever_estado(pasta, tarefa=None, progresso=1.0, erro=None,
                      mensagem=("prévia pronta" if previa else "vídeo exportado"),
                      ultimo_export=saida.replace(os.sep, "/"))
    log(f"{fotografados} de {n_quadros} quadros desenhados")
    return os.path.join(pasta, saida)
