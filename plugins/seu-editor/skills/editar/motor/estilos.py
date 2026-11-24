"""Fontes, visuais de texto e camadas.

Todo texto na tela (legenda, gancho, palavra de impacto, texto fixo) usa
o mesmo "visual": fonte, tamanho, cor, contorno, sombra, brilho e fundo.
A pessoa monta o visual que quiser na interface, e os PONTOS_DE_PARTIDA
são só atalhos com os visuais mais usados em Reels e TikTok.

A prévia e a exportação usam o mesmo desenhista em HTML (app/motion.js),
então o que aparece na prévia sai igual no vídeo.

Fontes: primeiro tenta a fonte do sistema (Helvetica, Impact, Bradley
Hand, Futura e Bodoni 72 vêm no Mac), e se ela não existir usa uma fonte
aberta parecida que vem junto com o plugin.
"""

import os

PASTA_FONTES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fontes")

# id -> como aparece na lista, pilha de fontes do CSS, peso e largura média
# de uma letra (em fração do tamanho) pra calcular quantas letras cabem.
FONTES = {
    "sfpro":      {"nome": "SF Pro Display Bold", "familia": '-apple-system, "SF Pro Display", system-ui, "Inter Tight"', "peso": 700, "largura": .55},
    # Alte Haas Grotesk (gratuita, de Yann Le Coroller): usa a instalada no computador;
    # sem ela, cai na Arimo (mesma família de desenho) um pouco mais apertada
    "altehaas":   {"nome": "Alte Haas Grotesk Bold", "familia": '"Alte Haas Grotesk", "AlteHaasGrotesk", "Alte Haas Grotesk Bold", "Helvetica Neue", "Arimo"', "peso": 700, "largura": .55, "tracking": -2},
    "bootzy":     {"nome": "Bootzy TM", "familia": '"Bootzy TM", "Bootzy", "Inter Tight"', "peso": 800, "largura": .5, "tracking": -4},
    "opensauce":  {"nome": "Open Sauce", "familia": '"Open Sauce Sans", "Open Sauce", "Open Sauce One"', "peso": 400, "largura": .54},
    "opensauce-bold": {"nome": "Open Sauce Bold", "familia": '"Open Sauce Sans", "Open Sauce", "Open Sauce One"', "peso": 700, "largura": .57},
    "courier":    {"nome": "Courier New Bold", "familia": '"Courier New", Courier, "Courier Prime"', "peso": 700, "largura": .6},
    "condensada": {"nome": "Condensada (Oswald)", "familia": '"Oswald"', "peso": 600, "largura": .42},
    "instrument": {"nome": "Instrument Serif", "familia": '"Instrument Serif"', "peso": 400, "largura": .42},
    "helvetica":  {"nome": "Helvetica Bold", "familia": '"Helvetica Neue", Helvetica, "Arimo"', "peso": 700, "largura": .56},
    "helvetica-regular": {"nome": "Helvetica", "familia": '"Helvetica Neue", Helvetica, "Arimo"', "peso": 400, "largura": .53},
    "times":      {"nome": "Times New Roman", "familia": '"Times New Roman", Times, "Tinos"', "peso": 400, "largura": .46},
    "chalkduster": {"nome": "Chalkduster", "familia": 'Chalkduster, "Cabin Sketch"', "peso": 700, "largura": .6},
    "burgues":    {"nome": "Burgues Script", "familia": '"Burgues Script", "Pinyon Script"', "peso": 400, "largura": .45},
    "futura":     {"nome": "Futura", "familia": 'Futura, "Jost"', "peso": 500, "largura": .53},
    "opensans":   {"nome": "Open Sans", "familia": '"Open Sans"', "peso": 600, "largura": .55},
    "bricolage":  {"nome": "Bricolage Grotesque Bold", "familia": '"Bricolage Grotesque"', "peso": 700, "largura": .55},
    "spacemono":  {"nome": "Space Mono", "familia": '"Space Mono"', "peso": 400, "largura": .62},
    "impact":     {"nome": "Impact", "familia": 'Impact, "Anton"', "peso": 400, "largura": .48},
    "pincel":     {"nome": "Pincel (Bradley Hand)", "familia": '"Bradley Hand", "Caveat Brush"', "peso": 700, "largura": .5},
    "bebas":      {"nome": "Bebas Neue", "familia": '"Bebas Neue"', "peso": 400, "largura": .4},
    "bodoni":     {"nome": "Bodoni", "familia": '"Bodoni 72", "Bodoni Moda"', "peso": 500, "largura": .5},
    "montserrat": {"nome": "Montserrat Black", "familia": '"Montserrat"', "peso": 900, "largura": .66},
    "poppins":    {"nome": "Poppins ExtraBold", "familia": '"Poppins"', "peso": 800, "largura": .62},
    "serifa":     {"nome": "DM Serif Display", "familia": '"DM Serif Display"', "peso": 400, "largura": .5},
    "marcador":   {"nome": "Marcador", "familia": '"Permanent Marker"', "peso": 400, "largura": .58},
    "maquina":    {"nome": "Máquina de escrever", "familia": '"American Typewriter", "Courier Prime"', "peso": 700, "largura": .6},
}

