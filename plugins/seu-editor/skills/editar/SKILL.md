---
name: editar
description: Edita vídeos falados em português (Reels, TikTok, Shorts) com interface visual. Palavra mágica "tcham" — quando a pessoa escrever "tcham" (ex. "edita o vídeo com tcham", "tcham nesse vídeo", "tcham no estilo da Marina"), use SEMPRE esta skill. Use também sempre que ela pedir pra editar, cortar, legendar, montar ou deixar pronto pra postar um vídeo, do jeito que escrever, ou citar o Seu Editor. O vídeo pode vir como link do Google Drive ou Dropbox, caminho, arquivo arrastado ou só uma descrição ("o que acabei de gravar", "tá nos downloads"). Corta pausas e regravações, coloca legenda, gancho, destaques, insertos, zoom, sons e cor, e exporta em 1080x1920.
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

## 2. Entender o pedido e achar o vídeo

A pessoa escreve do jeito dela, sem comando e sem caminho. Tire do pedido:
- **qual vídeo**: caminho, arquivo arrastado, ou uma descrição ("o que acabei de gravar",
  "o último que baixei", "o vídeo da tarita", "o do triathlon no desktop")
- **estilo**: nome de cliente ou de jeito ("no estilo da Marina", "igual o da Tarita"), um
  dos 4 padrão, ou nada
- **insertos**: link do Drive, Dropbox, pasta ou "as fotos que estão na pasta tal"
- **pedidos soltos**: "bem dinâmico", "sem legenda", "acelera um pouco", "com música",
  "coloca o print da Forbes quando eu falar do dado" etc.

**"tcham"** é a palavra mágica da pessoa: sempre que aparecer, o pedido é pra este editor.

Se veio um **link** (Google Drive, Dropbox ou link direto), passe o link direto pro `novo`:
ele baixa o vídeo pra `~/Downloads/seu-editor/` e cria o projeto. Se o link for uma pasta
com vários vídeos, o maior vira o vídeo principal e os outros vão pros insertos.
```bash
ed novo "https://drive.google.com/file/d/..." --nome "tarita 02"
```
O link precisa estar compartilhado como "qualquer pessoa com o link". Se o download
falhar por permissão, peça pra pessoa mudar o compartilhamento.

Se a pessoa disse onde está ("tá nos downloads", "na pasta da Tarita no desktop"), procure
lá. Se não veio caminho nenhum, ache o vídeo você mesmo, sem perguntar onde está:
```bash
ed achar-video              # os 5 mais recentes (Downloads, Desktop, Movies, Documents)
ed achar-video "tarita"     # por parte do nome
```
Pegue o que bate com a descrição (o mais recente pra "acabei de gravar" ou "último") e diga
em uma linha qual arquivo vai editar, já começando o trabalho. Só pergunte se houver
dúvida real entre dois arquivos. "Bem dinâmico" quer dizer mais zoom nos cortes, mais
destaques e insertos mais curtos. "Mais calmo" quer dizer o contrário.

```bash
ed novo "<vídeo>" --nome "<nome curto>"      # imprime a pasta do projeto: PRJ
ed servir "$PRJ"                             # rode EM SEGUNDO PLANO, abre o navegador
ed transcrever "$PRJ"                        # 1a vez baixa o modelo (~1,5 GB)
```

**Vários arquivos no mesmo projeto.** Takes, clipes de vlog e narração entram juntos numa
linha do tempo só, na ordem em que você passar:
```bash
ed novo take1.mov take2.mov take3.mov --nome "dica 03"        # takes ou clipes de vlog
ed novo ~/Downloads/vlog-lisboa --nome lisboa --ordem data     # pasta: todos, pela data
ed novo "<link da pasta do Drive>" --todos --nome lisboa       # pasta do Drive inteira
ed novo fotos/*.jpg broll.mp4 --narracao fala.m4a --nome praia # narração: insertos + áudio
```
- `--ordem nome` ou `--ordem data` quando a pessoa não disse a ordem. Pasta vem pela data.
- Depois de transcrever, os vídeos sem fala viram trechos de imagem (ficam 2,5 s do meio).
  Veja com `ed arquivos "$PRJ"` e troque com
  `ed arquivo-modo "$PRJ" 2 imagem --manter 3.0 4` (começa em 3 s e fica 4 s) ou
  `ed arquivo-modo "$PRJ" 2 fala`.
