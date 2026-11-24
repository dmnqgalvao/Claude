"""Servidor local da interface. Só escuta em 127.0.0.1 e só usa a biblioteca padrão."""


import json
import mimetypes
import os
import re
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from . import estilos as E
from . import plano as PL
from . import projeto as P
from . import render

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_APP = os.path.join(RAIZ, "app")


class Estudio(BaseHTTPRequestHandler):
    pasta = None
    dados = None
    exportando = threading.Lock()

    def log_message(self, *args):
        pass

    # ------------------------------------------------------------ respostas
    def _json(self, dados, status=200):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _corpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _arquivo(self, caminho, tipo=None):
        if not os.path.isfile(caminho):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        tamanho = os.path.getsize(caminho)
        tipo = tipo or mimetypes.guess_type(caminho)[0] or "application/octet-stream"
        intervalo = self.headers.get("Range")
        ini, fim = 0, tamanho - 1
        status = 200
        if intervalo:
            m = re.match(r"bytes=(\d*)-(\d*)", intervalo)
            if m:
                if m.group(1):
                    ini = int(m.group(1))
                    fim = int(m.group(2)) if m.group(2) else fim
                elif m.group(2):
                    ini = max(0, tamanho - int(m.group(2)))
                fim = min(fim, tamanho - 1)
                status = 206
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(fim - ini + 1))
        self.send_header("Cache-Control", "no-store")
        if status == 206:
            self.send_header("Content-Range", f"bytes {ini}-{fim}/{tamanho}")
        self.end_headers()
        try:
            with open(caminho, "rb") as f:
                f.seek(ini)
                falta = fim - ini + 1
                while falta > 0:
                    bloco = f.read(min(1 << 16, falta))
                    if not bloco:
                        break
                    self.wfile.write(bloco)
                    falta -= len(bloco)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ------------------------------------------------------------ rotas
    def do_GET(self):
        rota = unquote(urlparse(self.path).path)
        if rota in ("/", "/index.html"):
            return self._arquivo(os.path.join(PASTA_APP, "index.html"), "text/html; charset=utf-8")
        if rota.startswith("/app/"):
            return self._estatico(PASTA_APP, rota[5:])
        if rota.startswith("/fontes/"):
            return self._estatico(E.PASTA_FONTES, rota[8:])
        if rota == "/video":
            proj = P.carregar(self.pasta)
            return self._arquivo(proj["video"])
        if rota == "/render":
            return self._arquivo(os.path.join(PASTA_APP, "render.html"), "text/html; charset=utf-8")
        if rota.startswith("/insertos/"):
            return self._estatico(os.path.join(self.pasta, "insertos"), rota[10:])
        if rota == "/api/insertos":
            return self._json({"itens": listar_insertos(self.pasta)})
        if rota.startswith("/exportados/"):
            return self._estatico(os.path.join(self.pasta, "exportados"), rota[12:])
        if rota == "/api/projeto":
            return self._json({"projeto": P.carregar(self.pasta), "mtime": P.mtime(self.pasta)})
        if rota == "/api/estilos":
            return self._json(E.estilos_para_interface(self.dados))
        if rota.startswith("/fontes-pessoa/"):
            return self._estatico(os.path.join(self.dados, "fontes"), rota[15:])
        if rota == "/api/estado":
            return self._json({"estado": P.ler_estado(self.pasta), "mtime": P.mtime(self.pasta)})
        if rota == "/api/exportados":
            pasta = os.path.join(self.pasta, "exportados")
            itens = []
            if os.path.isdir(pasta):
                for nome in sorted(os.listdir(pasta), key=lambda n: -os.path.getmtime(os.path.join(pasta, n))):
                    if nome.endswith(".mp4"):
                        c = os.path.join(pasta, nome)
                        itens.append({"nome": nome, "tamanho": os.path.getsize(c), "quando": os.path.getmtime(c),
                                      "caminho": c})
            return self._json({"itens": itens})
        self.send_error(HTTPStatus.NOT_FOUND)

    def _estatico(self, base, relativo):
        caminho = os.path.realpath(os.path.join(base, relativo))
        if not caminho.startswith(os.path.realpath(base) + os.sep):
            return self.send_error(HTTPStatus.FORBIDDEN)
        return self._arquivo(caminho)

    def do_PUT(self):
        if urlparse(self.path).path != "/api/projeto":
            return self.send_error(HTTPStatus.NOT_FOUND)
        corpo = self._corpo()
        proj, base = corpo.get("projeto"), corpo.get("mtime")
        if not isinstance(proj, dict) or "palavras" not in proj:
            return self._json({"erro": "projeto inválido"}, 400)
        atual = P.mtime(self.pasta)
        if base is not None and abs(atual - float(base)) > 1e-6:
            # o Claude (ou outra aba) mudou o arquivo depois que a interface leu
            return self._json({"erro": "conflito", "projeto": P.carregar(self.pasta), "mtime": atual}, 409)
        P.salvar(self.pasta, proj)
        return self._json({"ok": True, "mtime": P.mtime(self.pasta)})

    def do_POST(self):
        rota = urlparse(self.path).path
        if rota == "/api/plano":
            return self._json(PL.montar_plano(P.normalizar(self._corpo())))
        if rota == "/api/exportar":
            previa = bool(self._corpo().get("previa"))
            if not self.exportando.acquire(blocking=False):
                return self._json({"erro": "já tem uma exportação rodando"}, 409)

            def trabalho():
                try:
                    render.exportar(self.pasta, previa=previa)
                except Exception as e:  # o erro vai pro estado e aparece na interface
                    P.escrever_estado(self.pasta, tarefa=None, mensagem="a exportação falhou", erro=str(e)[-1500:])
                finally:
                    self.exportando.release()

            threading.Thread(target=trabalho, daemon=True).start()
            return self._json({"ok": True})
        if rota == "/api/insertos":
            nome = os.path.basename(unquote(parse_qs(urlparse(self.path).query).get("nome", [""])[0]))
            nome = re.sub(r"[^\w.\- ]+", "-", nome).strip() or "arquivo"
            if os.path.splitext(nome)[1].lower() not in EXTENSOES:
                return self._json({"erro": "use foto (jpg, png, webp) ou vídeo (mp4, mov)"}, 400)
            pasta = os.path.join(self.pasta, "insertos")
            os.makedirs(pasta, exist_ok=True)
            destino, n = os.path.join(pasta, nome), 2
            base, ext = os.path.splitext(nome)
            while os.path.exists(destino):
                destino = os.path.join(pasta, f"{base}-{n}{ext}")
                n += 1
            falta = int(self.headers.get("Content-Length") or 0)
            with open(destino, "wb") as f:
                while falta > 0:
                    bloco = self.rfile.read(min(1 << 20, falta))
                    if not bloco:
                        break
                    f.write(bloco)
                    falta -= len(bloco)
            return self._json({"ok": True, "nome": os.path.basename(destino)})
        if rota == "/api/fontes":
            from . import fontes as F
            q = parse_qs(urlparse(self.path).query)
            arquivo = os.path.basename(unquote(q.get("arquivo", [""])[0]))
            nome = unquote(q.get("nome", [""])[0]).strip() or os.path.splitext(arquivo)[0]
            if os.path.splitext(arquivo)[1].lower() not in F.EXTENSOES:
                return self._json({"erro": "envie um arquivo .ttf, .otf, .woff ou .woff2"}, 400)
            tmp = os.path.join(self.dados, "fontes", "_envio")
            os.makedirs(tmp, exist_ok=True)
            caminho = os.path.join(tmp, arquivo)
            n = int(self.headers.get("Content-Length") or 0)
            with open(caminho, "wb") as f:
                f.write(self.rfile.read(n))
            try:
                fid = F.registrar(self.dados, [caminho], nome)
            finally:
                os.remove(caminho)
            return self._json({"ok": True, "id": fid})
        if rota == "/api/marca":
            proj = P.carregar(self.pasta)
            vis_leg = {k: v for k, v in proj["legenda"]["visual"].items()}
            marca = {
                "cores": proj["marca"].get("cores"), "legenda": vis_leg,
                "gancho": proj["gancho"].get("visual"), "ritmo": proj["ajustes"].get("ritmo"),
                "fontes": proj.get("fontes"),
                "termos": proj.get("termos", []),
            }
            if marca["ritmo"] not in P.RITMOS:
                marca["ritmo"] = "natural"
            os.makedirs(self.dados, exist_ok=True)
            with open(os.path.join(self.dados, "marca.json"), "w", encoding="utf-8") as f:
                json.dump(marca, f, ensure_ascii=False, indent=1)
            return self._json({"ok": True})
        self.send_error(HTTPStatus.NOT_FOUND)


