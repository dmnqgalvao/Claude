"""Linha de comando do Seu Editor. É por aqui que o Claude mexe no projeto.

Uso: python -m motor.cli <comando> ...   (rodar de dentro da pasta da skill)

Comandos:
  novo VIDEO_OU_LINK [--nome N] [--base PASTA]   cria o projeto (aceita link do Drive/Dropbox)
  achar-video [parte do nome]               acha o vídeo quando a pessoa não diz onde está
  transcrever PROJETO [--modelo M]          transcreve com o tempo de cada palavra
  servir PROJETO [--porta P] [--nao-abrir]  abre a interface no navegador
  texto PROJETO                             mostra a transcrição numerada
  cortar PROJETO 12-18 25 [--motivo M]      corta palavras (intervalos de índices)
  manter PROJETO 12-18                      desfaz o corte dessas palavras
  destacar PROJETO 30 41-42 [--remover]     marca palavras de destaque na legenda
  gancho PROJETO "texto" [--duracao 3]      define o gancho escrito do início
  sugerir PROJETO "gancho 1" "gancho 2"...  deixa sugestões de gancho na interface
  insertos PROJETO                          lista as fotos e vídeos da pasta insertos/
  buscar-insertos PROJETO LINK_OU_PASTA     traz insertos do Google Drive, Dropbox, link ou pasta
  camada PROJETO '{"tipo": ...}'            cria ou atualiza uma camada (JSON, veja o SKILL.md)
  camadas PROJETO                           lista as camadas com id, tipo e tempo
  remover PROJETO ID [ID...]                apaga camadas
  legenda PROJETO '{"cor": ...}'            muda o visual da legenda (JSON parcial)
  estilo PROJETO cool|star|basic|glow [--destaque ID] [--texto ID]
  fontes                                    lista as fontes disponíveis (ids)
  fonte "Nome no Google Fonts" | arquivo.ttf [--nome N]   instala uma fonte nova
  cor PROJETO [--auto] [--filtro quente] [--brilho 0.05] [--contraste 1.1] ...
  trilha PROJETO musica.mp3 [--volume 0.14] [--sem-abaixar]   música de fundo (arquivo em insertos/)
  cortar-tempo PROJETO 12.5 14.2 [--desfazer]   corta um trecho por tempo do vídeo original
  receitas                                  lista os jeitos de editar salvos
  receita-aplicar PROJETO "nome"            aplica uma receita e mostra as regras dela
  receita-salvar "nome" [--projeto P] [--descricao D] [--regras R]   cria ou atualiza
  receita-ver "nome"                        mostra a receita inteira
  ajustar PROJETO [--ritmo R] [--posicao 0.64] [--enquadramento ajustar] ...
  status PROJETO "mensagem" [--livre]       mostra o que o Claude está fazendo
  resumo PROJETO                            números do projeto
  exportar PROJETO [--previa]               gera o mp4
"""

import argparse
import json
import os
import re
import shutil
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "motor"

from . import estilos as E          # noqa: E402
from . import plano as PL           # noqa: E402
from . import projeto as P          # noqa: E402


def dados_dir():
    return P.dados_dir()


