"""
Mari Louise - serie "hard things"
Reels de 15s no estilo da referencia (@casey.scharoff7): takes de exaustao no rolo,
texto pequeno em serif branca minuscula centralizado e fixo, grade dessaturada.

Uso:
    python3 build.py --takes /caminho/dos/takes          # renderiza os 6
    python3 build.py --takes /caminho --only 01 04       # so alguns
    python3 build.py --takes /caminho --download         # baixa os takes do Drive antes

Os takes brutos ficam no Drive da Mari (pasta "Vídeo Coros" + "Ciclismo") e nao sao versionados.
"""
import argparse
import os
import subprocess
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "Lora-Variable.ttf")
W, H, FPS = 1080, 1920, 30

# id do Drive de cada take usado
DRIVE_IDS = {
    "IMG_1740": "1QUGWDkHcvvhIVceZ0iUqP2W6QcGhHQAx",
    "IMG_1743": "1f36xXrzB6dFGqjTqpjgtVgu2rCZqIUt-",
    "IMG_1745": "1PGOLCaFiwf1C1E_MmjRMImqE4XYHcxL9",
    "IMG_1746": "1FF22zYsyZ2zgdkejEeKlf9yqxViGT3Ms",
    "IMG_1748": "1T1zYpNpCqJjsCoVNimDBHOhzgC2DsA3D",
    "IMG_1754": "1Tx5FYXgY8lhoQXEwHK_UnUfZiYtx4WEA",
    "IMG_1755": "1okrxCCVZZtlwH1uSfCVVzqCHJoA52G74",
    "IMG_1756": "1rsqhXtLXKWCWTuPG0XOph6NS0JTGNrvg",
    "IMG_1757": "1dLzynPIyqCtPZ1yS94iG8OZiwXlYGzln",
    "IMG_1758": "1XIF3373iFUt6RDRoQfOAhx-GWO_kag4e",
}

# (take, inicio_s, duracao_s, zoom)  zoom > 1 aproxima o quadro (centro levemente acima)
VIDEOS = [
    {
        "id": "01",
        "slug": "hobbies-dificeis",
        "lines": [
            "escolha hobbies difíceis",
            "e prove pra si mesma que quem manda",
            "na sua cabeça é você.",
        ],
        "shots": [
            ("IMG_1740", 0.0, 3.2, 1.00),   # maos no rosto em cima da bike
            ("IMG_1758", 0.2, 3.0, 1.00),   # close lateral, cabeca pendurada
            ("IMG_1745", 0.8, 3.2, 1.08),   # encostada na parede, maos na cintura
            ("IMG_1757", 5.6, 3.2, 1.00),   # frontal, cabeca entre os bracos
            ("IMG_1740", 3.4, 2.2, 1.00),   # levanta o olhar e volta pro guidao
        ],
    },
    {
        "id": "02",
        "slug": "descobrir-do-que-e-capaz",
        "lines": [
            "escolha coisas que te desafiem",
            "o suficiente pra você",
            "descobrir do que é capaz.",
        ],
        "shots": [
            ("IMG_1755", 0.0, 3.0, 1.00),   # lateral, cabeca baixa
            ("IMG_1743", 1.5, 3.2, 1.10),   # frontal, cabelo caindo, respirando
            ("IMG_1756", 2.0, 3.2, 1.00),   # parede, recuperando o folego
            ("IMG_1754", 1.8, 3.0, 1.00),   # close do coque, peito subindo
            ("IMG_1755", 3.0, 2.6, 1.00),   # ergue a cabeca, boca aberta, olhar pra frente
        ],
    },
    {
        "id": "03",
        "slug": "treino-que-queria-abandonar",
        "lines": [
            "toda vez que você termina um treino",
            "que queria abandonar",
            "sua mente aprende a confiar",
            "um pouco mais em você.",
        ],
        "shots": [
            ("IMG_1757", 2.3, 3.0, 1.00),
            ("IMG_1740", 0.0, 3.3, 1.00),
            ("IMG_1748", 0.5, 3.3, 1.10),
            ("IMG_1746", 0.5, 3.5, 1.00),
            ("IMG_1758", 5.8, 2.8, 1.00),
        ],
    },
    {
        "id": "04",
        "slug": "go-do-the-hard-thing",
        "lines": [
            "go do the hard thing",
            "before your mind finishes the excuse.",
        ],
        # cortes mais curtos: a frase pede pressa
        "shots": [
            ("IMG_1754", 1.8, 2.6, 1.00),
            ("IMG_1755", 3.0, 2.5, 1.00),
            ("IMG_1743", 0.0, 2.6, 1.10),
            ("IMG_1758", 0.0, 2.6, 1.00),
            ("IMG_1740", 3.3, 2.3, 1.00),
            ("IMG_1757", 10.0, 2.4, 1.00),
        ],
    },
    {
        "id": "05",
        "slug": "do-hard-things-on-purpose",
        "lines": [
            "do hard things on purpose",
            "so life's hard things find you ready.",
        ],
        "shots": [
            ("IMG_1756", 1.8, 3.2, 1.00),
            ("IMG_1757", 5.5, 3.2, 1.00),
            ("IMG_1755", 5.0, 2.8, 1.00),
            ("IMG_1748", 1.5, 3.2, 1.10),
            ("IMG_1745", 1.0, 3.0, 1.08),
        ],
    },
    {
        "id": "06",
        "slug": "sofrer-por-escolha",
        "lines": [
            "se é pra sofrer,",
            "que seja por escolha minha.",
        ],
        "shots": [
            ("IMG_1758", 0.0, 3.2, 1.00),
            ("IMG_1740", 0.0, 3.3, 1.00),
            ("IMG_1746", 0.3, 3.2, 1.00),
            ("IMG_1755", 3.0, 2.6, 1.00),
            ("IMG_1756", 3.0, 3.2, 1.00),
        ],
    },
]

