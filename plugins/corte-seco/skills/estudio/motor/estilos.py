"""Estilos de legenda e título.

Cada estilo descreve a legenda (texto que acompanha a fala) e o título
(gancho do início e títulos de seção). Os mesmos números alimentam o
render final (ASS/libass) e a prévia ao vivo da interface (CSS), então a
prévia e o vídeo exportado ficam iguais.

Tamanhos estão em pixels de "em" (como no CSS) numa tela de 1080x1920.
Cores aceitam um hex (#RRGGBB) ou um papel da marca: "texto", "destaque".
"""

import os
import struct

PASTA_FONTES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fontes")

# nome que o libass procura -> arquivo .ttf
FONTES = {
    "Poppins Black": "Poppins-Black.ttf",
    "Poppins ExtraBold": "Poppins-ExtraBold.ttf",
    "Poppins SemiBold": "Poppins-SemiBold.ttf",
    "Anton": "Anton-Regular.ttf",
    "DM Serif Display": "DMSerifDisplay-Regular.ttf",
    "DM Serif Display Italic": "DMSerifDisplay-Italic.ttf",
    "Caveat Brush": "CaveatBrush-Regular.ttf",
}

MARCA_PADRAO = {
    "texto": "#FFFFFF",
    "destaque": "#FFD84D",
}

ESTILOS = [
    {
        "id": "pop",
        "nome": "Pop",
        "descricao": "Caixa alta e grossa, a palavra falada acende na cor de destaque.",
        "legenda": {
            "fonte": "Poppins Black", "tamanho": 64, "caixa_alta": True,
            "cor": "texto", "cor_ativa": "destaque", "cor_destaque": "destaque",
            "contorno": 7, "cor_contorno": "#000000", "sombra": 4,
            "caixa": None, "karaoke": True, "animacao": "pop", "rotacao": 0,
            "palavras": 3, "max_letras": 16,
        },
        "titulo": {
            "fonte": "Poppins ExtraBold", "tamanho": 54, "caixa_alta": False,
            "cor": "#111111", "caixa": "#FFFFFF", "contorno": 22,
            "cor_contorno": "#FFFFFF", "sombra": 0, "animacao": "pop", "rotacao": 0,
        },
    },
    {
        "id": "caixinha",
        "nome": "Caixinha",
        "descricao": "Texto escuro em etiqueta clara, a palavra falada ganha a etiqueta colorida.",
        "legenda": {
            "fonte": "Poppins ExtraBold", "tamanho": 52, "caixa_alta": False,
            "cor": "#111111", "cor_ativa": "#111111", "cor_destaque": "#111111",
            "contorno": 14, "cor_contorno": "#FFFFFF", "sombra": 0,
            "caixa": "#FFFFFF", "caixa_ativa": "destaque", "caixa_destaque": "destaque",
            "karaoke": True, "animacao": "pop", "rotacao": 0,
            "palavras": 3, "max_letras": 20,
        },
        "titulo": {
            "fonte": "Poppins Black", "tamanho": 58, "caixa_alta": True,
            "cor": "#111111", "caixa": "destaque", "contorno": 22,
            "cor_contorno": "destaque", "sombra": 0, "animacao": "pop", "rotacao": 0,
        },
    },
    {
        "id": "editorial",
        "nome": "Editorial",
        "descricao": "Serifa elegante sem caixa alta, destaques em itálico colorido.",
        "legenda": {
            "fonte": "DM Serif Display", "tamanho": 66, "caixa_alta": False,
            "cor": "texto", "cor_ativa": "texto", "cor_destaque": "destaque",
            "italico_destaque": True,
            "contorno": 0, "cor_contorno": "#000000", "sombra": 3,
            "caixa": None, "karaoke": False, "animacao": "fade", "rotacao": 0,
            "palavras": 4, "max_letras": 24,
        },
        "titulo": {
            "fonte": "DM Serif Display Italic", "tamanho": 84, "caixa_alta": False,
            "cor": "texto", "caixa": None, "contorno": 0,
            "cor_contorno": "#000000", "sombra": 4, "animacao": "fade", "rotacao": 0,
        },
    },
    {
        "id": "manuscrito",
        "nome": "Manuscrito",
        "descricao": "Letra de pincel levemente inclinada, com cara de anotação à mão.",
        "legenda": {
            "fonte": "Caveat Brush", "tamanho": 82, "caixa_alta": False,
            "cor": "texto", "cor_ativa": "destaque", "cor_destaque": "destaque",
            "contorno": 4, "cor_contorno": "#000000", "sombra": 3,
            "caixa": None, "karaoke": True, "animacao": "pop", "rotacao": -3,
            "palavras": 3, "max_letras": 20,
        },
        "titulo": {
            "fonte": "Caveat Brush", "tamanho": 104, "caixa_alta": False,
            "cor": "destaque", "caixa": None, "contorno": 5,
            "cor_contorno": "#000000", "sombra": 4, "animacao": "pop", "rotacao": -4,
        },
    },
    {
        "id": "impacto",
        "nome": "Impacto",
        "descricao": "Letra condensada enorme, uma ou duas palavras por vez.",
        "legenda": {
            "fonte": "Anton", "tamanho": 112, "caixa_alta": True,
            "cor": "texto", "cor_ativa": "texto", "cor_destaque": "destaque",
            "contorno": 6, "cor_contorno": "#000000", "sombra": 5,
            "caixa": None, "karaoke": False, "animacao": "pop", "rotacao": 0,
            "palavras": 2, "max_letras": 12,
        },
        "titulo": {
            "fonte": "Anton", "tamanho": 96, "caixa_alta": True,
            "cor": "destaque", "caixa": None, "contorno": 6,
            "cor_contorno": "#000000", "sombra": 5, "animacao": "pop", "rotacao": 0,
        },
    },
]


