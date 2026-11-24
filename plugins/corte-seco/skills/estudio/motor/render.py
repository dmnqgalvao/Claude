"""Exportação: legenda em ASS (libass) + cortes e enquadramento no FFmpeg."""

import os
import re
import shutil
import subprocess
import time

from . import estilos as E
from . import plano as PL
from . import projeto as P

LARGURA, ALTURA = 1080, 1920
MARGEM = 90


# ---------------------------------------------------------------- ASS

def cor_ass(hex_cor, alfa=0):
    h = hex_cor.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alfa:02X}{b}{g}{r}".upper()


def cor_tag(hex_cor):
    h = hex_cor.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def tempo_ass(t):
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def escapar(t):
    return t.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ")


def linha_estilo(nome, cfg, marca):
    fonte = cfg["fonte"]
    tamanho = round(cfg["tamanho"] * E.fator_ass(fonte))
    cor = E.resolver_cor(cfg["cor"], marca)
    caixa = E.resolver_cor(cfg.get("caixa"), marca)
    if caixa:
        borda, contorno, cor_contorno, sombra = 3, cfg.get("contorno", 16), caixa, 0
    else:
        borda, contorno = 1, cfg.get("contorno", 0)
        cor_contorno = E.resolver_cor(cfg.get("cor_contorno") or "#000000", marca)
        sombra = cfg.get("sombra", 0)
    return (f"Style: {nome},{fonte},{tamanho},{cor_ass(cor)},{cor_ass(cor)},"
            f"{cor_ass(cor_contorno, 0 if caixa else cfg.get('alfa_contorno', 0))},{cor_ass('#000000', 0x70)},0,0,0,0,100,100,0,0,"
            f"{borda},{contorno},{sombra},5,{MARGEM},{MARGEM},0,1")


def gerar_ass(proj, plano):
    marca = proj.get("marca", {})
    est = plano["estilo"]
    leg, tit = est["legenda"], est["titulo"]
    linhas = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {LARGURA}", f"PlayResY: {ALTURA}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        linha_estilo("Legenda", leg, marca),
        linha_estilo("Titulo", tit, marca),
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    y_leg = round(float(proj.get("legenda", {}).get("posicao", 0.64)) * ALTURA)
    rot_leg = -float(leg.get("rotacao", 0))
    cor_base = E.resolver_cor(leg["cor"], marca)
    cor_ativa = E.resolver_cor(leg.get("cor_ativa") or leg["cor"], marca)
    cor_dest = E.resolver_cor(leg.get("cor_destaque") or leg["cor"], marca)
    caixa_base = E.resolver_cor(leg.get("caixa"), marca)
    caixa_ativa = E.resolver_cor(leg.get("caixa_ativa"), marca) or caixa_base
    caixa_dest = E.resolver_cor(leg.get("caixa_destaque"), marca) or caixa_base
    italico_dest = bool(leg.get("italico_destaque"))
    fonte = leg["fonte"]
    fonte_it = fonte + " Italic" if (fonte + " Italic") in E.FONTES else None

    def animacao(tipo):
        if tipo == "pop":
            return r"\fscx78\fscy78\t(0,110,\fscx100\fscy100)"
        if tipo == "fade":
            return r"\fad(160,0)"
        return ""

    def texto_bloco(palavras, ativa):
        partes = []
        for w in palavras:
            if w is ativa:
                cor, caixa = cor_ativa, caixa_ativa
            elif w["destaque"]:
                cor, caixa = cor_dest, caixa_dest
            else:
                cor, caixa = cor_base, caixa_base
            tags = rf"\1c{cor_tag(cor)}"
            if caixa:
                tags += rf"\3c{cor_tag(caixa)}"
            if italico_dest and fonte_it:
                tags += rf"\fn{fonte_it if w['destaque'] else fonte}"
            partes.append("{" + tags + "}" + escapar(w["t"]))
        return " ".join(partes)

    pos = rf"\an5\pos({LARGURA // 2},{y_leg})" + (rf"\frz{rot_leg:g}" if rot_leg else "")
    for b in plano["blocos"]:
        pal = b["palavras"]
        anim = animacao(leg.get("animacao"))
        if leg.get("karaoke"):
            for k, w in enumerate(pal):
                ini = b["ini_out"] if k == 0 else w["ini_out"]
                fim = pal[k + 1]["ini_out"] if k + 1 < len(pal) else b["fim_out"]
                if fim <= ini:
                    continue
                cab = "{" + pos + (anim if k == 0 else "") + "}"
                linhas.append(f"Dialogue: 1,{tempo_ass(ini)},{tempo_ass(fim)},Legenda,,0,0,0,,{cab}{texto_bloco(pal, w)}")
        else:
            cab = "{" + pos + anim + "}"
            linhas.append(f"Dialogue: 1,{tempo_ass(b['ini_out'])},{tempo_ass(b['fim_out'])},Legenda,,0,0,0,,{cab}{texto_bloco(pal, None)}")

    def titulo(texto, ini, fim, y):
        t = texto.upper() if tit.get("caixa_alta") else texto
        rot = -float(tit.get("rotacao", 0))
        if tit.get("animacao") == "pop":
            anim = r"\fad(0,160)\fscx70\fscy70\t(0,140,\fscx100\fscy100)"
        else:
            anim = r"\fad(220,180)"
        cab = "{" + rf"\an5\pos({LARGURA // 2},{round(y * ALTURA)})" + (rf"\frz{rot:g}" if rot else "") + anim + "}"
        # quebra manual com "/" ou "|" vira nova linha
        t = escapar(re.sub(r"\s*[|]\s*", "\n", t)).replace(" \n", "\n")
        t = t.replace("\n", r"\N") if "\n" in t else t
        linhas.append(f"Dialogue: 2,{tempo_ass(ini)},{tempo_ass(fim)},Titulo,,0,0,0,,{cab}{t}")

    if plano.get("gancho"):
        g = plano["gancho"]
        titulo(g["texto"], g["ini_out"], g["fim_out"], g["posicao"])
    for t in plano.get("titulos", []):
        titulo(t["texto"], t["ini_out"], t["fim_out"], 0.20)

    return "\n".join(linhas) + "\n"