- Em takes repetidos, o `texto` mostra cada arquivo separado. Fique com a melhor versão
  de cada frase (normalmente a última) e corte as outras.
- **Vídeo narrado**: a pessoa manda a narração (áudio do celular, .m4a, .mp3, ou até um
  vídeo, do qual só o som é usado; arquivo, pasta ou link do Drive) e as imagens (clipes e
  fotos, também por link ou pasta). Passe a narração em `--narracao` e as imagens como
  arquivos normais: elas vão pros insertos. Se ela mandar só a narração, pergunte pelas
  imagens; se mandar só imagens, pergunte pela narração antes de montar.
  ```bash
  ed novo "<link ou pasta das imagens>" --narracao "<arquivo ou link da narração>" --nome praia
  ed transcrever "$PRJ"
  ed preencher "$PRJ" --cada 1.2      # um inserto a cada ~1 s, entrando no começo de uma palavra
  ```
  O jeito da referência de narrado: 100% imagem, um corte a cada ~1 s no começo de uma
  palavra (no meio da frase também), tela cheia, sem zoom, cortes secos, pausas da narração
  cortadas. Clipes repetidos continuam de onde pararam, sem mostrar a mesma imagem duas
  vezes. Use `--modo metade`, `--de 10 --ate 30` pra um trecho só. Depois de preencher,
  troque o inserto de cada trecho pra combinar com o que a narração diz (leia `camadas` e
  o `texto`): a imagem tem que ilustrar a frase.