def marca_global():
    try:
        with open(os.path.join(dados_dir(), "marca.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def intervalos(itens, total):
    idx = set()
    for item in itens:
        for parte in str(item).split(","):
            parte = parte.strip()
            if not parte:
                continue
            m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", parte)
            if m:
                a, b = sorted((int(m.group(1)), int(m.group(2))))
                idx.update(range(a, b + 1))
            else:
                idx.add(int(parte))
    return sorted(i for i in idx if 0 <= i < total)


def fmt_tempo(t):
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:04.1f}"


def cmd_novo(a):
    extras = []
    if not os.path.exists(os.path.expanduser(a.video)) and re.match(r"https?://", a.video):
        from . import buscar as B
        destino = os.path.join(os.path.expanduser("~"), "Downloads", "seu-editor")
        print("baixando o vídeo do link...", file=sys.stderr)
        a.video, extras = B.baixar_video(a.video, destino, log=lambda m: print(m, file=sys.stderr))
        print(f"vídeo baixado: {a.video}", file=sys.stderr)
    a.video = os.path.expanduser(a.video)
    if not os.path.exists(a.video):
        sys.exit(f"vídeo não encontrado: {a.video}")
    nome = a.nome or os.path.splitext(os.path.basename(a.video))[0]
    base = a.base or os.path.join(os.getcwd(), "seu-editor")
    pasta = os.path.join(base, re.sub(r"[^\w\-]+", "-", nome.lower()).strip("-") or "video")
    sufixo, original = 2, pasta
    while os.path.exists(pasta):
        pasta = f"{original}-{sufixo}"
        sufixo += 1
    os.makedirs(pasta)
    P.salvar(pasta, P.projeto_padrao(a.video, nome, marca_global()))
    if extras:
        os.makedirs(os.path.join(pasta, "insertos"), exist_ok=True)
        for v in extras:
            shutil.move(v, os.path.join(pasta, "insertos", os.path.basename(v)))
        print(f"{len(extras)} outros vídeos do link foram pra insertos/", file=sys.stderr)
    P.escrever_estado(pasta, mensagem="projeto criado", tarefa=None)
    print(pasta)


def cmd_transcrever(a):
    from . import transcrever as T
    modelos = os.path.join(dados_dir(), "modelos")
    T.transcrever(a.projeto, modelo=a.modelo, dir_modelos=modelos)
    proj = P.carregar(a.projeto)
    print(f"{len(proj['palavras'])} palavras transcritas")


def cmd_servir(a):
    from . import servidor
    servidor.servir(a.projeto, porta=a.porta, abrir=not a.nao_abrir, dados=dados_dir())


def cmd_texto(a):
    proj = P.carregar(a.projeto)
    pal = proj["palavras"]
    if not pal:
        print("(sem transcrição ainda)")
        return
    linha = []
    for k, p in enumerate(pal):
        if k and p["ini"] - pal[k - 1]["fim"] > 0.6:
            print(" ".join(linha))
            print(f"   [pausa {p['ini'] - pal[k - 1]['fim']:.1f}s]")
            linha = []
        if not linha:
            linha.append(f"({fmt_tempo(p['ini'])})")
        t = p["t"]
        if p.get("cortada"):
            t = f"~{t}~"
        if p.get("destaque"):
            t = f"*{t}*"
        linha.append(f"{p['i']}:{t}")
    print(" ".join(linha))
    print("\nlegenda: ~cortada~  *destaque*  (m:ss) início da linha no vídeo original")


def _editar_palavras(a, campo, valor, motivo=None):
    proj = P.carregar(a.projeto)
    idx = intervalos(a.indices, len(proj["palavras"]))
    for i in idx:
        p = proj["palavras"][i]
        p[campo] = valor
        if campo == "cortada":
            if valor:
                p["motivo"] = motivo or "claude"
                p["origem"] = "claude"
            else:
                p.pop("motivo", None)
                p["origem"] = "claude"
    P.salvar(a.projeto, proj)
    return idx


def cmd_cortar(a):
    idx = _editar_palavras(a, "cortada", True, a.motivo)
    print(f"{len(idx)} palavras cortadas ({a.motivo})")


def cmd_manter(a):
    idx = _editar_palavras(a, "cortada", False)
    print(f"{len(idx)} palavras de volta")


def cmd_destacar(a):
    idx = _editar_palavras(a, "destaque", not a.remover)
    print(f"{len(idx)} palavras {'sem' if a.remover else 'com'} destaque")


def cmd_gancho(a):
    proj = P.carregar(a.projeto)
    proj["gancho"].update(ativo=bool(a.texto.strip()), texto=a.texto.strip())
    if a.duracao:
        proj["gancho"]["duracao"] = a.duracao
    P.salvar(a.projeto, proj)
    print("gancho definido")


def cmd_sugerir(a):
    proj = P.carregar(a.projeto)
    proj.setdefault("sugestoes", {})["ganchos"] = [t.strip() for t in a.textos if t.strip()]
    P.salvar(a.projeto, proj)
    print(f"{len(proj['sugestoes']['ganchos'])} sugestões de gancho na interface")


def _ler_json(texto):
    try:
        d = json.loads(texto)
    except ValueError as e:
        sys.exit(f"JSON inválido: {e}")
    if not isinstance(d, dict):
        sys.exit("o JSON precisa ser um objeto {...}")
    return d


def cmd_insertos(a):
    from .servidor import listar_insertos
    itens = listar_insertos(a.projeto)
    if not itens:
        print("(nenhum arquivo em insertos/. Peça pra pessoa arrastar fotos e vídeos na aba camadas,"
              " ou copie os arquivos pra " + os.path.join(a.projeto, "insertos") + ")")
    for it in itens:
        caminho = os.path.join(a.projeto, "insertos", it["nome"])
        extra = ""
        if it["tipo"] == "video":
            extra = f" · {P.sondar_video(caminho)['duracao']:.1f}s"
        print(f"{it['tipo']:7} {it['nome']}{extra}  ->  {caminho}")


def cmd_camada(a):
    import random
    proj = P.carregar(a.projeto)
    c = _ler_json(a.json)
    lista = proj.setdefault("camadas", [])
    existente = next((x for x in lista if x.get("id") and x.get("id") == c.get("id")), None)
    if existente:
        for k, v in c.items():
            if v is None:
                existente.pop(k, None)
            else:
                existente[k] = v
        c = existente
    else:
        if c.get("tipo") not in ("impacto", "imagem", "video", "desenho", "texto", "efeito", "som", "cascata"):
            sys.exit("tipo precisa ser impacto, imagem, video, desenho, texto, cascata, efeito ou som")
        c.setdefault("id", c["tipo"][:3] + "".join(random.choice("abcdefghijkmnpqrstuvwxyz23456789") for _ in range(5)))
        if c.get("palavra") is None and c.get("ini") is None:
            c["ini"] = 0
        lista.append(c)
    P.salvar(a.projeto, proj)
    print(c["id"])


def cmd_camadas(a):
    proj = P.carregar(a.projeto)
    plano = PL.montar_plano(proj)
    if not plano["camadas"]:
        print("(nenhuma camada)")
    for c in plano["camadas"]:
        desc = c.get("texto") or c.get("arquivo") or c.get("forma") or ""
        ancora = f"palavra {c['palavra']}" if c.get("palavra") is not None else f"{c.get('ini', 0)}s"
        print(f"{c['id']:10} {c['tipo']:8} {fmt_tempo(c['ini_out'])}-{fmt_tempo(c['fim_out'])} ({ancora})  {desc}")


def cmd_remover(a):
    proj = P.carregar(a.projeto)
    antes = len(proj.get("camadas", []))
    proj["camadas"] = [c for c in proj.get("camadas", []) if c.get("id") not in set(a.ids)]
    proj["titulos"] = []
    P.salvar(a.projeto, proj)
    print(f"{antes - len(proj['camadas'])} camadas removidas")


def cmd_legenda(a):
    proj = P.carregar(a.projeto)
    proj["legenda"]["visual"].update(_ler_json(a.json))
    P.salvar(a.projeto, proj)
    print("visual da legenda atualizado")


def cmd_fonte(a):
    from . import fontes as F
    if os.path.exists(a.nome_ou_arquivo):
        fid = F.registrar(dados_dir(), [a.nome_ou_arquivo], a.nome or os.path.splitext(os.path.basename(a.nome_ou_arquivo))[0])
    else:
        fid = F.baixar_google(dados_dir(), a.nome_ou_arquivo)
    print(fid)


def cmd_fontes(a):
    for fid, f in E.todas_as_fontes(dados_dir()).items():
        print(f"{fid:18} {f['nome']}{'  (da pessoa)' if f.get('da_pessoa') else ''}")
    print("\nestilos (dupla destaque + texto):")
    for k in E.KITS:
        print(f"  {k['id']:10} destaque={k['destaque']}  texto={k['texto']}")


def cmd_estilo(a):
    proj = P.carregar(a.projeto)
    kit = next((k for k in E.KITS if k["id"] == a.estilo), None)
    f = proj["fontes"]
    if kit:
        f.update(kit=kit["id"], destaque=kit["destaque"], texto=kit["texto"])
    if a.destaque:
        f.update(destaque=a.destaque, kit="personalizado")
    if a.texto:
        f.update(texto=a.texto, kit="personalizado")
    P.salvar(a.projeto, proj)
    print(f"destaque={f['destaque']} texto={f['texto']}")


def cmd_cor(a):
    from . import cor as C
    proj = P.carregar(a.projeto)
    c = proj["cor"]
    if a.auto:
        c.update(C.analisar(proj["video"]), auto=True)
    if a.sem_auto:
        c["auto"] = False
    if a.filtro:
        c["look"] = C.APELIDOS.get(a.filtro, a.filtro)
    if a.intensidade is not None:
        c["intensidade"] = a.intensidade
    if a.nitidez is not None:
        c["nitidez"] = a.nitidez
    for campo in ("brilho", "contraste", "saturacao", "temperatura"):
        v = getattr(a, campo)
        if v is not None:
            c[campo] = v
    P.salvar(a.projeto, proj)
    print(json.dumps(c, ensure_ascii=False))


def cmd_trilha(a):
    proj = P.carregar(a.projeto)
    t = proj["trilha"]
    if a.arquivo is not None:
        t["arquivo"] = a.arquivo or None
    if a.volume is not None:
        t["volume"] = a.volume
    if a.sem_abaixar:
        t["abaixar_na_fala"] = False
    P.salvar(a.projeto, proj)
    print(json.dumps(t, ensure_ascii=False))


def cmd_cortar_tempo(a):
    proj = P.carregar(a.projeto)
    lista = proj.setdefault("cortes_tempo", [])
    if a.desfazer:
        proj["cortes_tempo"] = [c for c in lista if not (c["ini"] <= a.ini <= c["fim"])]
    else:
        lista.append({"ini": a.ini, "fim": a.fim})
        for p in proj["palavras"]:
            meio = (p["ini"] + p["fim"]) / 2
            if a.ini <= meio <= a.fim and not p.get("cortada"):
                p.update(cortada=True, motivo="linha do tempo", origem="claude")
    P.salvar(a.projeto, proj)
    print(f"{len(proj['cortes_tempo'])} trechos cortados por tempo")


def cmd_buscar_insertos(a):
    from . import buscar as B
    trazidos = B.buscar(a.projeto, a.origem, log=lambda m: print(m, file=sys.stderr))
    print(f"{len(trazidos)} arquivos em insertos/: " + ", ".join(trazidos))


def cmd_achar_video(a):
    """Acha vídeos quando a pessoa não diz o caminho: os mais recentes ou pelo nome."""
    import glob
    casa = os.path.expanduser("~")
    pastas = [os.path.join(casa, p) for p in ("Downloads", "Desktop", "Movies", "Documents", "Videos",
                                                "Área de Trabalho", "Documentos", "Vídeos")]
    pastas += [os.getcwd()]
    exts = (".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv")
    achados = {}
    for base in pastas:
        if not os.path.isdir(base):
            continue
        for raiz, dirs, arquivos in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("CapCut", "Library", "seu-editor", "node_modules")]
            if raiz.count(os.sep) - base.count(os.sep) > 3:
                dirs[:] = []
            for nome in arquivos:
                if nome.lower().endswith(exts) and not nome.startswith("."):
                    caminho = os.path.join(raiz, nome)
                    try:
                        achados[caminho] = os.path.getmtime(caminho)
                    except OSError:
                        pass
    lista = sorted(achados.items(), key=lambda x: -x[1])
    if a.nome:
        termos = [t for t in re.split(r"\W+", a.nome.lower()) if t]
        lista = [x for x in lista if all(t in os.path.basename(x[0]).lower() for t in termos)] or \
                [x for x in lista if any(t in os.path.basename(x[0]).lower() for t in termos)]
    import time as _t
    for caminho, quando in lista[:a.quantos]:
        dur = P.sondar_video(caminho)["duracao"]
        print(f"{_t.strftime('%d/%m %H:%M', _t.localtime(quando))}  {dur:5.0f}s  {caminho}")
    if not lista:
        print("(nenhum vídeo encontrado)")


