---
name: editar
description: Editor de vídeo falado em português com interface visual. Corta pausas, regravações e hesitações, coloca legenda animada, gancho escrito, palavras de impacto, fotos e vídeos inseridos (cartão ou tela cheia), desenhos à mão (círculo, seta, sublinhado) e textos fixos, e exporta em 1080x1920 pra Reels e TikTok. Use quando a pessoa pedir pra editar, cortar ou legendar um vídeo, tirar silêncios, colocar inserts ou b-roll, textos em destaque, ou abrir o Seu Editor.
argument-hint: "[caminho do vídeo]"
---

# Seu Editor

Você edita o vídeo junto com a pessoa. O trabalho pesado é seu: transcrever, achar
regravações, escolher destaques, sugerir gancho e montar as camadas (palavras de impacto,
fotos, desenhos e textos) nos momentos certos da fala. A interface no navegador serve pra
ela ver o resultado na hora e ajustar com o mouse. Vocês dois mexem no mesmo
`projeto.json`: o que você muda pela linha de comando aparece na interface sozinho, e o que
ela muda na interface você lê com `texto`, `camadas` e `resumo`.

Fale com a pessoa em português, em tom de conversa e sem jargão técnico. Ela não precisa
saber o que é FFmpeg, Whisper ou Playwright.

## Caminhos

- Pasta desta skill: `${CLAUDE_SKILL_DIR}`
- Linha de comando: `"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" <comando> ...`
  (`cli.py --help` lista tudo). Aqui embaixo ela aparece abreviada como `ed`.
- Projetos: `./seu-editor/<nome>/` na pasta atual. Fotos e vídeos pra inserir ficam em
  `<projeto>/insertos/`, e os vídeos prontos em `<projeto>/exportados/`.
- Preferências da marca, fontes instaladas e modelos ficam em `~/.seu-editor/`.

## 1. Preparar

```bash
python3 "${CLAUDE_SKILL_DIR}/instalar.py"
```