# Estilos = dupla de fontes. "destaque" vale pra gancho, títulos e palavras
# de impacto; "texto" vale pra legenda, frases e botões. Cores, contorno e
# fundo continuam livres por cima de qualquer estilo.
KITS = [
    {"id": "cool", "nome": "cool", "destaque": "bootzy", "texto": "helvetica-regular"},
    {"id": "star", "nome": "star", "destaque": "opensauce-bold", "texto": "courier"},
    {"id": "basic", "nome": "basic", "destaque": "condensada", "texto": "futura"},
    {"id": "glow", "nome": "glow", "destaque": "helvetica", "texto": "instrument"},
    {"id": "domi", "nome": "domi", "destaque": "altehaas", "texto": "opensauce"},
]
KIT_PADRAO = KITS[0]

PALETA_PADRAO = ["#FFFFFF", "#000000", "#FFD84D", "#FB76B2", "#C2366F", "#2B2B2B", "#C98A4B", "#7CE0B5"]

# visual completo de um texto; toda camada de texto guarda um destes
VISUAL_PADRAO = {
    "fonte": "@texto", "tamanho": 64, "cor": "#FFFFFF", "caixa_alta": False, "italico": False,
    "contorno": True, "espessura": 6, "cor_contorno": "#000000",
    "sombra": True, "brilho": False, "fundo": "nenhum", "cor_fundo": "#FFFFFF",
    "entrelinhas": 1.14,         # altura da linha, em múltiplos do tamanho da letra
    "espacamento": 0,            # espaço entre letras, em centésimos do tamanho (-10 a 40)
}

# Legenda no padrão das edições de referência (análise dos projetos do CapCut):
# 2 a 3 palavras, uma linha, minúsculas, sem pontuação, branca pequena com sombra
# leve no terço de baixo, fade em cada bloco. O destaque SUBSTITUI a legenda:
# a palavra sai do fluxo e aparece sozinha, ~1,8x maior, na fonte de destaque.
LEGENDA_PADRAO = {
    **VISUAL_PADRAO,
    "tamanho": 52, "contorno": True, "espessura": 2.5, "cor_contorno": "#292929", "sombra": True,
    "minusculas": True,
    "max_caracteres": 22,
    "cor_destaque": "#FFFFFF",   # cor da palavra destacada (ou falada, no modo "cor")
    "cor_destaque2": "#FFFFFF",  # segunda cor, alternada com a primeira
    "fonte_destaque": "@destaque",
    "fonte_destaque2": None,     # segunda fonte de destaque, alternada (ex.: serifa e manuscrita)
    "escala_destaque": 1.8,
    "modo_destaque": "substitui",  # substitui | cor
    "modo_ativa": "nenhum",      # palavra falada: cor | fundo | nenhum
    "animacao": "fade",          # pop | fade | nenhuma
    "palavras": 3,
}

