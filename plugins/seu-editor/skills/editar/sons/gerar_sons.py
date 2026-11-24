"""Gera os efeitos sonoros do Seu Editor do zero (síntese), sem direitos de terceiros.

Sons macios, com ataque suave e corpo, pensados pra ficar baixinho por baixo da voz:
  pop     bolha arredondada
  clique  botão pequeno, abafado
  camera  obturador de câmera (dois cliques mecânicos)
E, pra quem pedir: whoosh, ding, impacto, subida.

  python gerar_sons.py
"""
import math, os, random, struct, wave

TAXA = 48000
AQUI = os.path.dirname(os.path.abspath(__file__))


def salvar(nome, amostras, pico_final=0.7):
    pico = max(1e-9, max(abs(a) for a in amostras))
    with wave.open(os.path.join(AQUI, nome + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(TAXA)
        w.writeframes(b"".join(struct.pack("<h", int(a / pico * pico_final * 32767)) for a in amostras))


def passa_baixa(s, fc):
    a = 1 - math.exp(-2 * math.pi * fc / TAXA)
    y, out = 0.0, []
    for x in s:
        y += a * (x - y)
        out.append(y)
    return out


def passa_banda(s, f_baixo, f_alto):
    lp = passa_baixa(s, f_alto)
    lp2 = passa_baixa(lp, f_baixo)
    return [a - b for a, b in zip(lp, lp2)]


def env(i, ataque, queda):
    t = i / TAXA
    return min(1.0, t / ataque) * math.exp(-max(0.0, t - ataque) / queda)


def pop():
    """bolha: seno que desce de tom, ataque de 2 ms, corpo curto e arredondado"""
    n = int(.14 * TAXA); fase = 0; s = []
    for i in range(n):
        t = i / TAXA
        f = 260 + 520 * math.exp(-t * 55)
        fase += 2 * math.pi * f / TAXA
        s.append((math.sin(fase) + .18 * math.sin(2 * fase)) * env(i, .002, .035))
    return passa_baixa(s, 3500)


def clique():
    """botão pequeno: estalinho filtrado + um corpinho grave, tudo bem curto e abafado"""
    random.seed(4)
    n = int(.05 * TAXA)
    ruido = passa_banda([random.uniform(-1, 1) for _ in range(n)], 900, 4200)
    s = []
    for i in range(n):
        t = i / TAXA
        s.append(ruido[i] * env(i, .0006, .0045) * 2.2 + math.sin(2 * math.pi * 180 * t) * env(i, .001, .009) * .5)
    return passa_baixa(s, 6000)


def camera():
    """obturador: clique de abrir, clique de fechar 70 ms depois, com um leve chiado mecânico"""
    random.seed(8)
    n = int(.2 * TAXA)
    ruido = passa_banda([random.uniform(-1, 1) for _ in range(n)], 1200, 5200)
    s = [0.0] * n
    for inicio, forca in ((0.0, 1.0), (0.07, .8)):
        k0 = int(inicio * TAXA)
        for i in range(k0, n):
            j = i - k0
            s[i] += ruido[i] * env(j, .0005, .006) * forca * 2
            s[i] += math.sin(2 * math.pi * 140 * j / TAXA) * env(j, .001, .012) * .35 * forca
    for i in range(int(.004 * TAXA), int(.07 * TAXA)):
        s[i] += ruido[i] * .05
    return passa_baixa(s, 7000)


def whoosh():
    random.seed(3)
    n = int(.5 * TAXA); y = 0.0; y2 = 0.0; s = []
    for i in range(n):
        t = i / n
        fc = 250 + 3800 * math.sin(math.pi * t) ** 2
        a = 1 - math.exp(-2 * math.pi * fc / TAXA)
        y += a * (random.uniform(-1, 1) - y); y2 += a * (y - y2)
        s.append(y2 * math.sin(math.pi * t) ** 2)
    return s


def ding():
    n = int(.9 * TAXA)
    return [(math.sin(2 * math.pi * 1046.5 * i / TAXA) + .3 * math.sin(2 * math.pi * 2093 * i / TAXA))
            * env(i, .003, .25) for i in range(n)]


def impacto():
    random.seed(9)
    n = int(.6 * TAXA); fase = 0; s = []
    for i in range(n):
        t = i / TAXA
        fase += 2 * math.pi * (50 + 60 * math.exp(-t * 18)) / TAXA
        s.append(math.sin(fase) * env(i, .003, .16))
    return passa_baixa(s, 900)


def subida():
    random.seed(2)
    n = int(.8 * TAXA); y = 0.0; s = []
    for i in range(n):
        t = i / n
        a = 1 - math.exp(-2 * math.pi * (200 + 5000 * t * t) / TAXA)
        y += a * (random.uniform(-1, 1) - y)
        s.append(y * t ** 1.6 * (1 - max(0, t - .9) / .1))
    return s


if __name__ == "__main__":
    for nome, f, pico in [("pop", pop, .7), ("clique", clique, .6), ("camera", camera, .65),
                          ("whoosh", whoosh, .5), ("ding", ding, .45), ("impacto", impacto, .7), ("subida", subida, .5)]:
        salvar(nome, f(), pico)
        print(nome)