EXTENSOES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".m4v", ".webm"}
VIDEOS = {".mp4", ".mov", ".m4v", ".webm"}


def listar_insertos(pasta):
    base = os.path.join(pasta, "insertos")
    itens = []
    if os.path.isdir(base):
        for nome in sorted(os.listdir(base)):
            ext = os.path.splitext(nome)[1].lower()
            if ext in EXTENSOES:
                itens.append({"nome": nome, "tipo": "video" if ext in VIDEOS else "imagem",
                              "tamanho": os.path.getsize(os.path.join(base, nome))})
    return itens


def _classe(pasta, dados):
    return type("EstudioProjeto", (Estudio,), {"pasta": os.path.abspath(pasta), "dados": dados,
                                               "exportando": threading.Lock()})


def iniciar_em_segundo_plano(pasta):
    """Servidor temporário numa porta livre, usado pela exportação."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _classe(pasta, P.dados_dir()))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"


def servir(pasta, porta=4848, abrir=True, dados=None):
    classe = _classe(pasta, dados or P.dados_dir())
    servidor = None
    for p in range(porta, porta + 30):
        try:
            servidor = ThreadingHTTPServer(("127.0.0.1", p), classe)
            porta = p
            break
        except OSError:
            continue
    if servidor is None:
        raise SystemExit("nenhuma porta livre entre %d e %d" % (porta, porta + 29))
    url = f"http://127.0.0.1:{porta}/"
    P.escrever_estado(pasta, url=url)
    print(f"interface aberta em {url}", flush=True)
    if abrir:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
