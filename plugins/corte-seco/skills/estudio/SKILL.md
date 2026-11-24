---
name: estudio
description: Edita vídeos falados em português com uma interface visual. Corta pausas, regravações e hesitações, coloca legenda animada com destaque na palavra falada, gancho escrito no início e títulos de seção, e exporta em 1080x1920 pra Reels e TikTok. Use quando a pessoa pedir pra editar, cortar ou legendar um vídeo, tirar silêncios, fazer legenda de reels, ou abrir o estúdio do Corte Seco.
argument-hint: "[caminho do vídeo]"
---

# Corte Seco · estúdio de edição

Você edita o vídeo junto com a pessoa. O trabalho pesado (transcrever, achar regravações,
sugerir gancho, escolher destaques) é seu. A interface no navegador serve pra ela ver o
resultado na hora e ajustar o que quiser com o mouse. Vocês dois mexem no mesmo arquivo
`projeto.json`: o que você muda pela linha de comando aparece na interface sozinho, e o que
ela muda na interface você lê com `texto` e `resumo`.

Fale com a pessoa em português, em tom de conversa, sem jargão técnico. Ela não precisa
saber o que é FFmpeg ou Whisper.

## Caminhos

- Pasta desta skill: `${CLAUDE_SKILL_DIR}`
- Linha de comando: `"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" <comando> ...`
  onde `$PY` é o Python que o instalador devolve. Rode `cli.py --help` se precisar lembrar dos comandos.
- Projetos ficam em `./corte-seco/<nome>/` na pasta atual da pessoa. Os vídeos prontos
  ficam em `./corte-seco/<nome>/exportados/`.
- Preferências da marca e modelos de transcrição ficam em `~/.corte-seco/`.

## 1. Preparar (toda vez, é rápido quando já está pronto)

```bash
python3 "${CLAUDE_SKILL_DIR}/instalar.py"
```

A última linha é um JSON. Com `"ok": true`, guarde o valor de `"python"` como `PY`.

