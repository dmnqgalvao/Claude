"""Acha fala que ficou sem texto e lê de novo.

O reconhecimento de fala "limpa" a fala: muitas vezes não escreve o começo errado de uma
frase, a palavra repetida ou o pedaço largado no meio. Sem texto, o corte não enxerga esse
pedaço e ele escapa pro vídeo. Aqui:

1. um detector de voz (Silero, o mesmo do faster-whisper) marca onde tem fala no áudio;
2. palavra esticada demais (que engoliu um pedaço de fala vizinha) é encurtada pro tamanho
   normal, do lado que tem fala sobrando;
3. todo trecho com fala e sem palavra é lido de novo sozinho, com um pouco de contexto;
4. o que ainda ficar sem texto vira uma marca "[fala]" já cortada (motivo "fala sem texto"),
   que a pessoa pode trazer de volta na aba cortes.
Depois disso o detector de regravações enxerga as tentativas erradas.
"""

import re

TAXA = 16000
ALUCINACOES = re.compile(r"(obrigad|legenda|inscrev|tchau|amara\.org|música|aplausos)", re.I)


def _fala(audio):
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    trechos = get_speech_timestamps(audio, VadOptions(threshold=0.5, min_silence_duration_ms=100,
                                                      speech_pad_ms=20, min_speech_duration_ms=120))
    return [(t["start"] / TAXA, t["end"] / TAXA) for t in trechos]


def _sobreposicao(a, b, trechos):
    return sum(max(0.0, min(b, y) - max(a, x)) for x, y in trechos)


def _duracao_maxima(texto):
    letras = len(re.sub(r"\W", "", texto))
    return max(0.55, 0.16 * letras + 0.25)


def encurtar_esticadas(palavras, fala):
    """Palavra muito mais longa que o normal: corta o excesso do lado onde há fala sobrando
    (é ali que mora a tentativa que não foi escrita); sem fala dos dois lados, corta o
    começo (silêncio grudado)."""
    for p in palavras:
        dur = p["fim"] - p["ini"]
        maxd = _duracao_maxima(p["t"])
        if dur <= maxd:
            continue
        excesso = dur - maxd
        antes = _sobreposicao(p["ini"], p["ini"] + excesso, fala)
        depois = _sobreposicao(p["fim"] - excesso, p["fim"], fala)
        if depois > antes * 1.5 and depois > 0.15:
            p["fim"] = round(p["fim"] - excesso, 3)
        else:
            p["ini"] = round(p["ini"] + excesso, 3)


def buracos(palavras, fala, minimo=0.18):
    """Trechos com fala e sem nenhuma palavra por cima."""
    out = []
    for a, b in fala:
        cobertos = sorted((max(a, p["ini"] - .04), min(b, p["fim"] + .04)) for p in palavras
                          if p["fim"] > a and p["ini"] < b)
        t = a
        for x, y in cobertos + [(b, b)]:
            if x - t >= minimo:
                out.append((round(t, 3), round(x, 3)))
            t = max(t, y)
    return out


def recuperar(modelo, audio, palavras, prompt, hesitacao, log=print):
    """Lê de novo os buracos e devolve a lista nova de palavras (reindexada)."""
    fala = _fala(audio)
    encurtar_esticadas(palavras, fala)
    novos, marcas = [], []
    for a, b in buracos(palavras, fala):
        ini_clip, fim_clip = max(0.0, a - 0.6), min(len(audio) / TAXA, b + 0.6)
        antes = " ".join(p["t"] for p in palavras if p["fim"] <= a)[-200:]
        try:
            segs, _ = modelo.transcribe(audio[int(ini_clip * TAXA):int(fim_clip * TAXA)], language="pt",
                                        word_timestamps=True, vad_filter=False, beam_size=5,
                                        condition_on_previous_text=False,
                                        initial_prompt=(prompt + " " + antes).strip())
            achadas = []
            for s in segs:
                for w in s.words or []:
                    wi, wf = ini_clip + float(w.start), ini_clip + float(w.end)
                    meio = (wi + wf) / 2
                    texto = w.word.strip()
                    if not texto or not (a - 0.05 <= meio <= b + 0.05):
                        continue
                    if float(w.probability) < 0.25 or (ALUCINACOES.search(texto) and float(w.probability) < 0.6):
                        continue
                    # já existe palavra ali? então é a mesma, não duplica
                    if any(min(wf, p["fim"]) - max(wi, p["ini"]) > 0.5 * (wf - wi) for p in palavras):
                        continue
                    achadas.append({"t": texto, "ini": round(max(wi, a - 0.05), 3), "fim": round(min(wf, b + 0.05), 3),
                                    "prob": round(float(w.probability), 3), "cortada": False, "destaque": False,
                                    "recuperada": True})
        except Exception as e:
            log(f"não consegui reler {a:.2f}-{b:.2f}: {e}")
            achadas = []
        if achadas:
            novos += achadas
        else:
            marcas.append({"t": "[fala]", "ini": a, "fim": b, "prob": 0.0, "cortada": True, "destaque": False,
                           "motivo": "fala sem texto", "origem": "auto", "recuperada": True})
    for p in novos:
        if hesitacao(p["t"]):
            p.update(cortada=True, motivo="hesitação", origem="auto")
    todas = sorted(palavras + novos + marcas, key=lambda p: (p["ini"], p["fim"]))
    for k, p in enumerate(todas):
        p["i"] = k
    log(f"{len(novos)} palavras recuperadas, {len(marcas)} trechos de fala sem texto marcados")
    return todas, len(novos), len(marcas)