def estilo_por_id(eid):
    for e in ESTILOS:
        if e["id"] == eid:
            return e
    return ESTILOS[0]


def resolver_cor(valor, marca):
    """Troca papéis ("texto", "destaque") pela cor da marca."""
    if valor is None:
        return None
    if valor.startswith("#"):
        return valor.upper()
    m = dict(MARCA_PADRAO)
    m.update({k: v for k, v in (marca or {}).items() if v})
    return m.get(valor, "#FFFFFF").upper()


_metricas_cache = {}


def fator_ass(fonte):
    """Quanto o tamanho em px (em) precisa ser multiplicado pra virar tamanho ASS.

    O libass dimensiona a fonte pela altura total (ascendente + descendente
    do OS/2), enquanto o CSS dimensiona pelo em. Lemos as métricas direto do
    arquivo pra converter sem depender de bibliotecas extras.
    """
    if fonte in _metricas_cache:
        return _metricas_cache[fonte]
    fator = 1.0
    try:
        with open(os.path.join(PASTA_FONTES, FONTES[fonte]), "rb") as f:
            dados = f.read()
        num_tabelas = struct.unpack(">H", dados[4:6])[0]
        tabelas = {}
        for i in range(num_tabelas):
            reg = dados[12 + 16 * i: 28 + 16 * i]
            tag = reg[:4].decode("latin-1")
            tabelas[tag] = struct.unpack(">I", reg[8:12])[0]
        upm = struct.unpack(">H", dados[tabelas["head"] + 18: tabelas["head"] + 20])[0]
        os2 = tabelas["OS/2"]
        win_asc, win_desc = struct.unpack(">HH", dados[os2 + 74: os2 + 78])
        if win_asc + win_desc > 0:
            fator = (win_asc + win_desc) / upm
    except Exception:
        fator = 1.0
    _metricas_cache[fonte] = fator
    return fator


def estilos_para_interface():
    saida = []
    for e in ESTILOS:
        saida.append(dict(e))
    fontes = {nome: {"arquivo": arq, "fator_ass": fator_ass(nome)} for nome, arq in FONTES.items()}
    return {"estilos": saida, "fontes": fontes, "marca_padrao": MARCA_PADRAO}
