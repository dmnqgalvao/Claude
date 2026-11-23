"""Leitura e gravação do projeto (projeto.json) e do estado (estado.json).

Um projeto é uma pasta com:
  projeto.json   tudo que a pessoa e o Claude decidiram (cortes, textos, estilo)
  estado.json    o que está acontecendo agora (transcrevendo, exportando...)
  exportados/    os vídeos prontos
"""

import json
import os
import subprocess
import tempfile
import time

RITMOS = {
    "calmo": {"pausa_max": 0.70, "folga": 0.16},
    "natural": {"pausa_max": 0.40, "folga": 0.10},
    "acelerado": {"pausa_max": 0.18, "folga": 0.06},
}


def projeto_padrao(video, nome, marca=None):
    marca = marca or {}
    return {
        "versao": 1,
        "nome": nome,
        "video": os.path.abspath(video),
        "info": sondar_video(video),
        "palavras": [],
        "ajustes": {
            "ritmo": marca.get("ritmo", "natural"),
            "cortar_pausas": True,
            **RITMOS[marca.get("ritmo", "natural")],
        },
        "legenda": {
            "ativa": True,
            "estilo": marca.get("estilo", "pop"),
            "palavras": None,          # None = usa o padrão do estilo
            "posicao": 0.64,           # altura do centro da legenda (0 = topo, 1 = base)
            "caixa_alta": None,        # None = usa o padrão do estilo
            "sem_pontuacao": True,
        },
        "gancho": {"ativo": False, "texto": "", "duracao": 3.0, "posicao": 0.20},
        "titulos": [],                 # [{"palavra": i, "texto": "...", "duracao": 2.0}]
        "sugestoes": {"ganchos": []},
        "marca": {
            "texto": marca.get("texto", "#FFFFFF"),
            "destaque": marca.get("destaque", "#FFD84D"),
        },
        "formato": {"enquadramento": "preencher", "volume": True},
        "termos": marca.get("termos", []),
    }


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


def caminho(pasta, nome="projeto.json"):
    return os.path.join(pasta, nome)


def carregar(pasta):
    with open(caminho(pasta), encoding="utf-8") as f:
        return json.load(f)


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
