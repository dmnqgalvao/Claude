"""Leitura e gravação do projeto (projeto.json) e do estado (estado.json).

Um projeto é uma pasta com:
  projeto.json   tudo que a pessoa e o Claude decidiram (cortes, textos, estilo)
  estado.json    o que está acontecendo agora (transcrevendo, exportando...)
  insertos/      fotos e vídeos que entram por cima da fala
  exportados/    os vídeos prontos
"""

import json
import os
import subprocess
import tempfile
import time

from . import estilos as E

RITMOS = {
    "seco": {"pausa_max": 0.14, "folga": 0.05},
    "calmo": {"pausa_max": 0.70, "folga": 0.16},
    "natural": {"pausa_max": 0.40, "folga": 0.10},
    "acelerado": {"pausa_max": 0.18, "folga": 0.06},
}


EXT_VIDEO = (".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv", ".mts")
EXT_AUDIO = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".flac")


def sondar(caminho):
    """Tamanho, fps, duração, se tem vídeo, se tem áudio e se é HDR."""
    info = {"largura": 1080, "altura": 1920, "fps": 30.0, "duracao": 0.0,
            "tem_video": False, "tem_audio": False, "hdr": False}
    try:
        d = json.loads(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type,width,height,avg_frame_rate,color_transfer:stream_tags=rotate:"
             "stream_side_data=rotation:format=duration", "-of", "json", caminho],
            capture_output=True, text=True, check=True).stdout)
    except Exception:
        return info
    info["duracao"] = float(d.get("format", {}).get("duration") or 0)
    for s in d.get("streams", []):
        if s.get("codec_type") == "audio":
            info["tem_audio"] = True
        if s.get("codec_type") == "video" and not info["tem_video"] and s.get("width"):
            w, h = int(s["width"]), int(s["height"])
            rot = 0
            for sd in s.get("side_data_list", []) or []:
                if "rotation" in sd:
                    rot = int(sd["rotation"])
            if "tags" in s and "rotate" in s["tags"]:
                rot = int(s["tags"]["rotate"])
            if abs(rot) in (90, 270):
                w, h = h, w
            num, den = (s.get("avg_frame_rate") or "30/1").split("/")
            fps = float(num) / float(den) if float(den) else 30.0
            if fps <= 0 or fps > 120:
                fps = 30.0
            info.update(largura=w, altura=h, fps=round(fps, 3), tem_video=True,
                        hdr=s.get("color_transfer") in ("arib-std-b67", "smpte2084"))
    return info


def montar_arquivos(caminhos):
    """Arquivos um depois do outro numa linha do tempo única (tempo "virtual")."""
    arquivos, t = [], 0.0
    for k, c in enumerate(caminhos):
        info = sondar(c)
        if info["duracao"] <= 0.05:
            continue
        arquivos.append({"id": f"a{k + 1}", "arquivo": os.path.abspath(c), "nome": os.path.basename(c),
                         "tipo": "video" if info["tem_video"] else "audio", "info": info,
                         "ini": round(t, 3), "fim": round(t + info["duracao"], 3),
                         "modo": "fala", "manter": None})
        t += info["duracao"]
    return arquivos


def info_do_projeto(arquivos):
    video = next((a for a in arquivos if a["tipo"] == "video"), None)
    base = dict(video["info"]) if video else {"largura": 1080, "altura": 1920, "fps": 30.0}
    base["duracao"] = round(arquivos[-1]["fim"], 3) if arquivos else 0.0
    return {k: base[k] for k in ("largura", "altura", "fps", "duracao")}


def midia_previa(proj):
    """O arquivo que a interface toca e que a transcrição ouve: o proxy, quando há vários arquivos."""
    if proj.get("proxy") and os.path.exists(proj["proxy"]):
        return proj["proxy"]
    return proj["video"]


def precisa_proxy(proj):
    arqs = proj.get("arquivos") or []
    return len(arqs) > 1 or any(a["tipo"] == "audio" for a in arqs)


PROXY_FORMATO = 2