# ---------------------------------------------------------------- FFmpeg

def _versao_ffmpeg():
    try:
        out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout
        m = re.search(r"ffmpeg version n?(\d+)", out)
        return int(m.group(1)) if m else 6
    except Exception:
        return 6


def _tem_audio(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                          "stream=index", "-of", "csv=p=0", video], capture_output=True, text=True).stdout
    return bool(out.strip())


def montar_filtro(plano, proj, largura, altura, com_audio):
    segs = plano["segmentos"]
    partes = []
    entradas = []
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
    n = len(segs)
    partes.append("".join(entradas) + f"concat=n={n}:v=1:a={1 if com_audio else 0}" + ("[vc][ac]" if com_audio else "[vc]"))

    fps = min(60, max(24, round(float(proj.get("info", {}).get("fps", 30)))))
    enq = proj.get("formato", {}).get("enquadramento", "preencher")
    if enq == "ajustar":
        partes.append(
            f"[vc]split[f1][f2];"
            f"[f1]scale={largura}:{altura}:force_original_aspect_ratio=increase,crop={largura}:{altura},"
            f"boxblur=40:2,eq=brightness=-0.06[fundo];"
            f"[f2]scale={largura}:{altura}:force_original_aspect_ratio=decrease[frente];"
            f"[fundo][frente]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={fps},format=yuv420p[vq]")
    else:
        partes.append(
            f"[vc]scale={largura}:{altura}:force_original_aspect_ratio=increase,"
            f"crop={largura}:{altura},setsar=1,fps={fps},format=yuv420p[vq]")
    partes.append("[vq]ass=legenda.ass:fontsdir=_fontes[vout]")
    if com_audio:
        if proj.get("formato", {}).get("volume", True):
            partes.append("[ac]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
        else:
            partes.append("[ac]aresample=48000[aout]")
    return ";\n".join(partes)


def nome_arquivo(t):
    t = re.sub(r"[^\w\-]+", "-", t.lower()).strip("-")
    return t or "video"


def exportar(pasta, previa=False, log=lambda *_: None):
    proj = P.carregar(pasta)
    plano = PL.montar_plano(proj)
    if not plano["segmentos"]:
        raise RuntimeError("nada pra exportar: todos os trechos foram cortados")

    largura, altura = (540, 960) if previa else (LARGURA, ALTURA)
    with open(os.path.join(pasta, "legenda.ass"), "w", encoding="utf-8") as f:
        f.write(gerar_ass(proj, plano))

    pasta_fontes = os.path.join(pasta, "_fontes")
    os.makedirs(pasta_fontes, exist_ok=True)
    for arq in set(E.FONTES.values()):
        destino = os.path.join(pasta_fontes, arq)
        if not os.path.exists(destino):
            shutil.copy(os.path.join(E.PASTA_FONTES, arq), destino)

    com_audio = _tem_audio(proj["video"])
    with open(os.path.join(pasta, "filtro.txt"), "w", encoding="utf-8") as f:
        f.write(montar_filtro(plano, proj, largura, altura, com_audio))

    os.makedirs(os.path.join(pasta, "exportados"), exist_ok=True)
    if previa:
        saida = os.path.join("exportados", "previa.mp4")
    else:
        saida = os.path.join("exportados", f"{nome_arquivo(proj.get('nome', 'video'))}-{time.strftime('%Y%m%d-%H%M%S')}.mp4")

    opc_filtro = ["-/filter_complex", "filtro.txt"] if _versao_ffmpeg() >= 7 else ["-filter_complex_script", "filtro.txt"]
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostats", "-progress", "pipe:1",
           "-i", proj["video"], *opc_filtro, "-map", "[vout]"]
    if com_audio:
        cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k" if not previa else "128k"]
    if previa:
        cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"]
    else:
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high"]
    cmd += ["-movflags", "+faststart", saida]

    total = max(0.1, plano["duracao_saida"])
    rotulo = "gerando a prévia" if previa else "exportando o vídeo final"
    P.escrever_estado(pasta, tarefa="exportando", progresso=0.0, mensagem=rotulo)
    proc = subprocess.Popen(cmd, cwd=pasta, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ultimo = 0.0
    for linha in proc.stdout:
        if linha.startswith("out_time_us=") or linha.startswith("out_time_ms="):
            try:
                t = int(linha.split("=")[1]) / 1_000_000
            except ValueError:
                continue
            agora = time.time()
            if agora - ultimo > 0.4:
                prog = min(0.99, t / total)
                P.escrever_estado(pasta, progresso=round(prog, 3), mensagem=f"{rotulo} ({int(prog * 100)}%)")
                ultimo = agora
    erro = proc.stderr.read()
    proc.wait()
    if proc.returncode != 0:
        P.escrever_estado(pasta, tarefa=None, mensagem="a exportação falhou", erro=erro[-2000:])
        raise RuntimeError(erro[-2000:])
    P.escrever_estado(pasta, tarefa=None, progresso=1.0, erro=None,
                      mensagem=("prévia pronta" if previa else "vídeo exportado"),
                      ultimo_export=saida.replace(os.sep, "/"))
    log(os.path.join(pasta, saida))
    return os.path.join(pasta, saida)