# Título-gancho: frase inteira em caixa sólida na cor da marca, no terço de cima, por 5 a 6 s.
GANCHO_PADRAO = {
    **VISUAL_PADRAO, "fonte": "@destaque", "tamanho": 58, "cor": "#FFFFFF",
    "contorno": False, "sombra": False, "fundo": "caixa", "cor_fundo": "#C2366F", "entrelinhas": 1.2,
}

# Modelos de abertura (gancho escrito). O visual de cada um é aplicado por cima do visual
# do gancho do projeto, só nos campos que o modelo define; a fonte é sempre a de destaque
# do estilo e a linha pequena/etiqueta usa a fonte de texto.
MODELOS_GANCHO = {
    "caixa": {"nome": "caixa colorida", "posicao": 0.24, "duracao": 5.5, "visual": {}},
    "texto": {"nome": "só texto", "posicao": 0.64, "duracao": 5.0,
              "visual": {"fundo": "nenhum", "tamanho": 96, "caixa_alta": True, "sombra": True, "brilho": False,
                         "entrelinhas": 1.0, "cor": "#FFFFFF"}},
    "rosto": {"nome": "na frente do rosto", "posicao": 0.5, "duracao": 2.0,
              "visual": {"fundo": "nenhum", "tamanho": 124, "caixa_alta": False, "sombra": True,
                         "entrelinhas": 1.05, "cor": "#FFFFFF"}},
    "imagens": {"nome": "imagens atrás de você", "posicao": 0.31, "duracao": 4.2,
                "visual": {"fundo": "nenhum", "tamanho": 92, "caixa_alta": True, "sombra": True,
                           "entrelinhas": 1.0, "cor": "#FFFFFF"}},
    "icones": {"nome": "texto com ícones", "posicao": 0.2, "duracao": 4.5,
               "visual": {"fundo": "nenhum", "tamanho": 86, "caixa_alta": False, "sombra": True,
                          "entrelinhas": 1.0, "cor": "#FFFFFF"}},
    "palavras": {"nome": "palavra por palavra", "posicao": 0.27, "duracao": 3.0,
                 "visual": {"fundo": "nenhum", "tamanho": 62, "caixa_alta": False, "sombra": True,
                            "contorno": False, "cor": "#FFFFFF"}},
}
# (x, y, largura, giro) das fotos do modelo "imagens": 2 em cima, 2 dos lados, 2 embaixo
LUGARES_FOTOS_GANCHO = [(.25, .15, .3, -6), (.75, .15, .3, 5), (.13, .46, .26, -4),
                        (.87, .46, .26, 4), (.27, .79, .26, 3), (.73, .79, .26, -3)]
ICONES_GANCHO = ["estrela", "brilho", "estrela-contorno", "coracao", "nuvem", "raio", "seta", "circulo"]


def visual_gancho(g, fontes_proj):
    return resolver_fonte(visual_completo(GANCHO_PADRAO, (g or {}).get("visual")), fontes_proj)


def aplicar_modelo_gancho(g, modelo):
    """Troca o modelo da abertura: posição, tempo e formato do texto vêm do modelo; a fonte
    continua a de destaque do estilo e as cores que a pessoa escolheu ficam."""
    m = MODELOS_GANCHO[modelo]
    g["modelo"] = modelo
    g["posicao"] = m["posicao"]
    g["duracao"] = m["duracao"]
    v = dict(g.get("visual") or {})
    cor = v.get("cor")
    if modelo == "caixa":
        v.update({k: GANCHO_PADRAO[k] for k in ("fundo", "tamanho", "caixa_alta", "sombra", "entrelinhas")})
    else:
        v.update(m["visual"])
        if cor and cor.upper() not in ("#FFFFFF",):
            v["cor"] = cor
    g["visual"] = v
    return g