# Grade "quiet luxury" inspirada na ref: menos saturacao, pretos levemente lavados (matte),
# sombras puxadas pro frio, pele/meio-tons quentes, highlights contidos.
GRADE = ",".join([
    "eq=contrast=1.07:saturation=0.68:gamma=0.99",
    "colorbalance=rs=-0.05:gs=-0.01:bs=0.05:rm=0.03:gm=0.0:bm=-0.02:rh=0.03:gh=0.01:bh=-0.03",
    "curves=all='0/0.04 0.25/0.21 0.5/0.47 0.8/0.80 1/0.92'",
    "vignette=angle=PI/4.6",
    "noise=alls=4:allf=t",
])


def text_overlay(lines, path):
    """PNG transparente: sombra difusa central + texto serif branco com sombra suave."""
    size = 33
    lead = 1.42
    font = ImageFont.truetype(FONT, size)
    try:
        font.set_variation_by_axes([400])
    except Exception:
        pass

    line_h = int(size * lead)
    block_h = line_h * len(lines)
    cy = int(H * 0.5)
    top = cy - block_h // 2

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # 1) mancha escura bem difusa atras do bloco (o "filtro" que segura a leitura)
    halo = Image.new("L", (W, H), 0)
    hd = ImageDraw.Draw(halo)
    widest = max(font.getlength(l) for l in lines)
    rx, ry = int(widest * 0.62) + 60, int(block_h * 0.9) + 90
    hd.ellipse([W // 2 - rx, cy - ry, W // 2 + rx, cy + ry], fill=70)
    halo = halo.filter(ImageFilter.GaussianBlur(110))
    canvas.paste(Image.new("RGBA", (W, H), (8, 8, 10, 255)), (0, 0), halo)

    # 2) sombra do texto
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for i, l in enumerate(lines):
        x = (W - font.getlength(l)) / 2
        sd.text((x, top + i * line_h + 2), l, font=font, fill=(0, 0, 0, 170))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    canvas = Image.alpha_composite(canvas, shadow)

    # 3) texto
    td = ImageDraw.Draw(canvas)
    for i, l in enumerate(lines):
        x = (W - font.getlength(l)) / 2
        td.text((x, top + i * line_h), l, font=font, fill=(250, 248, 244, 255))

    canvas.save(path)


def shot_filter(idx, zoom):
    z = ""
    if zoom > 1.0:
        cw, ch = int(W / zoom) // 2 * 2, int(H / zoom) // 2 * 2
        # recorte um pouco acima do centro pra preservar cabeca
        z = f",crop={cw}:{ch}:(iw-{cw})/2:(ih-{ch})*0.40,scale={W}:{H}:flags=lanczos"
    return (
        f"[{idx}:v]scale={W}:{H}:flags=lanczos{z},setsar=1,fps={FPS},"
        f"format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[v{idx}]"
    )


def render(video, takes_dir, out_dir, tmp_dir):
    overlay = os.path.join(tmp_dir, f"text_{video['id']}.png")
    text_overlay(video["lines"], overlay)

    cmd = ["ffmpeg", "-y", "-v", "error"]
    for take, start, dur, _ in video["shots"]:
        cmd += ["-ss", f"{start}", "-t", f"{dur}", "-i", os.path.join(takes_dir, f"{take}.MOV")]
    n = len(video["shots"])
    cmd += ["-loop", "1", "-i", overlay]
    total = sum(s[2] for s in video["shots"])
    cmd += ["-f", "lavfi", "-t", f"{total}", "-i", "anullsrc=r=48000:cl=stereo"]

    parts = [shot_filter(i, s[3]) for i, s in enumerate(video["shots"])]
    parts.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[cat]")
    parts.append(f"[cat]{GRADE}[g]")
    parts.append(f"[g][{n}:v]overlay=0:0:shortest=1,format=yuv420p[out]")

    out = os.path.join(out_dir, f"{video['id']}-{video['slug']}.mp4")
    cmd += [
        "-filter_complex", ";".join(parts),
        "-map", "[out]", "-map", f"{n + 1}:a",
        "-t", f"{total}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "10M", "-bufsize", "20M", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "128k",
        out,
    ]
    subprocess.run(cmd, check=True)
    return out


def download(takes_dir):
    os.makedirs(takes_dir, exist_ok=True)
    for name, fid in DRIVE_IDS.items():
        dst = os.path.join(takes_dir, f"{name}.MOV")
        if os.path.exists(dst):
            continue
        url = f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"
        print("baixando", name)
        urllib.request.urlretrieve(url, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--takes", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--download", action="store_true")
    a = ap.parse_args()

    if a.download:
        download(a.takes)
    os.makedirs(a.out, exist_ok=True)
    tmp = os.path.join(a.out, ".tmp")
    os.makedirs(tmp, exist_ok=True)
    for v in VIDEOS:
        if a.only and v["id"] not in a.only:
            continue
        print("render", v["id"], v["slug"], file=sys.stderr)
        print(render(v, a.takes, a.out, tmp))


if __name__ == "__main__":
    main()