def gerar_proxy(pasta, proj, aviso=lambda *_: None):
    """Junta todos os arquivos num vídeo leve na linha do tempo do projeto.
    Cada arquivo entra inteiro (sem cortar as laterais), centralizado numa tela fixa, pra
    prévia poder enquadrar igual à exportação. Onde cada um ficou vai em proxy_caixas."""
    arqs = proj["arquivos"]
    destino = os.path.join(pasta, "_previa")
    os.makedirs(destino, exist_ok=True)
    saida = os.path.join(destino, "proxy.mp4")
    def proporcao(a):
        i = a.get("info") or {}
        return float(i.get("largura") or 9) / float(i.get("altura") or 16)
    em_pe = all(proporcao(a) <= 0.6 for a in arqs if a["tipo"] == "video")
    cw, ch = (540, 960) if em_pe else (960, 960)
    entradas, partes, rotulos, caixas = [], [], [], {}
    zscale = " zscale " in subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    for k, a in enumerate(arqs):
        entradas += ["-i", a["arquivo"]]
        dur = a["fim"] - a["ini"]
        if a["tipo"] == "video":
            hdr = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
                   "zscale=t=bt709:m=bt709:r=tv,") if a["info"].get("hdr") and zscale else ""
            r = proporcao(a)
            w, h = (cw, cw / r) if r > cw / ch else (ch * r, ch)
            w, h = max(2, int(round(w / 2)) * 2), max(2, int(round(h / 2)) * 2)
            x, y = (cw - w) // 2, (ch - h) // 2
            caixas[a["id"]] = [round(x / cw, 5), round(y / ch, 5), round(w / cw, 5), round(h / ch, 5)]
            partes.append(f"[{k}:v]{hdr}scale={w}:{h},pad={cw}:{ch}:{x}:{y}:black,"
                          f"fps=30,format=yuv420p,setsar=1,trim=duration={dur:.3f},setpts=PTS-STARTPTS[v{k}]")
        else:
            partes.append(f"color=c=black:s={cw}x{ch}:r=30:d={dur:.3f},format=yuv420p,setsar=1[v{k}]")
        if a["info"].get("tem_audio"):
            partes.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={dur:.3f},"
                          f"atrim=duration={dur:.3f},asetpts=PTS-STARTPTS[a{k}]")
        else:
            partes.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={dur:.3f}[a{k}]")
        rotulos.append(f"[v{k}][a{k}]")
    partes.append("".join(rotulos) + f"concat=n={len(arqs)}:v=1:a=1[v][a]")
    aviso("juntando os arquivos pra prévia")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *entradas, "-filter_complex", ";".join(partes),
                        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-g", "30",
                        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", saida], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("não consegui juntar os arquivos: " + r.stderr[-800:])
    proj["proxy"] = saida
    proj["proxy_caixas"] = caixas
    proj["proxy_formato"] = PROXY_FORMATO
    return saida


def proxy_desatualizado(proj):
    return precisa_proxy(proj) and (not proj.get("proxy") or not os.path.exists(proj["proxy"])
                                    or proj.get("proxy_formato") != PROXY_FORMATO)


def retangulo_arquivo(arquivo, ajustar, q):
    """Onde o quadro inteiro do arquivo fica na tela 1080x1920, em fração da tela
    (x, y, largura, altura). Mesma conta da prévia (app.js) e da exportação."""
    inf = (arquivo or {}).get("info") or {}
    W, H = float(inf.get("largura") or 1080), float(inf.get("altura") or 1920)
    z = q["zoom"] if ajustar else max(1.0, q["zoom"])
    base = min(1080 / W, 1920 / H) if ajustar else max(1080 / W, 1920 / H)
    dw, dh = W * base * z / 1080, H * base * z / 1920
    return (1 - dw) * q["x"], (1 - dh) * q["y"], dw, dh


ALVO_ROSTO = (0.5, 0.4)   # onde os olhos ficam na tela: centro, um pouco acima do meio


