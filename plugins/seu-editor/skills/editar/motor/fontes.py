"""Fontes da pessoa: enviadas pela interface ou baixadas do Google Fonts.

Ficam em ~/.seu-editor/fontes/ e servem pra todos os projetos. O registro
fica em fontes.json, no mesmo formato da lista FONTES de estilos.py.
"""

import json
import os
import re
import shutil
import urllib.request

EXTENSOES = {".ttf", ".otf", ".woff", ".woff2"}


def _pasta(dados):
    p = os.path.join(dados, "fontes")
    os.makedirs(p, exist_ok=True)
    return p


def _registro(dados):
    try:
        with open(os.path.join(_pasta(dados), "fontes.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _salvar(dados, reg):
    with open(os.path.join(_pasta(dados), "fontes.json"), "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)


def _id(nome):
    return "p-" + (re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-") or "fonte")


def _peso_do_arquivo(nome_arquivo):
    n = nome_arquivo.lower()
    for chave, peso in (("black", 900), ("heavy", 900), ("extrabold", 800), ("semibold", 600), ("bold", 700),
                        ("medium", 500), ("light", 300), ("thin", 100)):
        if chave in n:
            return peso
    return 400


def registrar(dados, arquivos, nome):
    """arquivos: caminhos de .ttf/.otf/.woff2 da mesma família. Devolve o id da fonte."""
    pasta = _pasta(dados)
    reg = _registro(dados)
    fid = _id(nome)
    lista = []
    for caminho in arquivos:
        ext = os.path.splitext(caminho)[1].lower()
        if ext not in EXTENSOES:
            continue
        destino_nome = f"{fid}-{os.path.basename(caminho)}".replace(" ", "-")
        destino = os.path.join(pasta, destino_nome)
        if os.path.abspath(caminho) != os.path.abspath(destino):
            shutil.copy(caminho, destino)
        lista.append({"arquivo": destino_nome, "peso": _peso_do_arquivo(destino_nome),
                      "italico": "italic" in destino_nome.lower()})
    if not lista:
        raise ValueError("nenhum arquivo de fonte (.ttf, .otf, .woff ou .woff2)")
    variavel = any("[" in a["arquivo"] for a in lista)
    pesos = sorted({a["peso"] for a in lista if not a["italico"]}) or [400]
    peso = 700 if variavel or 700 in pesos else pesos[-1] if pesos[-1] <= 700 else pesos[0]
    reg[fid] = {"nome": nome, "familia": f'"{nome}"', "peso": peso, "largura": .56,
                "arquivos": lista, "variavel": variavel, "da_pessoa": True}
    _salvar(dados, reg)
    return fid


def baixar_google(dados, nome):
    """Baixa uma família do repositório público do Google Fonts (github.com/google/fonts)."""
    slug = re.sub(r"[^a-z0-9]", "", nome.lower())
    tmp = os.path.join(_pasta(dados), "_baixando")
    os.makedirs(tmp, exist_ok=True)
    base = "https://raw.githubusercontent.com/google/fonts/main"
    try:
        for licenca in ("ofl", "apache", "ufl"):
            try:
                with urllib.request.urlopen(f"{base}/{licenca}/{slug}/METADATA.pb", timeout=20) as r:
                    meta = r.read().decode("utf-8", "replace")
            except Exception:
                continue
            arquivos = sorted(set(re.findall(r'filename:\s*"([^"]+\.ttf)"', meta)))
            m = re.search(r'^name:\s*"([^"]+)"', meta, re.M)
            nome_real = m.group(1) if m else nome
            caminhos = []
            for arq in arquivos:
                destino = os.path.join(tmp, arq)
                url = f"{base}/{licenca}/{slug}/" + urllib.request.quote(arq)
                with urllib.request.urlopen(url, timeout=60) as r, open(destino, "wb") as f:
                    f.write(r.read())
                caminhos.append(destino)
            if caminhos:
                return registrar(dados, caminhos, nome_real)
        raise LookupError(f"não achei '{nome}' no Google Fonts. Confira o nome em fonts.google.com")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
