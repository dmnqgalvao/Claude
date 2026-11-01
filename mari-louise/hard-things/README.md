# Mari Louise | série "hard things"

Seis Reels de ~15s, um por frase, no formato da referência do @casey.scharoff7: takes de exaustão no rolo, texto pequeno em serif branca minúscula, centralizado e parado do começo ao fim, cortes secos a cada 2,5 a 3s e uma cor dessaturada.

| # | Arquivo | Frase | Duração |
|:-:|---|---|:-:|
| 01 | `out/01-hobbies-dificeis.mp4` | escolha hobbies difíceis e prove pra si mesma que quem manda na sua cabeça é você. | 14,8s |
| 02 | `out/02-descobrir-do-que-e-capaz.mp4` | escolha coisas que te desafiem o suficiente pra você descobrir do que é capaz. | 15,0s |
| 03 | `out/03-treino-que-queria-abandonar.mp4` | toda vez que você termina um treino que queria abandonar sua mente aprende a confiar um pouco mais em você. | 15,9s |
| 04 | `out/04-go-do-the-hard-thing.mp4` | go do the hard thing before your mind finishes the excuse. | 15,0s |
| 05 | `out/05-do-hard-things-on-purpose.mp4` | do hard things on purpose so life's hard things find you ready. | 15,4s |
| 06 | `out/06-sofrer-por-escolha.mp4` | se é pra sofrer, que seja por escolha minha. | 15,5s |

`previews/` tem uma tira de quadros de cada vídeo pra aprovação rápida.

## O que a referência faz (e foi replicado)

- **Imagem**: só momentos entre os esforços. Cabeça baixa, mão no rosto, mão na cintura, respiração pela boca. Ela nunca aparece pedalando forte, aparece no intervalo em que daria pra desistir, e é isso que deixa a frase com cara de pensamento dela.
- **Texto**: serif fina, minúscula, ponto final, 2 a 4 linhas curtas no centro da tela, tamanho pequeno. Fica parado o vídeo todo, então a pessoa lê no próprio ritmo e o vídeo roda em loop sem perder a frase.
- **Ritmo**: 5 cortes em 15s, sem transição, sem zoom animado. O 04 tem 6 cortes mais curtos porque a frase fala de agir antes da desculpa terminar.
- **Abertura**: cada vídeo abre num take diferente pra o feed não ficar repetido quando postados em sequência.

## Takes usados

Pasta "Vídeo Coros" no Drive da Mari (4K vertical, 30fps). Selecionados pelo trecho de maior exaustão de cada um:

- `IMG_1740` mãos no rosto em cima da Trek (0 a 3,3s) e o olhar que volta pro guidão (3,3 a 5,6s)
- `IMG_1755` close lateral, cabeça baixa e depois erguendo com a boca aberta (3 a 5,6s)
- `IMG_1758` close lateral, cabeça pendurada
- `IMG_1757` frontal, cabeça entre os braços
- `IMG_1754` coque, peito subindo e descendo
- `IMG_1743`, `IMG_1748` frontal no rolo
- `IMG_1745`, `IMG_1746`, `IMG_1756` mão na cintura recuperando o fôlego

Ficaram de fora: `IMG_1744`, `IMG_1747`, `IMG_1750`, `IMG_1753` (planos abertos com janela estourada, a Mari fica pequena no quadro) e `IMG_9740` (externo, de capacete e conversando, foge da estética).

## Tratamento de cor

Aplicado igual nos seis pra virar assinatura da série:

- saturação em 68%, contraste levemente acima
- sombras puxadas pro frio, meios-tons e pele pro quente
- pretos levemente lavados e brancos segurados em 92% (a regata branca vira cinza claro, e o texto branco continua sendo a coisa mais clara da tela)
- vinheta suave e grão fino
- uma sombra muito difusa atrás do bloco de texto, que não aparece como caixa e garante a leitura em qualquer take

## Áudio

Os vídeos saem com trilha muda de propósito. A referência usa música do Instagram, e áudio licenciado só entra direito pelo próprio app: é só abrir o Reel no Instagram/TikTok e escolher o som em alta na hora de postar. Sugestão de linha: algo instrumental, lento e com peso (piano grave ou ambient), no mesmo clima da ref.

## Como refazer ou ajustar

```bash
pip install pillow
python3 build.py --takes ./takes --download          # baixa os takes do Drive e renderiza os 6
python3 build.py --takes ./takes --only 03           # renderiza só um
```

Frase, quebra de linha, takes, trechos e zoom de cada vídeo ficam na lista `VIDEOS` no topo do `build.py`. A grade fica em `GRADE`. Pra adicionar uma frase nova, é só copiar um bloco da lista e trocar texto e takes.