def cmd_receitas(a):
    from . import receitas as R
    itens = R.listar(dados_dir())
    if not itens:
        print("(nenhuma receita salva ainda)")
    for r in itens:
        print(f"- {r['nome']}: {r['descricao'] or '(sem descrição)'}")


def cmd_receita_ver(a):
    from . import receitas as R
    print(json.dumps(R.ler(dados_dir(), a.nome), ensure_ascii=False, indent=1))


def cmd_receita_salvar(a):
    from . import receitas as R
    proj = None if a.sem_visual or not a.projeto else P.carregar(a.projeto)
    rid = R.salvar(dados_dir(), a.nome, proj, a.descricao or "", a.regras or "")
    print(f"receita salva: {rid}")


def cmd_receita_aplicar(a):
    from . import receitas as R
    r = R.ler(dados_dir(), a.nome)
    proj = R.aplicar(P.carregar(a.projeto), r)
    P.salvar(a.projeto, proj)
    print(f"receita '{r['nome']}' aplicada (fontes, legenda, gancho, ritmo, cor e formato).")
    if proj["cor"].get("auto_pendente"):
        print("a receita usa correção de cor automática: rode `cor PROJETO --auto` neste vídeo.")
    if r.get("regras"):
        print("\nREGRAS DESTA RECEITA (siga ao montar cortes, destaques, gancho e camadas):\n" + r["regras"])