def quadro_de(arquivo, ajustar=False):
    """Enquadramento de um arquivo: zoom (1 = cabe certinho) e qual parte aparece
    (x e y de 0 a 1; 0,5 é o centro). Sem ajuste manual, centraliza o rosto quando
    sobra imagem pros lados (vídeo deitado, por exemplo)."""
    q = (arquivo or {}).get("quadro")
    if q:
        return {"zoom": max(0.5, min(4.0, float(q.get("zoom", 1.0)))),
                "x": max(0.0, min(1.0, float(q.get("x", 0.5)))),
                "y": max(0.0, min(1.0, float(q.get("y", 0.5))))}
    q = {"zoom": 1.0, "x": 0.5, "y": 0.5}
    r = (arquivo or {}).get("rosto")
    if r and not ajustar:
        _, _, dw, dh = retangulo_arquivo(arquivo, False, q)
        if dw > 1.001:
            q["x"] = max(0.0, min(1.0, (ALVO_ROSTO[0] - r["x"] * dw) / (1 - dw)))
        if dh > 1.001:
            q["y"] = max(0.0, min(1.0, (ALVO_ROSTO[1] - r["y"] * dh) / (1 - dh)))
    return q


def rosto_na_tela(arquivo, ajustar=False):
    """Posição dos olhos na tela editada (fração), ou None."""
    r = (arquivo or {}).get("rosto")
    if not r:
        return None
    x, y, w, h = retangulo_arquivo(arquivo, ajustar, quadro_de(arquivo, ajustar))
    return x + r["x"] * w, y + r["y"] * h


def projeto_padrao(video, nome, marca=None):
    """video: um caminho ou uma lista de caminhos (takes, clipes de vlog, narração)."""
    marca = marca or {}
    ritmo = marca.get("ritmo") if marca.get("ritmo") in RITMOS else "seco"
    caminhos = video if isinstance(video, (list, tuple)) else [video]
    arquivos = montar_arquivos(caminhos)
    return normalizar({
        "versao": 3,
        "nome": nome,
        "video": arquivos[0]["arquivo"] if arquivos else os.path.abspath(caminhos[0]),
        "arquivos": arquivos,
        "info": info_do_projeto(arquivos),
        "palavras": [],
        "ajustes": {"ritmo": ritmo, "cortar_pausas": True, **RITMOS[ritmo],
                    "velocidade": 1.0,
                    "zoom_cortes": {"ativo": True, "intensidade": 1.3, "frequencia": 0.35},
                    "sons_auto": True},
        "legenda": {
            "ativa": True,
            "posicao": 0.70,           # altura do centro da legenda (0 = topo, 1 = base)
            "sem_pontuacao": True,
            "visual": dict(E.LEGENDA_PADRAO, **(marca.get("legenda") or {})),
        },
        "gancho": {"ativo": False, "texto": "", "duracao": 5.5, "posicao": 0.24,
                   "visual": dict(E.GANCHO_PADRAO, **(marca.get("gancho") or {}))},
        "camadas": [],                 # palavras de impacto, insertos, desenhos e textos fixos
        "sugestoes": {"ganchos": []},
        "marca": {"cores": marca.get("cores") or list(E.PALETA_PADRAO)},
        "fontes": dict(marca.get("fontes") or {"kit": E.KIT_PADRAO["id"], "destaque": E.KIT_PADRAO["destaque"],
                                              "texto": E.KIT_PADRAO["texto"]}),
        "formato": {"enquadramento": "preencher", "volume": True},
        "cor": {"auto": False, "ganhos": [1.0, 1.0, 1.0], "look": "quente-suave", "intensidade": 1.0, "brilho": 0.0,
                "contraste": 1.0, "saturacao": 1.0, "temperatura": 0.0, "nitidez": 0.4},
        "termos": marca.get("termos", []),
    })


