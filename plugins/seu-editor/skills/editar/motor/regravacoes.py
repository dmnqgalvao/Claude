"""Acha regravações e gaguejos na transcrição e marca o trecho errado como cortado.

Regravação: a pessoa começa uma frase, erra, e fala de novo. A segunda tentativa repete
o começo da primeira. O detector procura um trecho de 3 ou mais palavras que aparece duas
vezes perto, alinha as duas tentativas pelo começo (volta palavra por palavra enquanto
elas forem iguais) e corta tudo da primeira tentativa até logo antes da segunda.

Exemplo: "se você tá enrolando desde o começo do ano ... ainda em | se você tá enrolando
desde o começo do ano ... ainda em 2026" -> corta a primeira tentativa inteira.

Gaguejo: palavra repetida em seguida ("a a", "eu eu") e palavra cortada no meio que vira
a próxima ("pro produzir").

Nunca mexe em palavra que a pessoa marcou à mão (origem "voce").
"""

import re

PEQUENAS = {
    "a", "o", "as", "os", "e", "é", "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
    "um", "uma", "que", "se", "pra", "pro", "por", "com", "eu", "você", "vc", "ele", "ela", "isso",
    "esse", "essa", "tá", "ta", "não", "nao", "mas", "aí", "ai", "então", "tipo", "né", "ne", "já",
}
# palavras que a pessoa repete de propósito
ENFASE = {"muito", "nada", "não", "nao", "sim", "bem", "super", "tão", "tchau", "olha", "vai", "corre"}

MULETAS = {"é", "e", "eh", "tipo", "né", "ne", "assim", "digo", "aliás", "ou", "quer", "dizer", "não", "nao", "pera", "peraí"}
FIM_FRASE = re.compile(r"[.!?…]$")

MOTIVO = "regravação"
MOTIVO_GAGUEJO = "gaguejo"


def _norm(t):
    return re.sub(r"[^\wÀ-ÿ]", "", (t or "").strip().lower())


def _marcar(p, motivo):
    if p.get("origem") == "voce" or p.get("cortada"):
        return False
    p.update(cortada=True, motivo=motivo, origem="auto")
    return True


def detectar(palavras, janela_palavras=60, janela_s=30.0, minimo=3):
    """Marca regravações e gaguejos. Devolve [(motivo, i_ini, i_fim, texto)] do que cortou."""
    # compara a fala inteira (inclusive o que já foi cortado), menos as hesitações,
    # pra alinhar as tentativas pelo começo de verdade
    seq = [p for p in palavras if p.get("motivo") != "hesitação"]
    tok = [_norm(p["t"]) for p in seq]
    achados = []

    # 1. regravações
    j = 1
    while j < len(seq):
        melhor = None
        for i in range(max(0, j - janela_palavras), j):
            if seq[j]["ini"] - seq[i]["ini"] > janela_s or tok[i] != tok[j] or not tok[i]:
                continue
            k = 0
            while j + k < len(seq) and i + k < j and tok[i + k] == tok[j + k]:
                k += 1
            significativas = sum(1 for x in tok[j:j + k] if x not in PEQUENAS)
            precisa = minimo if j - i <= 25 else minimo + 1
            if k >= precisa and significativas >= 2 and (melhor is None or k > melhor[1]):
                melhor = (i, k)
        if melhor:
            i, k = melhor
            a, b = i, j
            while a > 0 and b - 1 > a and tok[a - 1] == tok[b - 1] and tok[a - 1]:
                a -= 1
                b -= 1
            igual = k + (i - a)          # quanto da 1a tentativa a 2a repete
            tamanho = b - a              # tamanho da 1a tentativa
            # regravação: a 1a tentativa é quase toda o começo da 2a (só o finalzinho
            # difere, que é o erro). Se difere muito, é repetição de propósito
            # ("você precisa fazer X. você precisa fazer Y") e fica.
            # regravação reformulada: quase todas as palavras da 1a voltam logo na 2a
            seguinte = set(tok[b:b + tamanho + 6])
            volta = sum(1 for x in tok[a:b] if x in seguinte) / max(1, tamanho)
            if 0 < tamanho <= 45 and (tamanho - igual <= max(3, int(0.4 * tamanho)) or volta >= 0.75):
                trecho = seq[a:b]
                if any([_marcar(p, MOTIVO) for p in trecho]):
                    achados.append((MOTIVO, trecho[0]["i"], trecho[-1]["i"], " ".join(p["t"] for p in trecho)))
                j = max(j + 1, b + k)   # sempre anda (b pode voltar antes de j)
                continue
        j += 1

    # 2. recomeços curtos: "o meu o meu processo", "eu acho, é, eu acho", "pri primeiro",
    #    "o meu pri o meu primeiro". A 1a tentativa (1 a 4 palavras) vem colada na 2a,
    #    no máximo com uma muleta no meio; a última palavra dela pode estar pela metade.
    def igual(x, y, ultima):
        return x == y or (ultima and len(x) >= 2 and len(y) > len(x) and y.startswith(x))

    vivas = [p for p in palavras if not p.get("cortada")]
    vt = [_norm(p["t"]) for p in vivas]
    j = 1
    while j < len(vivas):
        feito = False
        for n in (4, 3, 2, 1):
            for meio in (0, 1):
                a = j - n - meio
                if a < 0 or j + n > len(vivas) + (0 if n > 1 else 0):
                    continue
                if meio and vt[j - 1] not in MULETAS:
                    continue
                if vivas[j]["ini"] - vivas[a]["fim"] > 2.5:
                    continue
                prim, seg = vt[a:a + n], vt[j:j + n]
                if len(seg) < n or not all(prim) or not all(seg):
                    continue
                if not all(igual(prim[k], seg[k], k == n - 1) for k in range(n)):
                    continue
                inteira = prim == seg
                if n == 1 and inteira:
                    # palavra repetida: só gaguejo de palavra curta ou mal pronunciada
                    if prim[0] in ENFASE or not (len(prim[0]) <= 3 or vivas[a].get("prob", 1) < 0.6):
                        continue
                if n == 1 and not inteira and prim[0] in PEQUENAS:
                    continue      # "pra praia", "pro programa"
                if n >= 2 and inteira and all(x in ENFASE for x in prim):
                    continue
                trecho = vivas[a:j]
                if any([_marcar(p, MOTIVO_GAGUEJO if n == 1 else MOTIVO) for p in trecho]):
                    achados.append((MOTIVO_GAGUEJO if n == 1 else MOTIVO, trecho[0]["i"], trecho[-1]["i"],
                                    " ".join(p["t"] for p in trecho) + " | " + " ".join(p["t"] for p in vivas[j:j + n])))
                feito = True
                break
            if feito:
                break
        j += 1

    # 3. frase abandonada e refeita com outro começo: quase todas as palavras de conteúdo
    #    de uma frase voltam na frase seguinte, logo depois
    vivas = [p for p in palavras if not p.get("cortada")]
    frases, atual = [], []
    for k, p in enumerate(vivas):
        atual.append(p)
        prox = vivas[k + 1] if k + 1 < len(vivas) else None
        if FIM_FRASE.search(p["t"]) or prox is None or prox["ini"] - p["fim"] > 0.9:
            frases.append(atual)
            atual = []
    conteudo = lambda f: [x for x in (_norm(p["t"]) for p in f) if x and x not in PEQUENAS]
    for fa, fb in zip(frases, frases[1:]):
        ca, cb = conteudo(fa), set(conteudo(fb))
        if len(ca) < 3 or fb[0]["ini"] - fa[-1]["fim"] > 6 or fa[-1]["t"].strip().endswith("?"):
            continue
        volta = sum(1 for x in ca if x in cb) / len(ca)
        if volta >= 0.7 and len(fa) <= len(fb) + 3:
            if any([_marcar(p, MOTIVO) for p in fa]):
                achados.append((MOTIVO, fa[0]["i"], fa[-1]["i"], " ".join(p["t"] for p in fa)))
    return achados