def cmd_ajustar(a):
    proj = P.carregar(a.projeto)
    if a.ritmo:
        proj["ajustes"]["ritmo"] = a.ritmo
        proj["ajustes"].update(P.RITMOS[a.ritmo])
    if a.pausa_max is not None:
        proj["ajustes"].update(pausa_max=a.pausa_max, ritmo="personalizado")
    if a.folga is not None:
        proj["ajustes"].update(folga=a.folga, ritmo="personalizado")
    if a.posicao is not None:
        proj["legenda"]["posicao"] = a.posicao
    if a.velocidade is not None:
        proj["ajustes"]["velocidade"] = a.velocidade
    if a.zoom_cortes is not None:
        zc = proj["ajustes"].setdefault("zoom_cortes", {"ativo": True, "intensidade": 1.3, "frequencia": 0.35})
        zc["ativo"] = a.zoom_cortes > 1.001
        if zc["ativo"]:
            zc["intensidade"] = a.zoom_cortes
    if a.sons_auto is not None:
        proj["ajustes"]["sons_auto"] = a.sons_auto == "sim"
    if a.enquadramento:
        proj["formato"]["enquadramento"] = a.enquadramento
    if a.sem_legenda:
        proj["legenda"]["ativa"] = False
    P.salvar(a.projeto, proj)
    print("ajustes salvos")


