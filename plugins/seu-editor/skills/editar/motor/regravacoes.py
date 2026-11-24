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
                j = b + k
                continue
        j += 1

    # 2. gaguejos
    vivas = [p for p in palavras if not p.get("cortada")]
    for x, y in zip(vivas, vivas[1:]):
        a, b = _norm(x["t"]), _norm(y["t"])
        if not a or not b or y["ini"] - x["fim"] > 0.8:
            continue
        repetida = a == b and a not in ENFASE and (len(a) <= 3 or x.get("prob", 1) < 0.6)
        pedaco = a != b and len(a) >= 2 and len(b) >= len(a) + 2 and b.startswith(a) and a not in PEQUENAS
        if repetida or pedaco:
            if _marcar(x, MOTIVO_GAGUEJO):
                achados.append((MOTIVO_GAGUEJO, x["i"], x["i"], f"{x['t']} {y['t']}"))
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
