"""Transcrição em português com o tempo de cada palavra (faster-whisper).

Decisões que fazem diferença em vídeo falado em português:
- idioma travado em "pt", sem detecção automática;
- um texto de partida cheio de hesitações, pra o Whisper escrever os
  "éé", "hum" e "tipo" em vez de limpar a fala (sem isso não dá pra cortar);
- detector de voz (Silero VAD, já incluso) pra ignorar ruído e trechos mudos;
- condition_on_previous_text desligado, o que evita frases inventadas em
  trechos repetidos.
"""

import re
import time

from . import projeto as P

PROMPT_BASE = (
    "Então, é... hum, deixa eu ver. Tipo, sabe? Aí eu, ahn, comecei a gravar, né. "
    "Éé, peraí, vou falar de novo."
)

HESITACAO = re.compile(
    r"^(h+u+m+|h+m+|u+m+|hum+|ã+h*|ahn+|a+h+n|é{2,}|e{2,}h*|eh+|uh+|hã+|ãã+|hmm+|uhum)$",
    re.IGNORECASE,
)


def normalizar(t):
    return re.sub(r"[^\wÀ-ÿ]", "", t.strip().lower())


def transcrever(pasta, modelo="large-v3-turbo", dir_modelos=None, log=print):
    proj = P.carregar(pasta)
    duracao = float(proj.get("info", {}).get("duracao") or 0) or 1.0
    P.escrever_estado(pasta, tarefa="transcrevendo", progresso=0.0,
                      mensagem="carregando o modelo de transcrição")

    from faster_whisper import WhisperModel

    modelo_w = WhisperModel(modelo, device="auto", compute_type="int8", download_root=dir_modelos)
    termos = proj.get("termos") or []
    prompt = PROMPT_BASE + (" " + ", ".join(termos) + "." if termos else "")

    P.escrever_estado(pasta, mensagem="ouvindo o vídeo")
    segmentos, _info = modelo_w.transcribe(
        P.midia_previa(proj),
        language="pt",
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 250, "speech_pad_ms": 150},
        initial_prompt=prompt,
        condition_on_previous_text=False,
        beam_size=5,
    )

    palavras = []
    ultimo_aviso = 0.0
    for seg in segmentos:
        for w in seg.words or []:
            texto = w.word.strip()
            if not texto:
                continue
            ini, fim = float(w.start), float(w.end)
            if palavras and ini < palavras[-1]["fim"]:
                ini = palavras[-1]["fim"]
            fim = max(fim, ini + 0.05)
            # palavra esticada demais costuma ser silêncio grudado nela
            if fim - ini > 1.6:
                ini = fim - 1.0
            p = {"i": len(palavras), "t": texto, "ini": round(ini, 3), "fim": round(fim, 3),
                 "prob": round(float(w.probability), 3), "cortada": False, "destaque": False}
            if HESITACAO.match(normalizar(texto)):
                p.update(cortada=True, motivo="hesitação", origem="auto")
            palavras.append(p)
        agora = time.time()
        if agora - ultimo_aviso > 0.8:
            prog = min(0.99, seg.end / duracao)
            P.escrever_estado(pasta, progresso=round(prog, 3),
                              mensagem=f"ouvindo o vídeo ({int(prog * 100)}%)")
            log(f"transcrevendo... {int(prog * 100)}%")
            ultimo_aviso = agora

    proj = P.carregar(pasta)   # relê, a interface pode ter mudado algo
    proj["palavras"] = palavras
    proj["modelo"] = modelo
    # vários arquivos: clipe de vídeo quase sem fala vira trecho de imagem (vlog, paisagem, b-roll)
    arqs = proj.get("arquivos") or []
    if len(arqs) > 1:
        for a in arqs:
            if a["tipo"] != "video" or a.get("modo_manual"):
                continue
            dur = max(0.1, a["fim"] - a["ini"])
            n = sum(1 for p in palavras if a["ini"] <= (p["ini"] + p["fim"]) / 2 < a["fim"])
            a["modo"] = "imagem" if n < 3 or n / dur < 0.35 else "fala"
    P.salvar(pasta, proj)
    auto = sum(1 for p in palavras if p.get("cortada"))
    P.escrever_estado(pasta, tarefa=None, progresso=1.0,
                      mensagem=f"transcrição pronta: {len(palavras)} palavras, {auto} hesitações marcadas")
    return palavras