A última linha é um JSON. Com `"ok": true`, guarde `"python"` como `PY`.
- `"instalar_ffmpeg"` no erro: mostre o comando sugerido, peça licença e rode. No Mac sem
  Homebrew, explique que precisa instalar o Homebrew antes (https://brew.sh).
- Na primeira vez leva alguns minutos (baixa a transcrição e um navegador invisível de uns
  100 MB que desenha as camadas). Avise antes.
- No Windows, se `python3` não existir, tente `py -3`.

## 2. Abrir o vídeo

Se a pessoa não passou o caminho, peça (pode vir arrastado pro terminal, com aspas ou com
barras invertidas antes dos espaços).

```bash
ed novo "<vídeo>" --nome "<nome curto>"      # imprime a pasta do projeto: PRJ
ed servir "$PRJ"                             # rode EM SEGUNDO PLANO, abre o navegador
ed transcrever "$PRJ"                        # 1a vez baixa o modelo (~1,5 GB)
```

O servidor imprime o endereço (normalmente http://127.0.0.1:4848). Passe pra pessoa se o
navegador não abrir. Em computador fraco, use `transcrever "$PRJ" --modelo small`.

Pergunte, sem travar o trabalho, se ela tem fotos, prints ou vídeos pra inserir. Ela pode
arrastar na aba "camadas" ou você copia os arquivos pra `$PRJ/insertos/`.

## 3. Primeira edição

Mostre na interface o que você está fazendo: `ed status "$PRJ" "procurando regravações"`.
Leia a transcrição: `ed texto "$PRJ"`. Cada palavra aparece como `índice:palavra`,
`~palavra~` já está cortada e `*palavra*` está em destaque. Então:

**Regravações.** Quando a pessoa começa uma frase, para e começa de novo, corte a tentativa
anterior e fique com a última. Sinais: o mesmo começo repetido, frase interrompida, "peraí",
"vou de novo". `ed cortar "$PRJ" 25-30 --motivo regravação`

**Vícios de fala.** "tipo", "né", "então", "aí", "sabe", "assim" usados como muleta: corte só
quando não mudam o sentido e soam como enchimento. Na dúvida, mantenha. `--motivo vício`.
Comentários fora do roteiro ("tá gravando?") saem com `--motivo fora do roteiro`.

**Destaques da legenda.** Uma ou duas palavras a cada duas ou três linhas: números, a
promessa, o nome do produto. `ed destacar "$PRJ" 10 19-20`

**Gancho.** Escreva de 3 a 5 opções curtas, baseadas no que a pessoa fala, e deixe a melhor:
```bash
ed sugerir "$PRJ" "opção 1" "opção 2" "opção 3"
ed gancho "$PRJ" "opção escolhida"
```
Regras: até 9 palavras, concreto (número, situação, resultado), minúsculas, sem ponto de
exclamação, sem travessão, sem "não é X, é Y" e sem frase de coach. `|` quebra a linha.

**Camadas.** Monte as camadas com `ed camada "$PRJ" '<json>'` (devolve o id). Toda camada que
acompanha a fala usa `"palavra": <índice>` e fica presa a essa palavra mesmo depois de novos
cortes. Use com critério: um vídeo de 30 segundos fica bom com 2 a 4 palavras de impacto,
fotos quando a pessoa cita algo que dá pra mostrar e um desenho pra apontar o que importa.

Antes de usar fotos e vídeos, rode `ed insertos "$PRJ"` e **olhe cada imagem** (leia o
arquivo) pra entender o que ela mostra. Encaixe a foto no momento em que a pessoa fala daquilo.

Campos comuns: `palavra` (ou `ini` em segundos do vídeo editado), `duracao`, `x` e `y`
(centro, de 0 a 1), `tamanho`, `rot` (graus), `entrada` (`pop`, `desliza`, `fade`,
`escreve`, `nenhuma`), `ate_o_fim: true` pra ficar até o fim.

```bash
# palavra de impacto: jeitos pincel, condensado, estilo (fonte de destaque) ou etiqueta
ed camada "$PRJ" '{"tipo":"impacto","estilo":"pincel","texto":"estratégia","palavra":42,"duracao":1.8,"y":0.42,"ligar":true}'
# foto em cartão flutuando (ou "modo":"tela" pra tela inteira com zoom lento)
ed camada "$PRJ" '{"tipo":"imagem","arquivo":"print.jpg","modo":"cartao","palavra":42,"duracao":2.5,"x":0.72,"y":0.28,"tamanho":0.34,"rot":6}'
# vídeo inserido (b-roll), sem som; "inicio_clip" escolhe o trecho
ed camada "$PRJ" '{"tipo":"video","arquivo":"broll.mp4","modo":"tela","palavra":60,"duracao":3,"inicio_clip":2}'
# desenho que se desenha sozinho: circulo, seta, sublinhado, x, brilho
ed camada "$PRJ" '{"tipo":"desenho","forma":"circulo","cor":"#E8352E","palavra":42,"duracao":2,"x":0.5,"y":0.45,"tamanho":0.7}'
# texto fixo: titulo, frase, apoio, cta (botão), etiqueta, anotacao
ed camada "$PRJ" '{"tipo":"texto","estilo":"cta","texto":"comenta EU QUERO","ini":0,"ate_o_fim":true,"y":0.82}'
```

**Ganchos visuais e sonoros.** Use poucos e nos pontos certos: um zoom na frase mais forte,
uma tremida ou flash numa virada, e som junto com as entradas importantes.
```bash
# zoom rápido (estilo "suave" ou "seco"), tremida ou flash
ed camada "$PRJ" '{"tipo":"efeito","efeito":"zoom","palavra":42,"duracao":1.2,"intensidade":1.2,"x":0.5,"y":0.4}'
ed camada "$PRJ" '{"tipo":"efeito","efeito":"flash","palavra":60,"duracao":0.35}'
# efeito sonoro sozinho: whoosh, pop, ding, clique, impacto, subida
ed camada "$PRJ" '{"tipo":"som","som":"whoosh","palavra":60,"volume":0.8}'
# ou som na entrada de qualquer camada
ed camada "$PRJ" '{"id":"imp4k2xz","som":"pop"}'
```
Trilha de fundo: a música fica em `insertos/` e abaixa sozinha quando a pessoa fala.
`ed trilha "$PRJ" musica.mp3 --volume 0.14` (`--sem-abaixar` desliga o abaixamento).

**Cor.** `ed cor "$PRJ" --auto` acerta luz e balanço de branco olhando o vídeo. Filtros:
`--filtro quente|frio|vivo|suave|filme|pb`, e ajustes finos com `--brilho 0.03`,
`--contraste 1.1`, `--saturacao 1.2`, `--temperatura 0.3` (-1 a 1). Rode o `--auto` em
todo vídeo gravado com luz de casa, que costuma sair amarelado ou escuro.

**Corte por tempo.** Pra tirar um trecho que não tem fala (barulho, cena parada),
`ed cortar-tempo "$PRJ" 12.5 14.2` (segundos do vídeo original). A pessoa também corta
arrastando na onda do áudio, na aba cortes, e tem botão de desfazer.

`"ligar": true` na palavra de impacto desenha linhas dela até as fotos em cartão que estão na
tela ao mesmo tempo (o efeito de mapa mental). Pra mudar uma camada, mande o `id` com os
campos novos: `ed camada "$PRJ" '{"id":"imp4k2xz","y":0.3}'`. Pra listar: `ed camadas "$PRJ"`.
Pra apagar: `ed remover "$PRJ" <id>`.

Evite a área que o Instagram cobre: nada importante acima de `y` 0.11, abaixo de 0.79 ou
encostado na direita (`x` acima de 0.87) entre 0.47 e 0.79.

No fim: `ed status "$PRJ" "primeira edição pronta" --livre` e `ed resumo "$PRJ"`. Conte em
poucas linhas o que fez (quanto tempo saiu, regravações, gancho escolhido, camadas criadas)
e diga que ela ajusta tudo na interface: clicar nas palavras, arrastar camadas na prévia e
na linha do tempo, trocar fontes, cores e contorno.

## 4. Estilo, fontes e cores

Cada estilo é uma dupla de fontes: **destaque** (gancho, títulos, palavras de impacto) e
**texto** (legenda, frases, botões). Estilos prontos: `cool` (Bootzy TM + Helvetica),
`star` (Open Sauce Bold + Courier New Bold), `basic` (condensada Oswald + Futura) e `glow`
(Helvetica Bold + Instrument Serif).

```bash
ed estilo "$PRJ" glow
ed estilo "$PRJ" --destaque bodoni --texto opensans   # dupla personalizada
ed fontes                                             # ids de todas as fontes
```

Se a pessoa pedir uma fonte que não está na lista, instale do Google Fonts pelo nome, ou
pelo arquivo se ela tiver um:
```bash
ed fonte "Playfair Display"
ed fonte ~/Downloads/MinhaFonte.otf --nome "Minha Fonte"
```
O comando imprime o id (ex.: `p-playfair-display`), que serve em `estilo --destaque`,
`estilo --texto` ou no `"fonte"` de um visual. Fontes pagas (como a Bootzy TM) só
funcionam se a pessoa tiver o arquivo. Sem ele, entra uma fonte gratuita parecida
(a Bootzy TM, que é paga, vira Inter Tight).

Visual da legenda (JSON parcial, só o que mudar):
```bash
ed legenda "$PRJ" '{"cor":"#FFFFFF","contorno":true,"espessura":6,"cor_contorno":"#000000","cor_destaque":"#FFD84D","modo_ativa":"cor","palavras":3}'
```
Campos de visual (servem pra legenda e pro `"visual"` de camadas de impacto e texto):
`fonte` (id, `@destaque` ou `@texto`), `tamanho` (px numa tela de 1080), `cor`,
`caixa_alta`, `italico`, `contorno`, `espessura`, `cor_contorno`, `sombra`, `brilho`,
`fundo` (`nenhum`, `caixa`, `pilula`), `cor_fundo`, `entrelinhas` (ex.: 1.1),
`espacamento` (espaço entre letras, -10 a 40). Só da legenda: `cor_destaque`,
`modo_ativa` (`cor`, `fundo`, `nenhum`), `animacao` (`pop`, `fade`, `nenhuma`), `palavras`.

Outros ajustes: `ed ajustar "$PRJ" --ritmo acelerado` (`calmo`, `natural`, `acelerado`),
`--posicao 0.64` (altura da legenda), `--enquadramento ajustar` (vídeo horizontal inteiro
com fundo desfocado), `--sem-legenda`.

## 5. Pedidos no chat

"Tira a parte do preço", "coloca uma foto quando eu falo do produto", "deixa a legenda
maior": leia `texto` e `camadas` de novo (ela pode ter mudado coisas na interface), encontre
o trecho e use `cortar`, `manter`, `destacar`, `camada`, `legenda`, `estilo` ou `ajustar`.

## 6. Exportar

A pessoa pode exportar pela interface. Pelo chat:
```bash
ed exportar "$PRJ"            # final, 1080x1920
ed exportar "$PRJ" --previa   # rápida, pra conferir
```
Um vídeo de 1 minuto leva de 1 a 3 minutos pra exportar, porque cada quadro com camada é
desenhado. Diga onde o arquivo ficou. Se ela gostou de fontes, cores e ritmo, sugira o botão
"salvar como padrão da marca" na aba estilo. Quando ela terminar, encerre o servidor que
ficou em segundo plano.

## Se algo der errado

- Interface não abre: confira se o servidor ainda roda e passe o endereço de novo.
- Exportação falhou: a mensagem aparece na aba exportar. Os arquivos `filtro.txt` e
  `ffmpeg.log` na pasta do projeto mostram o detalhe.
- Erro do navegador invisível ("Executable doesn't exist"): rode
  `"$PY" -m playwright install chromium --only-shell`.
- Nomes próprios errados na legenda: adicione os termos na lista `termos` do `projeto.json`
  e rode `transcrever` de novo.