# Palavra de impacto: a palavra falada aparece grande, presa ao momento da fala.
IMPACTO = {
    "pincel":     {"nome": "pincel com brilho", "entrada": "escreve", "rotacao": -4,
                   "visual": {"fonte": "pincel", "tamanho": 150, "entrelinhas": 1.0, "cor": "#E8352E", "contorno": False, "sombra": False, "brilho": True}},
    "condensado": {"nome": "condensado grande", "entrada": "pop", "rotacao": 0,
                   "visual": {"fonte": "impact", "tamanho": 190, "entrelinhas": 1.0, "cor": "#F6EFD9", "caixa_alta": True, "contorno": False, "sombra": True}},
    "estilo":     {"nome": "fonte de destaque do estilo", "entrada": "desliza", "rotacao": 0,
                   "visual": {"fonte": "@destaque", "tamanho": 150, "entrelinhas": 1.0, "cor": "#FFFFFF", "italico": True, "contorno": False, "sombra": True}},
    "etiqueta":   {"nome": "etiqueta colorida", "entrada": "pop", "rotacao": -2,
                   "visual": {"fonte": "montserrat", "tamanho": 96, "entrelinhas": 1.0, "cor": "#111111", "caixa_alta": True, "contorno": False,
                              "sombra": False, "fundo": "caixa", "cor_fundo": "#FFD84D"}},
}

# Textos fixos: título, frase, apoio, botão de chamada.
TEXTOS = {
    "titulo":   {"nome": "título", "entrada": "fade",
                 "visual": {"fonte": "@destaque", "tamanho": 80, "cor": "#FFFFFF", "contorno": False, "sombra": True}},
    "frase":    {"nome": "frase", "entrada": "fade",
                 "visual": {"fonte": "@texto", "tamanho": 54, "cor": "#FFFFFF", "contorno": False, "sombra": True}},
    "apoio":    {"nome": "texto de apoio", "entrada": "fade",
                 "visual": {"fonte": "@texto", "tamanho": 38, "cor": "#FFFFFF", "contorno": False, "sombra": True}},
    "cta":      {"nome": "botão de chamada", "entrada": "pop",
                 "visual": {"fonte": "@texto", "tamanho": 40, "cor": "#111111", "contorno": False, "sombra": False,
                            "fundo": "pilula", "cor_fundo": "#FFFFFF"}},
    "etiqueta": {"nome": "etiqueta", "entrada": "pop",
                 "visual": {"fonte": "montserrat", "tamanho": 50, "cor": "#111111", "caixa_alta": True, "contorno": False,
                            "sombra": False, "fundo": "caixa", "cor_fundo": "#FFD84D"}},
    "anotacao": {"nome": "anotação à mão", "entrada": "escreve", "rotacao": -3,
                 "visual": {"fonte": "pincel", "tamanho": 84, "cor": "#FFD84D", "contorno": False, "sombra": True}},
}

# Cascata: palavras-chave que entram uma por uma, empilhadas, e saem juntas.
CASCATA = {
    "padrao": {"nome": "cascata", "entrada": "desliza",
               "visual": {"fonte": "@destaque", "tamanho": 100, "cor": "#FFFFFF", "caixa_alta": True,
                          "contorno": False, "sombra": True, "entrelinhas": 1.0}},
}

DESENHOS = {
    "circulo": {"nome": "círculo"},
    "seta": {"nome": "seta"},
    "sublinhado": {"nome": "sublinhado"},
    "x": {"nome": "xis"},
    "brilho": {"nome": "brilhinho"},
}

ENTRADAS = ["pop", "desliza", "fade", "escreve", "nenhuma"]


def resolver_fonte(visual, fontes_proj):
    """Troca "@destaque"/"@texto" pela fonte do estilo escolhido no projeto."""
    f = visual.get("fonte") or "@texto"
    if f.startswith("@"):
        papel = f[1:]
        visual["fonte"] = (fontes_proj or {}).get(papel) or KIT_PADRAO.get(papel, "helvetica")
    return visual


