"""Prepara o computador pra usar o Corte Seco.

Roda com o python3 do sistema. Confere o FFmpeg, cria um ambiente Python
isolado em ~/.corte-seco/venv e instala o faster-whisper. No fim imprime
uma linha JSON com o caminho do Python que o Claude deve usar.

  python3 instalar.py                 confere e instala o que faltar
  python3 instalar.py --baixar-modelo também baixa o modelo de transcrição
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import venv

PACOTES = ["faster-whisper>=1.1,<2", "av>=12,<16"]


def dados():
    d = os.environ.get("CORTE_SECO_DADOS") or os.path.join(os.path.expanduser("~"), ".corte-seco")
    os.makedirs(d, exist_ok=True)
    return d


def python_do_venv(pasta):
    if platform.system() == "Windows":
        return os.path.join(pasta, "Scripts", "python.exe")
    return os.path.join(pasta, "bin", "python")


def dica_ffmpeg():
    so = platform.system()
    if so == "Darwin":
        return "brew install ffmpeg   (se não tiver o Homebrew: https://brew.sh)"
    if so == "Windows":
        return "winget install --id Gyan.FFmpeg -e   (depois feche e abra o terminal)"
    return "sudo apt install ffmpeg   (ou o gerenciador de pacotes da sua distribuição)"


def conferir_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return False, "ffmpeg não encontrado"
    filtros = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    if " ass " not in filtros:
        return False, "o ffmpeg instalado não tem suporte a legendas (libass)"
    return True, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baixar-modelo", action="store_true")
    ap.add_argument("--modelo", default="large-v3-turbo")
    a = ap.parse_args()

    if sys.version_info < (3, 9):
        print(json.dumps({"ok": False, "erro": "precisa de Python 3.9 ou mais novo"}))
        sys.exit(1)

    ok, motivo = conferir_ffmpeg()
    if not ok:
        print(json.dumps({"ok": False, "erro": motivo, "instalar_ffmpeg": dica_ffmpeg()}, ensure_ascii=False))
        sys.exit(2)

    pasta_venv = os.path.join(dados(), "venv")
    py = python_do_venv(pasta_venv)
    if not os.path.exists(py):
        print("criando o ambiente Python em " + pasta_venv, file=sys.stderr)
        venv.create(pasta_venv, with_pip=True)

    teste = subprocess.run([py, "-c", "import faster_whisper, av"], capture_output=True)
    if teste.returncode != 0:
        print("instalando o faster-whisper (uns 2 minutos na primeira vez)", file=sys.stderr)
        subprocess.run([py, "-m", "pip", "install", "-q", "--upgrade", "pip"], check=False)
        r = subprocess.run([py, "-m", "pip", "install", "-q", *PACOTES])
        if r.returncode != 0:
            print(json.dumps({"ok": False, "erro": "a instalação do faster-whisper falhou"}))
            sys.exit(3)

    if a.baixar_modelo:
        print(f"baixando o modelo {a.modelo} (cerca de 1,5 GB na primeira vez)", file=sys.stderr)
        codigo = (
            "from faster_whisper import WhisperModel; import sys; "
            f"WhisperModel({a.modelo!r}, device='cpu', compute_type='int8', download_root=sys.argv[1])"
        )
        subprocess.run([py, "-c", codigo, os.path.join(dados(), "modelos")], check=True)

    print(json.dumps({"ok": True, "python": py, "dados": dados()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