def normalizar(proj):
    """Completa campos que faltam (projetos de versões anteriores)."""
    leg = proj.setdefault("legenda", {})
    vis = dict(E.LEGENDA_PADRAO)
    vis.update(leg.get("visual") or {})
    if leg.get("palavras"):
        vis["palavras"] = leg["palavras"]
    leg["visual"] = vis
    leg.setdefault("ativa", True)
    leg.setdefault("posicao", 0.64)
    leg.setdefault("sem_pontuacao", True)
    for velho in ("estilo", "palavras", "caixa_alta"):
        leg.pop(velho, None)
    g = proj.setdefault("gancho", {"ativo": False, "texto": "", "duracao": 3.0, "posicao": 0.2})
    gv = dict(E.GANCHO_PADRAO)
    gv.update(g.get("visual") or {})
    g["visual"] = gv
    marca = proj.setdefault("marca", {})
    if "cores" not in marca:
        marca["cores"] = list(E.PALETA_PADRAO)
    for velho in ("texto", "destaque"):
        marca.pop(velho, None)
    proj.setdefault("fontes", {"kit": E.KIT_PADRAO["id"], "destaque": E.KIT_PADRAO["destaque"],
                               "texto": E.KIT_PADRAO["texto"]})
    proj.setdefault("camadas", [])
    proj.setdefault("cortes_tempo", [])
    cor = proj.get("cor") or {}
    if "look" not in cor:
        # projetos antigos: o filtro vira look, e os valores do filtro antigo saem dos ajustes
        velho = cor.get("filtro", "nenhum")
        cor["look"] = {"quente": "dourado", "quente_nitido": "dourado", "vivo": "verao"}.get(velho, velho)
        if cor["look"] not in ("nenhum", "natural", "dourado", "pessego", "verao", "frio", "cinema", "filme", "suave", "pb"):  # noqa
            cor["look"] = "nenhum"
        if velho != "personalizado":
            cor.update(brilho=0.0, contraste=1.0, saturacao=1.0, temperatura=0.0)
        cor.setdefault("intensidade", 1.0)
        proj["cor"] = cor
    aj = proj.setdefault("ajustes", {})
    aj.setdefault("velocidade", 1.0)
    aj.setdefault("zoom_cortes", {"ativo": False, "intensidade": 1.3, "frequencia": 0.35})
    aj.setdefault("sons_auto", False)
    proj.setdefault("cor", {"auto": False, "ganhos": [1.0, 1.0, 1.0], "filtro": "nenhum", "brilho": 0.0,
                            "contraste": 1.0, "saturacao": 1.0, "temperatura": 0.0})
    proj.setdefault("trilha", {"arquivo": None, "volume": 0.14, "abaixar_na_fala": True})
    proj.setdefault("sugestoes", {"ganchos": []})
    proj.setdefault("formato", {"enquadramento": "preencher", "volume": True})
    if not proj.get("arquivos") and proj.get("video"):
        # projeto de um arquivo só, das versões anteriores
        info = dict(proj.get("info") or {})
        info.setdefault("tem_video", True); info.setdefault("tem_audio", True); info.setdefault("hdr", False)
        proj["arquivos"] = [{"id": "a1", "arquivo": proj["video"], "nome": os.path.basename(proj["video"]),
                             "tipo": "video", "info": info, "ini": 0.0, "fim": float(info.get("duracao", 0)),
                             "modo": "fala", "manter": None}]
    proj["versao"] = max(3, int(proj.get("versao", 2)))
    return proj


def sondar_video(video):
    s = sondar(video)
    return {k: s[k] for k in ("largura", "altura", "fps", "duracao")}


def dados_dir():
    d = os.environ.get("SEU_EDITOR_DADOS") or os.path.join(os.path.expanduser("~"), ".seu-editor")
    os.makedirs(d, exist_ok=True)
    return d


def caminho(pasta, nome="projeto.json"):
    return os.path.join(pasta, nome)


def carregar(pasta):
    with open(caminho(pasta), encoding="utf-8") as f:
        return normalizar(json.load(f))


def salvar(pasta, proj):
    _gravar_atomico(caminho(pasta), proj)


def mtime(pasta):
    try:
        return os.path.getmtime(caminho(pasta))
    except OSError:
        return 0.0


def ler_estado(pasta):
    try:
        with open(caminho(pasta, "estado.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def escrever_estado(pasta, **campos):
    estado = ler_estado(pasta)
    estado.update(campos)
    estado["atualizado"] = time.time()
    _gravar_atomico(caminho(pasta, "estado.json"), estado)
    return estado


def _gravar_atomico(destino, dados):
    pasta = os.path.dirname(destino)
    fd, tmp = tempfile.mkstemp(dir=pasta, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    os.replace(tmp, destino)