- `"erro"` com `"instalar_ffmpeg"`: o FFmpeg está faltando. Mostre o comando sugerido,
  peça licença pra rodar e rode. No Mac sem Homebrew, explique que é preciso instalar o
  Homebrew antes (https://brew.sh) e espere a pessoa.
- Na primeira vez o instalador leva uns 2 minutos. Avise antes.
- Se `python3` não existir no Windows, tente `py -3`.

## 2. Abrir o vídeo

Se a pessoa não passou o caminho do vídeo, peça. Aceite caminho arrastado pro terminal
(pode vir entre aspas ou com barras invertidas antes dos espaços).

```bash
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" novo "<vídeo>" --nome "<nome curto>"
```

A saída é a pasta do projeto, que aqui vai se chamar `PRJ`. Depois suba a interface **em
segundo plano** (ela fica rodando enquanto vocês trabalham):

```bash
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" servir "$PRJ"
```

Ela abre o navegador sozinha e imprime o endereço (normalmente http://127.0.0.1:4848).
Passe o endereço pra pessoa caso o navegador não abra.

## 3. Transcrever

```bash
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" transcrever "$PRJ"
```

Na primeira vez baixa o modelo de transcrição (cerca de 1,5 GB). Avise que pode demorar
alguns minutos e que das próximas vezes é bem mais rápido. Enquanto isso a interface
mostra o progresso. Hesitações puras ("éé", "hum", "ahn") já saem marcadas como cortadas.

Em computador fraco ou sem espaço, use `--modelo small` (mais leve, erra um pouco mais).

## 4. Fazer a primeira edição

Mostre na interface o que você está fazendo:

```bash
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" status "$PRJ" "procurando regravações"
```

Leia a transcrição numerada:

```bash
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" texto "$PRJ"
```

Cada palavra aparece como `índice:palavra`. `~palavra~` já está cortada e `*palavra*` está
em destaque. As pausas longas aparecem entre colchetes. Então faça, nesta ordem:

**Regravações.** Quando a pessoa começa uma frase, para e começa de novo, corte a tentativa
anterior e fique com a última, que costuma ser a boa. Sinais: o mesmo começo de frase
repetido, frase que termina no meio ("o segundo passo é deixar o... o segundo passo é"),
"peraí", "vou de novo", "corta isso".
```bash
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" cortar "$PRJ" 25-30 --motivo regravação
```

**Vícios de fala.** "tipo", "né", "então", "aí", "sabe", "assim" e "é" usados como muleta.
Corte só quando a palavra não muda o sentido e soa como enchimento, principalmente no começo
da frase ou repetida. Mantenha quando faz parte do jeito da pessoa falar ou quando cortar
deixaria a frase estranha. Na dúvida, mantenha. Use `--motivo vício`.

**Frases soltas.** Comentários fora do roteiro ("deixa eu ver aqui", "tá gravando?") saem
com `--motivo fora do roteiro`.

**Destaques.** Uma ou duas palavras a cada duas ou três linhas: números, a promessa, o
contraste da frase, o nome do produto. Destaque demais faz o destaque perder força.
```bash
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" destacar "$PRJ" 10 19-20
```

**Gancho.** Escreva de 3 a 5 opções de gancho em texto pra tela, baseadas no que a pessoa
realmente fala no vídeo, deixe todas como sugestão e coloque a melhor como gancho:
```bash
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" sugerir "$PRJ" "opção 1" "opção 2" "opção 3"
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" gancho "$PRJ" "opção escolhida"
```
Regras pro gancho: até 9 palavras, concreto e específico (número, situação, resultado), em
minúsculas como a pessoa escreveria, sem ponto de exclamação, sem travessão, sem a fórmula
"não é X, é Y" e sem frase de coach. Use `|` pra quebrar a linha onde fizer sentido.

**Títulos de seção.** Só pra vídeos com mais de 45 segundos e partes claras (passos, dicas,
antes e depois). O número é o índice da palavra onde a seção começa:
```bash
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" titulo "$PRJ" 45 "passo 2"
```

No fim, libere o status e confira os números:
```bash
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" status "$PRJ" "primeira edição pronta" --livre
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" resumo "$PRJ"
```

Conte pra pessoa em poucas linhas o que você fez (quanto tempo o vídeo perdeu, quantas
regravações saíram, qual gancho escolheu) e diga que ela pode ajustar tudo na interface:
clicar nas palavras pra cortar ou destacar, trocar o ritmo, o estilo e as cores.

## 5. Ajustes pedidos no chat

A pessoa pode pedir coisas como "tira a parte que eu falo do preço" ou "deixa mais rápido".
Leia `texto` de novo (ela pode ter mudado coisas na interface), encontre o trecho e use
`cortar`, `manter`, `destacar` ou `ajustar`:

```bash
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" ajustar "$PRJ" --ritmo acelerado
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" ajustar "$PRJ" --estilo editorial --destaque "#FB76B2"
```

Ritmos: `calmo`, `natural`, `acelerado`. Estilos: `pop`, `caixinha`, `editorial`,
`manuscrito`, `impacto`. Outras opções: `--palavras N` (palavras por vez na legenda),
`--posicao 0.64` (altura da legenda), `--enquadramento ajustar` (vídeo horizontal inteiro com
fundo desfocado), `--sem-legenda`.

## 6. Exportar

A pessoa pode exportar pela própria interface. Se pedir pelo chat:

```bash
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" exportar "$PRJ"            # final, 1080x1920
"$PY" "${CLAUDE_SKILL_DIR}/motor/cli.py" exportar "$PRJ" --previa   # rápida, pra conferir
```

Diga onde o arquivo ficou. Se ela mudou estilo, cores ou ritmo e gostou, sugira o botão
"salvar como padrão da marca" na aba estilo, pra os próximos vídeos já começarem assim.

Quando ela disser que terminou, encerre o servidor que ficou rodando em segundo plano.

## Se algo der errado

- Interface não abre: confira se o servidor ainda está rodando e passe o endereço de novo.
  Se a porta 4848 estiver ocupada, ele usa a próxima livre e imprime qual.
- Transcrição com muitos erros de nomes próprios: adicione os termos no projeto (campo
  `termos` do `projeto.json`, lista de palavras) e rode `transcrever` de novo.
- Exportação falhou: a mensagem aparece na aba exportar e no `estado.json` do projeto.
  Os arquivos `legenda.ass` e `filtro.txt` na pasta do projeto ajudam a investigar.
