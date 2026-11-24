"""Confere se tem versão nova do Seu Editor no GitHub e o que mudou.

Lê dois arquivos públicos do repositório (o plugin.json e o novidades.json) e compara com
a versão instalada. Não manda nada sobre a pessoa nem sobre o vídeo: é só um download dos
dois arquivos. A resposta fica guardada por 6 horas pra não perguntar toda hora, e se a
internet falhar a ferramenta segue sem aviso.
"""

import json
import os
import time
import urllib.request

RAIZ_PLUGIN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE = "https://raw.githubusercontent.com/dmnqgalvao/Claude/claude/eager-galileo-xl2wpq/plugins/seu-editor"
CACHE_S = 6 * 3600
COMANDO = "atualiza o plugin seu-editor do marketplace domigalvao"


def _ler_json(caminho):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def local():
    return (_ler_json(os.path.join(RAIZ_PLUGIN, ".claude-plugin", "plugin.json")) or {}).get("version", "0")


def _num(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)


def _baixar(nome):
    req = urllib.request.Request(f"{BASE}/{nome}?t={int(time.time() // 600)}", headers={"User-Agent": "seu-editor"})
    with urllib.request.urlopen(req, timeout=4) as r:
        return json.loads(r.read().decode("utf-8"))


def checar(dados, forcar=False):
    """{"local", "remota", "nova", "novidades": [...], "comando"}. Nunca levanta erro."""
    cache = os.path.join(dados, "versao.json")
    guardado = _ler_json(cache) or {}
    if forcar or time.time() - guardado.get("quando", 0) > CACHE_S:
        try:
            remota = _baixar(".claude-plugin/plugin.json").get("version")
            try:
                novidades = _baixar("novidades.json")
            except Exception:
                novidades = []
            guardado = {"quando": time.time(), "remota": remota, "novidades": novidades}
            os.makedirs(dados, exist_ok=True)
            with open(cache, "w", encoding="utf-8") as f:
                json.dump(guardado, f, ensure_ascii=False)
        except Exception:
            pass
    atual = local()
    remota = guardado.get("remota") or atual
    nova = _num(remota) > _num(atual)
    # o que mudou entre a versão instalada e a nova
    itens = [n for n in guardado.get("novidades") or [] if _num(n.get("versao")) > _num(atual)] if nova else []
    return {"local": atual, "remota": remota, "nova": nova, "novidades": itens, "comando": COMANDO}