def desfazer(palavras):
    n = 0
    for p in palavras:
        if p.get("origem") == "auto" and p.get("motivo") in (MOTIVO, MOTIVO_GAGUEJO):
            p.update(cortada=False)
            p.pop("motivo", None)
            p.pop("origem", None)
            n += 1
    return n


def revisar(palavras):
    """Texto que ficou, frase por frase, com o que parece erro marcado pra revisão.
    Devolve linhas prontas pra imprimir."""
    vivas = [p for p in palavras if not p.get("cortada")]
    frases, atual = [], []
    for k, p in enumerate(vivas):
        atual.append(p)
        prox = vivas[k + 1] if k + 1 < len(vivas) else None
        if FIM_FRASE.search(p["t"]) or prox is None or prox["ini"] - p["fim"] > 0.9:
            frases.append(atual)
            atual = []
    linhas = []
    conteudo = lambda f: [x for x in (_norm(p["t"]) for p in f) if x and x not in PEQUENAS]
    for n, f in enumerate(frases):
        tok = [_norm(p["t"]) for p in f]
        avisos = []
        # começo igual ao de uma das 2 frases anteriores
        for ant in frases[max(0, n - 2):n]:
            ta = [_norm(p["t"]) for p in ant]
            k = 0
            while k < min(len(ta), len(tok)) and ta[k] == tok[k]:
                k += 1
            if k >= 2 and any(x not in PEQUENAS for x in tok[:k]):
                avisos.append(f"começa igual a uma frase anterior ({' '.join(tok[:k])})")
        # parecida com a próxima
        if n + 1 < len(frases):
            ca, cb = conteudo(f), set(conteudo(frases[n + 1]))
            if len(ca) >= 2:
                volta = sum(1 for x in ca if x in cb) / len(ca)
                if volta >= 0.5:
                    avisos.append(f"{int(volta * 100)}% das palavras voltam na frase seguinte")
        # frase que termina sem ponto e com pausa: pode ser tentativa abandonada
        prox = frases[n + 1][0] if n + 1 < len(frases) else None
        if prox is not None and not FIM_FRASE.search(f[-1]["t"]) and prox["ini"] - f[-1]["fim"] > 0.9 and len(f) <= 12:
            avisos.append("termina no meio, seguida de pausa")
        # palavra repetida perto, dentro da frase
        for a in range(len(tok)):
            for b in range(a + 1, min(len(tok), a + 4)):
                if tok[a] and tok[a] == tok[b] and tok[a] not in PEQUENAS and tok[a] not in ENFASE:
                    avisos.append(f"'{f[a]['t']}' repetida ({f[a]['i']} e {f[b]['i']})")
        # palavra que o reconhecimento entendeu mal (fala embolada ou errada)
        inseguras = [f"{p['i']}:{p['t']}" for p in f if p.get("prob", 1) < 0.45]
        if inseguras:
            avisos.append("palavras inseguras " + ", ".join(inseguras))
        marca = "  ⚠ " + " · ".join(dict.fromkeys(avisos)) if avisos else ""
        linhas.append(f"[{f[0]['i']}-{f[-1]['i']}] " + " ".join(p["t"] for p in f) + marca)
    return linhas