def _norm(t):
    return re.sub(r"[^\wÀ-ÿ]", "", (t or "").lower())


def _ouvir(modelo, audio, a, b, prompt):
    """Transcreve só o trecho [a, b] do áudio, sem contexto do resto do vídeo."""
    ini, fim = max(0.0, a), min(len(audio) / TAXA, b)
    segs, _ = modelo.transcribe(audio[int(ini * TAXA):int(fim * TAXA)], language="pt", word_timestamps=True,
                                vad_filter=False, beam_size=5, condition_on_previous_text=False,
                                initial_prompt=prompt)
    out = []
    for s in segs:
        for w in s.words or []:
            t = w.word.strip()
            if not t or float(w.probability) < 0.2 or (ALUCINACOES.search(t) and float(w.probability) < 0.6):
                continue
            out.append({"t": t, "ini": round(ini + float(w.start), 3), "fim": round(ini + float(w.end), 3),
                        "prob": round(float(w.probability), 3)})
    return out


def _repeticoes(tok):
    """Quantos pedaços de 1 a 3 palavras aparecem repetidos logo em seguida."""
    n = 0
    for k in (1, 2, 3):
        for i in range(len(tok) - 2 * k + 1):
            if tok[i:i + k] == tok[i + k:i + 2 * k] and all(tok[i:i + k]):
                n += 1
    return n


def blocos_de_fala(fala, maximo=9.0, pausa=0.6):
    """Junta os trechos de voz em blocos de até ~9 s, quebrando nas pausas."""
    blocos = []
    for a, b in fala:
        if blocos and a - blocos[-1][1] < pausa and b - blocos[-1][0] <= maximo:
            blocos[-1][1] = b
        else:
            blocos.append([a, b])
    return blocos


def segunda_escuta(modelo, audio, palavras, prompt, hesitacao, log=print):
    """Ouve de novo cada bloco de fala sozinho. Na transcrição do vídeo inteiro o
    reconhecimento usa o contexto e "arruma" a fala: junta várias tentativas numa só e some
    com repetições. Ouvindo um bloco curto sozinho ele escreve o que foi dito. Quando a
    segunda escuta traz mais palavras ou mais repetições, ela substitui a primeira ali."""
    fala = _fala(audio)
    trocas = 0
    resultado = list(palavras)
    for a, b in blocos_de_fala(fala):
        dentro = [p for p in resultado if a - 0.1 <= (p["ini"] + p["fim"]) / 2 <= b + 0.1]
        try:
            novas = _ouvir(modelo, audio, a - 0.15, b + 0.15, prompt)
        except Exception as e:
            log(f"segunda escuta falhou em {a:.1f}s: {e}")
            continue
        t1 = [_norm(p["t"]) for p in dentro]
        t2 = [_norm(p["t"]) for p in novas]
        if not novas or (len(t2) < len(t1) + 2 and _repeticoes(t2) <= _repeticoes(t1)):
            continue
        for p in novas:
            p.update(cortada=False, destaque=False, segunda_escuta=True)
            if hesitacao(p["t"]):
                p.update(cortada=True, motivo="hesitação", origem="auto")
        resultado = [p for p in resultado if p not in dentro] + novas
        trocas += 1
    resultado.sort(key=lambda p: (p["ini"], p["fim"]))
    for k, p in enumerate(resultado):
        p["i"] = k
    log(f"segunda escuta: {trocas} trechos tinham fala escondida")
    return resultado, trocas


def conferir(modelo, audio, palavras, segmentos, prompt, log=print):
    """Reescuta cada trecho que vai pro vídeo, sozinho, e passa o que ouviu pelo detector de
    regravações (com as últimas palavras do trecho anterior como contexto). O que o detector
    cortar ali é tentativa ou repetição escondida dentro de um trecho mantido.
    Devolve [(ini, fim, devia, ouvi, extras)], extras = [(ini, fim, texto)]."""
    from . import regravacoes as R
    vivas = [p for p in palavras if not p.get("cortada")]
    relatorio, contexto = [], []
    for s in segmentos:
        a, b = s["ini"], s["fim"]
        devia = [p for p in vivas if a - 0.02 <= (p["ini"] + p["fim"]) / 2 <= b + 0.02]
        try:
            ouvi = _ouvir(modelo, audio, a, b, prompt)
        except Exception as e:
            log(f"não consegui reescutar {a:.1f}s: {e}")
            continue
        seq = [dict(p, origem="voce", cortada=False) for p in contexto[-6:]]
        seq += [dict(p, cortada=False, destaque=False) for p in ouvi]
        for k, p in enumerate(seq):
            p["i"] = k
        R.detectar(seq)
        extras, atual = [], []
        for p in seq:
            if p.get("cortada") and p.get("origem") == "auto" and p.get("motivo") != "hesitação":
                atual.append(p)
            elif atual:
                extras.append(atual)
                atual = []
        if atual:
            extras.append(atual)
        extras = [(g[0]["ini"], g[-1]["fim"], " ".join(p["t"] for p in g)) for g in extras]
        if not devia and ouvi:
            extras.append((a, b, " ".join(p["t"] for p in ouvi) + " (trecho sem texto)"))
        if extras:
            relatorio.append((a, b, " ".join(p["t"] for p in devia), " ".join(p["t"] for p in ouvi), extras))
        contexto = [p for p in seq if not p.get("cortada")] or contexto
    return relatorio
