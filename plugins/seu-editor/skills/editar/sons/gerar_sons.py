"""Gera os efeitos sonoros do Seu Editor do zero (síntese), sem direitos de terceiros.

  python gerar_sons.py   -> whoosh.wav, pop.wav, ding.wav, clique.wav, impacto.wav, subida.wav
"""
import math, os, random, struct, wave

TAXA = 48000
AQUI = os.path.dirname(os.path.abspath(__file__))


def salvar(nome, amostras):
    pico = max(1e-9, max(abs(a) for a in amostras))
    with wave.open(os.path.join(AQUI, nome + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(TAXA)
        w.writeframes(b"".join(struct.pack("<h", int(a / pico * 0.89 * 32767)) for a in amostras))


def ruido_filtrado(dur, corte, env, semente=3):
    """ruído branco passando por um passa-baixa de um polo com corte variável"""
    random.seed(semente)
    n = int(dur * TAXA); y = 0.0; y2 = 0.0; saida = []
    for i in range(n):
        t = i / n
        fc = corte(t)
        a = 1 - math.exp(-2 * math.pi * fc / TAXA)
        x = random.uniform(-1, 1)
        y += a * (x - y); y2 += a * (y - y2)          # dois polos
        hp = y2 - (saida[-1] * 0.0 if saida else 0)
        saida.append(hp * env(t))
    return saida


def whoosh():
    return ruido_filtrado(.5, lambda t: 250 + 5200 * math.sin(math.pi * t) ** 2,
                          lambda t: math.sin(math.pi * t) ** 1.6)


def subida():
    return ruido_filtrado(.9, lambda t: 200 + 7000 * t ** 2, lambda t: t ** 1.5 * (1 - max(0, t - .92) / .08))


def pop():
    n = int(.09 * TAXA); fase = 0; s = []
    for i in range(n):
        t = i / TAXA
        f = 150 + 650 * math.exp(-t * 60)
        fase += 2 * math.pi * f / TAXA
        s.append(math.sin(fase) * math.exp(-t * 38) * min(1, i / 40))
    return s


def ding():
    n = int(1.1 * TAXA)
    return [(math.sin(2 * math.pi * 1318.5 * i / TAXA) + .45 * math.sin(2 * math.pi * 2637 * i / TAXA)
             + .2 * math.sin(2 * math.pi * 3955 * i / TAXA)) * math.exp(-i / TAXA * 4.2) * min(1, i / 30)
            for i in range(n)]


def clique():
    random.seed(5)
    n = int(.03 * TAXA)
    return [(random.uniform(-1, 1) * math.exp(-i / TAXA * 900) + .6 * math.sin(2 * math.pi * 3200 * i / TAXA)
             * math.exp(-i / TAXA * 220)) for i in range(n)]


def impacto():
    random.seed(9)
    n = int(.8 * TAXA); fase = 0; y = 0; s = []
    for i in range(n):
        t = i / TAXA
        f = 48 + 70 * math.exp(-t * 18)
        fase += 2 * math.pi * f / TAXA
        y += .08 * (random.uniform(-1, 1) - y)
        s.append(math.sin(fase) * math.exp(-t * 5.5) + y * 2.5 * math.exp(-t * 14))
    return s


if __name__ == "__main__":
    for nome, f in [("whoosh", whoosh), ("pop", pop), ("ding", ding), ("clique", clique),
                    ("impacto", impacto), ("subida", subida)]:
        salvar(nome, f())
        print(nome)