def fontes_da_pessoa(dados):
    """Fontes enviadas pela pessoa ou baixadas pelo Claude (~/.seu-editor/fontes)."""
    import json
    try:
        with open(os.path.join(dados, "fontes", "fontes.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def todas_as_fontes(dados=None):
    tudo = dict(FONTES)
    if dados:
        tudo.update(fontes_da_pessoa(dados))
    return tudo


def visual_completo(base, *extras):
    v = dict(VISUAL_PADRAO)
    v.update(base or {})
    for e in extras:
        v.update({k: val for k, val in (e or {}).items() if val is not None})
    return v


def max_letras(visual, largura_util=900):
    f = FONTES.get(visual.get("fonte")) or {"largura": .56}
    tam = float(visual.get("tamanho", 64))
    fator = f["largura"] * (1.08 if visual.get("caixa_alta") else 1.0)
    return max(6, int(largura_util / (tam * fator)))


def estilos_para_interface(dados=None):
    return {
        "fontes": todas_as_fontes(dados), "kits": KITS, "paleta": PALETA_PADRAO,
        "visual_padrao": VISUAL_PADRAO, "legenda_padrao": LEGENDA_PADRAO, "gancho_padrao": GANCHO_PADRAO,
        "impacto": IMPACTO, "textos": TEXTOS, "cascata": CASCATA, "desenhos": DESENHOS, "entradas": ENTRADAS,
        "filtros_cor": _filtros_cor(dados), "sons": sons_disponiveis(dados),
        "sons_mapa": SONS_MAPA, "sons_momentos": SONS_MOMENTOS,
        "modelos_gancho": MODELOS_GANCHO,
        "icones_gancho": ICONES_GANCHO,
    }


SONS = {"pop": "pop", "clique": "clique", "camera": "camera", "whoosh": "whoosh", "ding": "ding",
        "impacto": "impacto", "subida": "subida"}
EXT_SONS = (".wav", ".mp3", ".m4a", ".aac", ".ogg")

# qual som entra em cada momento quando os sons automáticos estão ligados
# (destaque alterna entre os dois da lista)
SONS_MAPA = {"destaque": ["pop", "clique"], "palavra": "pop", "texto": "clique", "foto": "camera",
             "cta": "pop", "volume": 1.0}
SONS_MOMENTOS = [("destaque", "palavra em destaque na legenda"), ("palavra", "palavra-chave grande e cascata"),
                 ("texto", "texto na tela"), ("foto", "foto ou vídeo que entra"), ("cta", "botão de chamada")]


def pasta_sons():
    import os
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sons")


def sons_disponiveis(dados=None):
    """nome -> url. Os sons da pessoa (~/.seu-editor/sons) ficam junto dos que vêm no plugin."""
    import os
    sons = {k: f"/sons/{k}.wav" for k in SONS}
    pasta = os.path.join(dados, "sons") if dados else None
    if pasta and os.path.isdir(pasta):
        for nome in sorted(os.listdir(pasta)):
            base, ext = os.path.splitext(nome)
            if ext.lower() in EXT_SONS:
                sons[base] = f"/sons-pessoa/{nome}"
    return sons


def arquivo_do_som(nome, dados=None, pasta_projeto=None):
    import os
    if not nome:
        return None
    candidatos = [os.path.join(pasta_sons(), nome + ".wav")]
    if dados:
        candidatos += [os.path.join(dados, "sons", nome + e) for e in EXT_SONS] + [os.path.join(dados, "sons", nome)]
    if pasta_projeto:
        candidatos.append(os.path.join(pasta_projeto, "insertos", nome))
    return next((c for c in candidatos if os.path.isfile(c)), None)


def _filtros_cor(dados=None):
    from .cor import looks_para_interface
    return looks_para_interface(dados)
