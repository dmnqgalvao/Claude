"""Receitas de edição: jeitos de editar com nome, pra repetir em outros vídeos.

Uma receita guarda duas coisas:
- o visual que dá pra aplicar direto no projeto (fontes, legenda, gancho,
  ritmo dos cortes, cor, enquadramento, cores da marca);
- as regras em texto, que o Claude segue ao montar a edição (quantas
  palavras de impacto, quando usar zoom, que tipo de gancho, sons...).

Ficam em ~/.seu-editor/receitas/<nome>.json e servem pra todos os projetos.
"""

import json
import os
import re
import time

CAMPOS = {
    "fontes": lambda p: p.get("fontes"),
    "legenda_visual": lambda p: p.get("legenda", {}).get("visual"),
    "legenda_posicao": lambda p: p.get("legenda", {}).get("posicao"),
    "legenda_sem_pontuacao": lambda p: p.get("legenda", {}).get("sem_pontuacao"),
    "gancho_visual": lambda p: p.get("gancho", {}).get("visual"),
    "gancho_posicao": lambda p: p.get("gancho", {}).get("posicao"),
    "gancho_duracao": lambda p: p.get("gancho", {}).get("duracao"),
    "ajustes": lambda p: p.get("ajustes"),
    "cor": lambda p: {k: v for k, v in (p.get("cor") or {}).items()
                      if k not in ("ganhos", "auto_brilho", "auto_contraste")},
    "formato": lambda p: p.get("formato"),
    "cores_marca": lambda p: p.get("marca", {}).get("cores"),
}


def _pasta(dados):
    p = os.path.join(dados, "receitas")
    os.makedirs(p, exist_ok=True)
    return p


def _slug(nome):
    s = re.sub(r"[^\w\-]+", "-", nome.lower()).strip("-")
    return s or "receita"


def listar(dados):
    itens = []
    for arq in sorted(os.listdir(_pasta(dados))):
        if arq.endswith(".json"):
            try:
                with open(os.path.join(_pasta(dados), arq), encoding="utf-8") as f:
                    r = json.load(f)
                itens.append({"id": arq[:-5], "nome": r.get("nome", arq[:-5]), "descricao": r.get("descricao", ""),
                              "regras": r.get("regras", "")})
            except (OSError, ValueError):
                continue
    return itens


def ler(dados, nome):
    caminho = os.path.join(_pasta(dados), _slug(nome) + ".json")
    if not os.path.exists(caminho):
        # aceita o nome com acento ou parte dele
        for r in listar(dados):
            if _slug(nome) in r["id"] or nome.lower() in r["nome"].lower():
                caminho = os.path.join(_pasta(dados), r["id"] + ".json")
                break
        else:
            raise LookupError(f"não existe receita '{nome}'")
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def salvar(dados, nome, proj=None, descricao="", regras="", juntar=True):
    """Cria ou atualiza. Com proj, guarda o visual dele. Regras novas substituem as antigas."""
    caminho = os.path.join(_pasta(dados), _slug(nome) + ".json")
    atual = {}
    if juntar and os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            atual = json.load(f)
    atual["nome"] = nome
    if descricao:
        atual["descricao"] = descricao
    if regras:
        atual["regras"] = regras
    if proj is not None:
        atual["aplicar"] = {k: f(proj) for k, f in CAMPOS.items() if f(proj) is not None}
    atual["atualizada"] = time.strftime("%Y-%m-%d %H:%M")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(atual, f, ensure_ascii=False, indent=1)
    return _slug(nome)


def aplicar(proj, receita):
    a = receita.get("aplicar") or {}
    if a.get("fontes"):
        proj["fontes"] = dict(a["fontes"])
    if a.get("legenda_visual"):
        proj["legenda"]["visual"].update(a["legenda_visual"])
    for campo, chave in (("legenda_posicao", "posicao"), ("legenda_sem_pontuacao", "sem_pontuacao")):
        if a.get(campo) is not None:
            proj["legenda"][chave] = a[campo]
    if a.get("gancho_visual"):
        proj["gancho"]["visual"].update(a["gancho_visual"])
    for campo, chave in (("gancho_posicao", "posicao"), ("gancho_duracao", "duracao")):
        if a.get(campo) is not None:
            proj["gancho"][chave] = a[campo]
    if a.get("ajustes"):
        proj["ajustes"].update(a["ajustes"])
    if a.get("cor"):
        auto = proj["cor"].get("auto")
        proj["cor"].update(a["cor"])
        if a["cor"].get("auto") and not auto:
            proj["cor"]["auto_pendente"] = True   # o Claude roda `cor --auto` depois
    if a.get("formato"):
        proj["formato"].update(a["formato"])
    if a.get("cores_marca"):
        proj["marca"]["cores"] = list(a["cores_marca"])
    proj["receita"] = receita.get("nome")
    return proj
