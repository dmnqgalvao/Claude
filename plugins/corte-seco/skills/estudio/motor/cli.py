"""Linha de comando do Corte Seco. É por aqui que o Claude mexe no projeto.

Uso: python -m motor.cli <comando> ...   (rodar de dentro da pasta da skill)

Comandos:
  novo VIDEO [--nome N] [--base PASTA]      cria o projeto e mostra a pasta dele
  transcrever PROJETO [--modelo M]          transcreve com o tempo de cada palavra
  servir PROJETO [--porta P] [--nao-abrir]  abre a interface no navegador
  texto PROJETO                             mostra a transcrição numerada
  cortar PROJETO 12-18 25 [--motivo M]      corta palavras (intervalos de índices)
  manter PROJETO 12-18                      desfaz o corte dessas palavras
  destacar PROJETO 30 41-42 [--remover]     marca palavras de destaque na legenda
  gancho PROJETO "texto" [--duracao 3]      define o gancho escrito do início
  sugerir PROJETO "gancho 1" "gancho 2"...  deixa sugestões de gancho na interface
  titulo PROJETO PALAVRA "texto" [--duracao 2]   título de seção a partir de uma palavra
  ajustar PROJETO [--ritmo R] [--estilo E] [--destaque #hex] [--texto #hex] ...
  status PROJETO "mensagem" [--livre]       mostra o que o Claude está fazendo
  resumo PROJETO                            números do projeto
  exportar PROJETO [--previa]               gera o mp4
"""

import argparse
import json
import os
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "motor"

from . import estilos as E          # noqa: E402
from . import plano as PL           # noqa: E402
from . import projeto as P          # noqa: E402


def dados_dir():
    d = os.environ.get("CORTE_SECO_DADOS") or os.path.join(os.path.expanduser("~"), ".corte-seco")
    os.makedirs(d, exist_ok=True)
    return d


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
    if not os.path.exists(a.video):
        sys.exit(f"vídeo não encontrado: {a.video}")
    nome = a.nome or os.path.splitext(os.path.basename(a.video))[0]
    base = a.base or os.path.join(os.getcwd(), "corte-seco")
    pasta = os.path.join(base, re.sub(r"[^\w\-]+", "-", nome.lower()).strip("-") or "video")
    sufixo, original = 2, pasta
    while os.path.exists(pasta):
        pasta = f"{original}-{sufixo}"
        sufixo += 1
    os.makedirs(pasta)
    P.salvar(pasta, P.projeto_padrao(a.video, nome, marca_global()))
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


def cmd_titulo(a):
    proj = P.carregar(a.projeto)
    proj["titulos"] = [t for t in proj.get("titulos", []) if t.get("palavra") != a.palavra]
    if a.texto.strip():
        proj["titulos"].append({"palavra": a.palavra, "texto": a.texto.strip(), "duracao": a.duracao})
        proj["titulos"].sort(key=lambda t: t["palavra"])
    P.salvar(a.projeto, proj)
    print("título salvo" if a.texto.strip() else "título removido")


def cmd_ajustar(a):
    proj = P.carregar(a.projeto)
    if a.ritmo:
        proj["ajustes"]["ritmo"] = a.ritmo
        proj["ajustes"].update(P.RITMOS[a.ritmo])
    if a.pausa_max is not None:
        proj["ajustes"].update(pausa_max=a.pausa_max, ritmo="personalizado")
    if a.folga is not None:
        proj["ajustes"].update(folga=a.folga, ritmo="personalizado")
    if a.estilo:
        proj["legenda"]["estilo"] = a.estilo
    if a.palavras:
        proj["legenda"]["palavras"] = a.palavras
    if a.posicao is not None:
        proj["legenda"]["posicao"] = a.posicao
    if a.destaque:
        proj["marca"]["destaque"] = a.destaque
    if a.texto:
        proj["marca"]["texto"] = a.texto
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
        "estilo": proj["legenda"]["estilo"],
        "ritmo": proj["ajustes"]["ritmo"],
        "gancho": proj["gancho"]["texto"] if proj["gancho"]["ativo"] else None,
        "titulos": len(plano["titulos"]),
    }, ensure_ascii=False, indent=1))


def cmd_exportar(a):
    from . import render
    print(render.exportar(a.projeto, previa=a.previa))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="corte-seco", description=__doc__,
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
    s = sub.add_parser("titulo"); s.add_argument("projeto"); s.add_argument("palavra", type=int)
    s.add_argument("texto"); s.add_argument("--duracao", type=float, default=2.0); s.set_defaults(f=cmd_titulo)
    s = sub.add_parser("ajustar"); s.add_argument("projeto")
    s.add_argument("--ritmo", choices=list(P.RITMOS)); s.add_argument("--pausa-max", type=float)
    s.add_argument("--folga", type=float); s.add_argument("--estilo", choices=[e["id"] for e in E.ESTILOS])
    s.add_argument("--palavras", type=int); s.add_argument("--posicao", type=float)
    s.add_argument("--destaque"); s.add_argument("--texto")
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