O servidor imprime o endereço (normalmente http://127.0.0.1:4848). Passe pra pessoa se o
navegador não abrir. Em computador fraco, use `transcrever "$PRJ" --modelo small`.

Pergunte, sem travar o trabalho, se ela tem fotos, prints ou vídeos pra inserir. Ela pode
arrastar na aba "camadas", colar um link do Google Drive ali, ou mandar o link no chat:
`ed buscar-insertos "$PRJ" "<link do Drive, Dropbox, link direto ou pasta do computador>"`.
O link do Drive precisa estar compartilhado como "qualquer pessoa com o link".

## 2.5. Estilo do vídeo

O estilo vem do pedido da pessoa. As receitas de cliente não aparecem na interface: elas só
existem quando a pessoa pede no chat.

- **A pessoa citou um estilo** ("no estilo da marina", "do jeito triathlon", "igual ao
  último da tarita"): rode `ed receitas`, ache a receita com esse nome e aplique com
  `ed receita-aplicar "$PRJ" "marina"`. O comando imprime as **regras da receita**, que
  valem mais que as orientações padrão da etapa 3: siga à risca palavras de impacto, zoom,
  sons, tipo de gancho, ritmo, insertos e CTA. Se a receita pede cor automática, rode
  `ed cor "$PRJ" --auto`. Se não existir receita com esse nome, diga isso e siga o que a
  pessoa descreveu.
- **A pessoa não citou estilo**: use os 5 estilos padrão, `cool`, `star`, `basic`, `glow` e
  `domi` (Alte Haas Grotesk Bold + Open Sauce, o estilo da Domi). Enquanto a transcrição
  roda, pergunte em uma linha qual deles ela quer. Se ela não
  responder, siga com o padrão da marca (ou `cool`) e lembre que ela troca na aba estilo.
- **A pessoa descreveu um jeito novo** e gostou do resultado: ofereça salvar como receita,
  pra pedir pelo nome da próxima vez:
  `ed receita-salvar "nome" --projeto "$PRJ" --descricao "resumo curto" --regras "o que ela pediu, escrito como regra"`.
- **A pessoa corrigiu algo que deve valer sempre** naquele estilo ("na marina a legenda é
  sempre amarela", "nunca usa flash"): leia com `ed receita-ver "nome"`, reescreva as regras
  com a correção e salve com `ed receita-salvar "nome" --regras "texto completo"`
  (acrescente `--projeto "$PRJ"` se o visual também mudou).

## 3. Primeira edição

Mostre na interface o que você está fazendo: `ed status "$PRJ" "procurando regravações"`.
Leia a transcrição: `ed texto "$PRJ"`. Cada palavra aparece como `índice:palavra`,
`~palavra~` já está cortada e `*palavra*` está em destaque. Então:

**Regravações.** A transcrição já marca sozinha as regravações (a pessoa começa a frase, erra
e fala de novo: corta a tentativa anterior inteira, desde a primeira palavra) e os gaguejos
("a a", "pro produzir"). Elas aparecem cortadas no `texto` e na aba cortes. Mesmo assim:
1. leia o texto procurando o que sobrou: frase que termina no meio e começa de novo logo
   depois, pedaço de frase repetido, "peraí", "vou de novo", "não, pera". A regra é
   **cortar a tentativa errada do começo dela até logo antes da tentativa boa**. Não corte
   só o começo: se sobrar meia frase errada, a pessoa ouve.
2. confira se o detector não cortou repetição de propósito (anáfora, ênfase). Se cortou,
   devolva com `ed manter "$PRJ" 40-46`.
3. **revisão obrigatória, frase por frase**: rode `ed revisar "$PRJ"`. Ele mostra o texto
   que ficou, uma frase por linha com os índices, e marca com ⚠ o que parece erro: frase
   que começa igual a uma anterior, frase parecida com a seguinte, frase que termina no
   meio com pausa, palavra repetida perto e palavra que o reconhecimento entendeu mal
   (fala embolada costuma ser palavra errada que ela corrigiu logo depois). Leia TODAS as
   frases, não só as marcadas, como se fosse a pessoa assistindo: qualquer pedaço que ela
   regravaria, qualquer palavra trocada que ela corrigiu na sequência ("o meu... a minha"),
   qualquer frase que não faz sentido sozinha sai. Rode `ed revisar` de novo depois de
   cortar e só siga quando não sobrar nenhum erro. Esse é o diferencial do editor: a pessoa
   não pode precisar caçar erro na revisão dela.
```bash
ed cortar "$PRJ" 25-30 --motivo regravação
ed regravacoes "$PRJ"             # roda o detector de novo (depois de mexer na transcrição)
ed regravacoes "$PRJ" --refazer   # desfaz o que o detector marcou e procura de novo
ed regravacoes "$PRJ" --desfazer  # tira todos os cortes automáticos de regravação
```

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
# foto em cartão (ou "modo":"tela" pra tela inteira com zoom lento)
# moldura: polaroid, fita, arredondada, celular, sem (png recortado)
# movimento: flutua, aproxima, gira | entrada: pop, desliza, cai, esquerda, direita, fade
ed camada "$PRJ" '{"tipo":"imagem","arquivo":"print.jpg","modo":"cartao","moldura":"celular","movimento":"flutua","entrada":"direita","palavra":42,"duracao":2.5,"x":0.72,"y":0.28,"tamanho":0.34,"rot":6}'
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
# efeito sonoro sozinho: pop, clique, camera, whoosh, ding, impacto, subida
# (e os sons que a pessoa enviou; `ed sons --listar` mostra todos)
ed camada "$PRJ" '{"tipo":"som","som":"camera","palavra":60,"volume":0.5}'
# ou som na entrada de qualquer camada
ed camada "$PRJ" '{"id":"imp4k2xz","som":"pop"}'
```
Sons automáticos: cada momento tem o seu som e dá pra trocar qualquer um.
```bash
# padrão: destaque alterna pop e clique, palavra-chave e cascata = pop,
# texto na tela = clique, foto ou vídeo que entra = camera, CTA = pop
ed sons "$PRJ" --foto camera --destaque pop,clique --palavra clique --volume 0.8
ed sons "$PRJ" --texto nenhum      # tira o som de um momento
ed sons "$PRJ" --desligar          # desliga os sons automáticos
```
A pessoa também envia os próprios sons pela interface (aba estilo, card da trilha,
"+ enviar meu som"). Eles ficam em `~/.seu-editor/sons/` e valem pra todos os vídeos.
Trilha de fundo: a música fica em `insertos/` e abaixa sozinha quando a pessoa fala.
`ed trilha "$PRJ" musica.mp3 --volume 0.14` (`--sem-abaixar` desliga o abaixamento).

**Cor.** Os estilos de cor da pessoa foram medidos nas edições dela no CapCut e viraram
filtros `.cube` (LUT 3D), aplicados igual na prévia e no vídeo final:
- `quente-suave` (o padrão): quase natural, esquenta a pele sem amarelar a imagem. Pra
  especialista falando, vídeo de autoridade e publi em que a cor do produto precisa ser fiel.
- `dourado-quente` (se estiver instalado): o mais quente, luz amarela e pele bronzeada,
  "fim de tarde". Pra fala sentada em casa ou escritório, depoimento, conteúdo pessoal.
- `pessego-vibrante`: o mais colorido, pele rosada, escurece e assenta o preto. Pra dica
  e nicho com cenário claro e lavado. Com roupas ou objetos muito vermelhos, use
  intensidade 0.6 a 0.8, senão o vermelho puxa pro laranja.
- `doc-contraste` (documentário): preto bem fundo e luz amarelada. Pra muito b-roll,
  fotos de arquivo e prova esportiva.
- `frio` (frio limpo) e `cinema`: os dois que não esquentam a luz. Frio pra praia, água,
  tecnologia e saúde; cinema (sombra azul-esverdeada, pele quente) pra história e atleta.
`ed cor "$PRJ" --filtro pessego-vibrante --intensidade 0.8`. A pessoa sempre puxa a pele
pro pêssego, escurece a imagem sem estourar o branco e nunca deixa a pele amarela ou
pálida: se for ajustar à mão, vá nessa direção. Nitidez leve (0.3 a 0.5) faz o papel do
"4K" do CapCut. `--auto` acerta luz e branco antes do filtro, pra vídeo com luz de casa.
Vídeo de iPhone em HDR é convertido sozinho pra cor normal antes do filtro.
Filtros novos em `.cube` entram pelo botão "enviar filtro" na aba estilo.

**Corte por tempo.** Pra tirar um trecho que não tem fala (barulho, cena parada),
`ed cortar-tempo "$PRJ" 12.5 14.2` (segundos do vídeo original). A pessoa também corta
arrastando na onda do áudio, na aba cortes, e tem botão de desfazer.

**Atrás da pessoa.** Qualquer palavra de impacto, texto, foto, vídeo ou desenho pode ficar
atrás de quem fala com `"atras": true`. O plugin recorta a pessoa do vídeo sozinho (na
primeira vez baixa um modelo de 25 MB). Funciona melhor em plano médio ou aberto, com
espaço acima da cabeça ou dos lados. Cada trecho atrás leva alguns segundos a mais pra
exportar, então use nos momentos que valem.
```bash
ed camada "$PRJ" '{"tipo":"impacto","estilo":"condensado","texto":"42 KM","palavra":12,"duracao":2.5,"y":0.28,"tamanho":1.6,"atras":true}'
```

**Foto esmaecendo.** `"opacidade": 0.6` deixa a foto transparente, `"esfumar": 0.6` some
com as bordas, `"entrada": "fadelento"` aparece e some devagar. Combinados, a foto parece
uma lembrança se misturando com o vídeo. Molduras sem borda: `"moldura": "nenhuma"` (só a
foto) ou `"sombra"` (só a foto com sombra).

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

## Padrão de edição (o jeito da Domi, medido em 11 projetos reais)

Quando a pessoa pede algo específico na mensagem, ou cita um estilo de cliente, faça
isso. Quando não pede, este é o padrão. Projeto novo já nasce com corte seco, zoom nos
cortes, legenda no formato abaixo, destaque que substitui a legenda, sons automáticos e
cor quente e nítida. **Velocidade fica normal**: só acelere (1,1× a 1,3×) se a pessoa pedir.

**Corte.** Ritmo `seco` (tira toda pausa a partir de ~0,14 s, sem sobrar ar entre as
frases). Toda frase refeita sai, fica a última versão. Nenhuma transição. Se o vídeo
começa com "oi", apresentação ou "deixa eu ver", corte: o vídeo abre direto no gancho.

**Zoom.** O zoom nos cortes já vem ligado e respeita a frase: o plano só muda quando
começa uma frase nova (dentro da mesma frase todos os cortes ficam no mesmo zoom), alterna
normal e fechado, nunca dois fechados seguidos. O recorte do plano fechado centraliza o
rosto (achado sozinho na transcrição; `ed rosto "$PRJ"` refaz) e o vídeo fica parado: nada
de zoom animado ou tremida sem a pessoa pedir, ela grava de tripé e movimento à toa
derruba a retenção. A pontuação da transcrição define as frases: se uma frase longa
precisar de troca de plano no meio, é sinal de que a pontuação veio errada. Na fala sentada ou de perto, use 1,3 a 1,5
(`ed ajustar "$PRJ" --zoom-cortes 1.4`). Em plano aberto, 1,08 a 1,12. Em selfie andando,
pessoa recortada ou vídeo só de narração com imagens, desligue (`--zoom-cortes 1`). Na
frase de maior ênfase, faça uma escada de zoom: `{"tipo":"efeito","efeito":"escada","palavra":N,"duracao":2.5}`.

**Legenda corrida.** 2 a 3 palavras, uma linha, minúsculas, sem pontuação, branca e pequena
no terço de baixo, sempre no mesmo lugar, com fade em cada bloco (já é o padrão). Nos
vídeos que não pedem legenda corrida (frase, documentário com narração, vídeos com texto
forte só nos momentos-chave), desligue com `--sem-legenda` e use cascata.

**Destaque.** A palavra destacada aparece sozinha, ~1,8× maior, na fonte de destaque, no
lugar da legenda. Marque com `ed destacar`:
- o conceito-chave (substantivo, nunca verbo de ligação nem artigo), 1 a 2 palavras
- itens de lista e ordinais ("primeiro", "segundo", "terceiro")
- nomes próprios e o nome do lugar ou do produto
- **sempre** a palavra do CTA ("plano", "link", a palavra-chave pra comentar)
- um destaque a cada 2 a 4 segundos (18% a 30% dos blocos)
Fonte e cor do destaque vêm do estilo (os 4 padrão ou o estilo de cliente que a pessoa
citou). Não escolha fonte por conta própria.

**Cascata (sem legenda corrida).** No gancho e em 4 a 7 momentos-chave, as palavras
entram uma a uma empilhadas e saem juntas, grandes, na fonte de destaque do estilo:
`{"tipo":"cascata","linhas":[{"texto":"orçamento","palavra":3},{"texto":"de fachada","palavra":5}],"y":0.3,"variar":true}`.
Cada linha ganha um pop baixinho logo antes, sozinho. As linhas ficam quase encostando;
`"espaco"` afasta ou aproxima (1 é o padrão, 0,7 bem junto, 1,5 solto).

**Gancho.** O título-gancho (caixa sólida no terço de cima, 5 a 6 s) repete a
primeira frase falada, que é o gancho. Existem modelos de abertura prontos (veja
"Modelos de abertura" abaixo); escolha o que combina com o vídeo. Ou reforce o gancho com um inserto de prova em meia
tela nos primeiros segundos. O gancho tem que aparecer na imagem nos primeiros 2 a 6 s.

**Modelos de abertura.** A fonte do título é sempre a de destaque do estilo; a linha
pequena e a etiqueta usam a fonte de texto. `|` quebra a linha e `*palavra*` marca o
destaque. A pessoa troca o modelo e o texto na aba texto, card "gancho escrito".
| modelo | como fica | use quando |
|---|---|---|
| `caixa` | caixa colorida no terço de cima, 5,5 s | padrão, dica e serviço |
| `texto` | título grande no peito (y 0,64), etiqueta em pílula entra em 1,4 s, 5 s | lista, opinião ("trends que eu não compro") |
| `rosto` | frase curta no meio da tela, na frente do rosto, 2 s | frase de efeito, citação |
| `imagens` | linha inclinada + título em caixa alta, 2 a 6 fotos nas bordas entrando uma a uma, 4,2 s (com `--imagens-atras` elas ficam atrás da pessoa recortada, bom quando ela aparece de longe) | resultado, prova, "como transformar..." com prints |
| `icones` | linha pequena + palavra gigante com estrelas e brilhos em volta da cabeça, 4,5 s | tema de uma palavra ("fontes", "ferramentas") |
| `palavras` | a fala do começo aparece uma palavra por vez, destaques grandes, 3 s | gancho falado forte, sem título |
```bash
ed gancho "$PRJ" "trends que eu|*não* compro" --modelo texto --etiqueta "letras ilegíveis"
ed gancho "$PRJ" "deixa eles|*saberem*" --modelo rosto
ed gancho "$PRJ" "seus seguidores|viram uma *comunidade*" --modelo imagens --linha "como transformar" --imagens print1.png print2.png print3.png print4.png
ed gancho "$PRJ" "*fontes*" --modelo icones --linha "roube essas" --icones estrela brilho --cor-icones "#FB76B2"
ed gancho "$PRJ" "" --modelo palavras
```
Ícones: estrela, brilho, estrela-contorno, coracao, nuvem, raio, seta, circulo, ou o nome de
uma imagem dos insertos (png transparente). Nos modelos fora da `caixa` a legenda some
durante a abertura; `--legenda-junto` mantém. Sugira o texto, mas mostre na interface pra
pessoa trocar. Os 4 vídeos de referência das aberturas abrem com o título já inteiro na tela
e saem num corte seco junto com um corte do vídeo: combine a `--duracao` com um corte.

**Insertos.**
- *Prova ou contexto*: 1,7 a 4 s, trocando a cada ~2 s quando a pessoa cita algo.
- *Pano de fundo*: 10 a 15 s em meia tela enquanto ela fala.
- O jeito preferido é a **meia tela** (`"modo":"metade"`, `"lado":"cima"` ou `"baixo"`),
  com a pessoa falando na outra metade. Tela cheia só por 1 a 2 s.
- Fotos com movimento lento ("aproxima"). Sem animação de entrada nos insertos de tela
  cheia ou meia tela.
- Vídeos documentário (história, atleta, lugar) têm de 30 a 40 insertos por minuto. Fala
  com prova, de 12 a 15. Fala pura, de 0 a 5.

**Som.** Os sons automáticos acompanham o texto, nunca o corte, sempre macios e baixinhos
por baixo da voz: pop e clique alternando nos destaques, pop na palavra-chave e na
cascata, clique no texto na tela, câmera quando entra foto ou vídeo e pop no CTA. A
pessoa não gosta de som escrachado: não use whoosh, ding, impacto nem subida a não ser
que ela peça. Não coloque música no vídeo, a não ser que a pessoa
peça (ela entra depois, no Instagram).

**Cor.** Estilo `quente-suave` com nitidez leve (já é o padrão); troque pelo estilo que
combina com o vídeo, conforme a seção Cor acima. Rode `ed cor "$PRJ" --auto`
em vídeo gravado com luz de casa. Na confissão ou na virada da história, coloque preto e
branco por 1 a 7 s: `{"tipo":"efeito","efeito":"pb","palavra":N,"duracao":3}`.

**Roteiro.** Você não muda o que a pessoa falou, mas a edição segue a estrutura dela:
- gancho de 1 frase (até 5 s) que contradiz, pergunta, alerta, imagina uma cena ou traz
  um dado com contraste
- desenvolvimento em lista de 3 ("primeiro / segundo / terceiro", com os números em
  destaque) ou em ordem cronológica, com uma frase de virada antes do fim
- CTA nos últimos ~6 s, com a palavra-chave em destaque e um pop
Se o gancho não estiver no começo da gravação, mas existir mais pra frente, avise a pessoa
e sugira começar o vídeo nele.

**Por tipo de vídeo, quando a pessoa não diz nada:**
- *Especialista dando dica (sentada)*: legenda corrida, destaque branco, zoom 1,3 a 1,5,
  insertos de prova em meia tela, lista de 3 em destaque.
- *Lugar, evento ou desejo (narração com imagens)*: legenda corrida com destaques
  frequentes (1 a cada ~2 s, alternando as duas fontes de destaque se o estilo tiver),
  insertos a cada ~2 s, pessoa recortada com fotos em volta (`"atras": true`), sem zoom.
- *História, atleta ou documentário*: sem legenda corrida, insertos curtos em meia tela e
  tela cheia, preto e branco na virada, sem zoom quando a pessoa está recortada.
- *Opinião ou relato pessoal*: cascata no gancho e nas viradas, escada de zoom na frase
  mais forte, preto e branco na confissão.
- *Serviço ou empresa*: palavras-chave em pares (cascata curta), título-gancho em caixa,
  pop no CTA.

Depois de montar, gere a prévia (`ed exportar "$PRJ" --previa`), olhe 3 ou 4 quadros e
corrija o que ficou poluído, ilegível ou fora do lugar antes de mostrar pra pessoa.

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

Outros ajustes: `ed ajustar "$PRJ" --ritmo seco` (`seco`, `calmo`, `natural`, `acelerado`),
`--velocidade 1.2` (só se a pessoa pedir), `--zoom-cortes 1.4` (1 desliga), `--sons-auto nao`,
`--posicao 0.64` (altura da legenda), `--enquadramento ajustar` (vídeo horizontal inteiro
com fundo desfocado), `--sem-legenda`.

**Enquadramento.** Quando a pessoa ficou cortada, fora do centro ou longe demais, ajuste
o quadro do arquivo em vez de refazer a edição. `zoom` 1 é o vídeo cabendo certinho na
tela; `x` e `y` escolhem qual parte aparece (0 = esquerda/topo, 0,5 = centro, 1 =
direita/baixo). Cada arquivo guarda o seu.
```bash
ed enquadrar "$PRJ" --zoom 1.25 --x 0.7          # arquivo 1, aproxima e puxa pra direita
ed enquadrar "$PRJ" --arquivo 2 --y 0.3          # mostra mais a parte de cima
ed enquadrar "$PRJ" --arquivo todos --centro     # volta tudo ao centro
```
Na interface: aba estilo, card enquadramento, "mexer no enquadramento". Aí ela arrasta
o vídeo dentro do celular e usa a rodinha ou o controle de zoom.

## 5. Pedidos no chat

"Tira a parte do preço", "coloca uma foto quando eu falo do produto", "deixa a legenda
maior": leia `texto` e `camadas` de novo (ela pode ter mudado coisas na interface), encontre
o trecho e use `cortar`, `manter`, `destacar`, `camada`, `legenda`, `estilo` ou `ajustar`.
"Troca o som das fotos por clique", "tira os sons": `sons`. "Eu fiquei cortada",
"centraliza", "aproxima mais": `enquadrar` (pergunte o arquivo só se houver vários e não
der pra saber pelo contexto).

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