def cmd_status(a):
    P.escrever_estado(a.projeto, claude={"trabalhando": not a.livre, "mensagem": a.mensagem})
    print("ok")


def cmd_resumo(a):
    proj = P.carregar(a.projeto)
    plano = PL.montar_plano(proj)
    motivos = {}
    for p in proj["palavras"]:
        if p.get("cortada"):
            motivos[p.get("motivo", "?")] = motivos.get(p.get("motivo", "?"), 0) + 1
    print(json.dumps({
        "original": fmt_tempo(plano["duracao_original"]),
        "editado": fmt_tempo(plano["duracao_saida"]),
        "cortes": plano["cortes"],
        "palavras": len(proj["palavras"]),
        "palavras_cortadas": motivos,
        "fonte_legenda": proj["legenda"]["visual"].get("fonte"),
        "ritmo": proj["ajustes"]["ritmo"],
        "gancho": proj["gancho"]["texto"] if proj["gancho"]["ativo"] else None,
        "camadas": len(plano["camadas"]),
    }, ensure_ascii=False, indent=1))


def cmd_exportar(a):
    from . import render
    print(render.exportar(a.projeto, previa=a.previa, log=lambda m: print(m, file=sys.stderr)))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="seu-editor", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("novo"); s.add_argument("video"); s.add_argument("--nome"); s.add_argument("--base")
    s.set_defaults(f=cmd_novo)
    s = sub.add_parser("transcrever"); s.add_argument("projeto"); s.add_argument("--modelo", default="large-v3-turbo")
    s.set_defaults(f=cmd_transcrever)
    s = sub.add_parser("servir"); s.add_argument("projeto"); s.add_argument("--porta", type=int, default=4848)
    s.add_argument("--nao-abrir", action="store_true"); s.set_defaults(f=cmd_servir)
    s = sub.add_parser("texto"); s.add_argument("projeto"); s.set_defaults(f=cmd_texto)
    s = sub.add_parser("cortar"); s.add_argument("projeto"); s.add_argument("indices", nargs="+")
    s.add_argument("--motivo", default="claude"); s.set_defaults(f=cmd_cortar)
    s = sub.add_parser("manter"); s.add_argument("projeto"); s.add_argument("indices", nargs="+")
    s.set_defaults(f=cmd_manter)
    s = sub.add_parser("destacar"); s.add_argument("projeto"); s.add_argument("indices", nargs="+")
    s.add_argument("--remover", action="store_true"); s.set_defaults(f=cmd_destacar)
    s = sub.add_parser("gancho"); s.add_argument("projeto"); s.add_argument("texto")
    s.add_argument("--duracao", type=float); s.set_defaults(f=cmd_gancho)
    s = sub.add_parser("sugerir"); s.add_argument("projeto"); s.add_argument("textos", nargs="+")
    s.set_defaults(f=cmd_sugerir)
    s = sub.add_parser("insertos"); s.add_argument("projeto"); s.set_defaults(f=cmd_insertos)
    s = sub.add_parser("camada"); s.add_argument("projeto"); s.add_argument("json"); s.set_defaults(f=cmd_camada)
    s = sub.add_parser("camadas"); s.add_argument("projeto"); s.set_defaults(f=cmd_camadas)
    s = sub.add_parser("remover"); s.add_argument("projeto"); s.add_argument("ids", nargs="+"); s.set_defaults(f=cmd_remover)
    s = sub.add_parser("legenda"); s.add_argument("projeto"); s.add_argument("json"); s.set_defaults(f=cmd_legenda)
    s = sub.add_parser("fonte"); s.add_argument("nome_ou_arquivo"); s.add_argument("--nome"); s.set_defaults(f=cmd_fonte)
    s = sub.add_parser("fontes"); s.set_defaults(f=cmd_fontes)
    s = sub.add_parser("estilo"); s.add_argument("projeto"); s.add_argument("estilo", nargs="?")
    s.add_argument("--destaque"); s.add_argument("--texto"); s.set_defaults(f=cmd_estilo)
    s = sub.add_parser("cor"); s.add_argument("projeto"); s.add_argument("--auto", action="store_true")
    s.add_argument("--sem-auto", action="store_true")
    s.add_argument("--filtro", help="quente-suave, dourado-quente, pessego-vibrante, doc-contraste, neutro-limpo, "
                   "ou natural, dourado, pessego, verao, frio, cinema, filme, suave, pb, nenhum")
    s.add_argument("--intensidade", type=float); s.add_argument("--nitidez", type=float)
    for campo in ("brilho", "contraste", "saturacao", "temperatura"):
        s.add_argument("--" + campo, type=float)
    s.set_defaults(f=cmd_cor)
    s = sub.add_parser("trilha"); s.add_argument("projeto"); s.add_argument("arquivo", nargs="?")
    s.add_argument("--volume", type=float); s.add_argument("--sem-abaixar", action="store_true"); s.set_defaults(f=cmd_trilha)
    s = sub.add_parser("cortar-tempo"); s.add_argument("projeto"); s.add_argument("ini", type=float)
    s.add_argument("fim", type=float, nargs="?", default=0); s.add_argument("--desfazer", action="store_true")
    s.set_defaults(f=cmd_cortar_tempo)
    s = sub.add_parser("buscar-insertos"); s.add_argument("projeto"); s.add_argument("origem")
    s.set_defaults(f=cmd_buscar_insertos)
    s = sub.add_parser("achar-video"); s.add_argument("nome", nargs="?"); s.add_argument("--quantos", type=int, default=5)
    s.set_defaults(f=cmd_achar_video)
    s = sub.add_parser("receitas"); s.set_defaults(f=cmd_receitas)
    s = sub.add_parser("receita-ver"); s.add_argument("nome"); s.set_defaults(f=cmd_receita_ver)
    s = sub.add_parser("receita-salvar"); s.add_argument("nome"); s.add_argument("--projeto")
    s.add_argument("--descricao"); s.add_argument("--regras"); s.add_argument("--sem-visual", action="store_true")
    s.set_defaults(f=cmd_receita_salvar)
    s = sub.add_parser("receita-aplicar"); s.add_argument("projeto"); s.add_argument("nome"); s.set_defaults(f=cmd_receita_aplicar)
    s = sub.add_parser("ajustar"); s.add_argument("projeto")
    s.add_argument("--ritmo", choices=list(P.RITMOS)); s.add_argument("--pausa-max", type=float)
    s.add_argument("--folga", type=float); s.add_argument("--posicao", type=float)
    s.add_argument("--velocidade", type=float); s.add_argument("--zoom-cortes", type=float)
    s.add_argument("--sons-auto", choices=["sim", "nao"])
    s.add_argument("--enquadramento", choices=["preencher", "ajustar"])
    s.add_argument("--sem-legenda", action="store_true"); s.set_defaults(f=cmd_ajustar)
    s = sub.add_parser("status"); s.add_argument("projeto"); s.add_argument("mensagem")
    s.add_argument("--livre", action="store_true"); s.set_defaults(f=cmd_status)
    s = sub.add_parser("resumo"); s.add_argument("projeto"); s.set_defaults(f=cmd_resumo)
    s = sub.add_parser("exportar"); s.add_argument("projeto"); s.add_argument("--previa", action="store_true")
    s.set_defaults(f=cmd_exportar)

    a = ap.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
