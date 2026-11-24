"""Traz insertos de fora pra pasta insertos/ do projeto.

Aceita:
- pasta ou arquivo do Google Drive compartilhado como "qualquer pessoa com o link";
- link do Dropbox;
- link direto pra um arquivo (jpg, png, mp4, mp3...);
- uma pasta ou arquivo do próprio computador.
"""

import os
import re
import shutil
import urllib.parse
import urllib.request

EXTENSOES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".m4v", ".webm",
             ".mp3", ".wav", ".m4a", ".aac", ".ogg"}


def _achatar(origem, destino):
    """Move todos os arquivos úteis de origem (com subpastas) pra destino, sem sobrescrever."""
    trazidos = []
    for raiz, _, arquivos in os.walk(origem):
        for nome in sorted(arquivos):
            if os.path.splitext(nome)[1].lower() not in EXTENSOES:
                continue
            alvo, n = os.path.join(destino, nome), 2
            base, ext = os.path.splitext(nome)
            while os.path.exists(alvo):
                alvo = os.path.join(destino, f"{base}-{n}{ext}")
                n += 1
            shutil.move(os.path.join(raiz, nome), alvo)
            trazidos.append(os.path.basename(alvo))
    return trazidos


def buscar(pasta_projeto, origem, log=print):
    destino = os.path.join(pasta_projeto, "insertos")
    os.makedirs(destino, exist_ok=True)
    tmp = os.path.join(pasta_projeto, "_baixando")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    try:
        caminho_local = os.path.expanduser(origem)
        if os.path.exists(caminho_local):
            if os.path.isdir(caminho_local):
                shutil.copytree(caminho_local, os.path.join(tmp, "copia"))
            else:
                shutil.copy(caminho_local, tmp)
        elif "drive.google.com" in origem or "docs.google.com" in origem:
            import gdown
            if "/folders/" in origem:
                log("baixando a pasta do Google Drive")
                gdown.download_folder(url=origem, output=tmp, quiet=True, use_cookies=False)
            else:
                log("baixando o arquivo do Google Drive")
                gdown.download(url=origem, output=tmp + os.sep, quiet=True, fuzzy=True, use_cookies=False)
        else:
            url = origem
            if "dropbox.com" in url:
                url = re.sub(r"([?&])dl=0", r"\1dl=1", url)
                if "dl=1" not in url:
                    url += ("&" if "?" in url else "?") + "dl=1"
            nome = os.path.basename(urllib.parse.urlparse(url).path) or "arquivo"
            log(f"baixando {nome}")
            req = urllib.request.Request(url, headers={"User-Agent": "seu-editor"})
            with urllib.request.urlopen(req, timeout=120) as r, open(os.path.join(tmp, nome), "wb") as f:
                shutil.copyfileobj(r, f)
            if nome.lower().endswith(".zip"):
                shutil.unpack_archive(os.path.join(tmp, nome), os.path.join(tmp, "zip"))
        trazidos = _achatar(tmp, destino)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not trazidos:
        raise RuntimeError("não encontrei fotos, vídeos ou músicas nesse link. Confira se ele está compartilhado "
                           "como 'qualquer pessoa com o link'.")
    return trazidos
