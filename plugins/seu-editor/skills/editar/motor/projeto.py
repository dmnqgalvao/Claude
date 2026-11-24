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


def projeto_padrao(video, nome, marca=None):
    marca = marca or {}
    ritmo = marca.get("ritmo") if marca.get("ritmo") in RITMOS else "seco"
    return normalizar({
        "versao": 2,
        "nome": nome,
        "video": os.path.abspath(video),
        "info": sondar_video(video),
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
        "cor": {"auto": False, "ganhos": [1.0, 1.0, 1.0], "look": "dourado", "intensidade": 0.8, "brilho": 0.0,
                "contraste": 1.0, "saturacao": 1.0, "temperatura": 0.0, "nitidez": 0.5},
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
        if cor["look"] not in ("nenhum", "natural", "dourado", "pessego", "verao", "frio", "cinema", "filme", "suave", "pb"):
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
    proj["versao"] = 2
    return proj


def sondar_video(video):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,avg_frame_rate:stream_tags=rotate:stream_side_data=rotation:format=duration",
             "-of", "json", video],
            capture_output=True, text=True, check=True).stdout
        d = json.loads(out)
        s = d["streams"][0]
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
        return {"largura": w, "altura": h, "fps": round(fps, 3),
                "duracao": float(d["format"]["duration"])}
    except Exception:
        return {"largura": 1080, "altura": 1920, "fps": 30.0, "duracao": 0.0}


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
