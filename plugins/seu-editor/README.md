# Seu Editor

Um editor de vídeo que roda dentro do Claude Code. Você grava falando do jeito que sair, com pausa, erro e frase repetida, e o Claude faz a primeira edição inteira: tira as pausas, as regravações e os "éé", coloca legenda animada, escreve opções de gancho, solta palavras de impacto nos momentos certos, encaixa suas fotos e vídeos quando você fala deles e desenha círculos e setas pra apontar o que importa. Depois abre uma interface no navegador onde você confere tudo e ajusta com o mouse antes de exportar em 1080 x 1920.

Tudo roda no seu computador. O vídeo não sobe pra servidor nenhum e não tem custo além da sua assinatura do Claude.

## Instalar

No Claude Code:

```
/plugin marketplace add dmnqgalvao/Claude
/plugin install seu-editor@domigalvao
```

Depois é só pedir: `edita esse vídeo pra mim: /caminho/do/video.mp4`, ou chamar `/seu-editor:editar`.

Na primeira vez o Claude instala o que falta (FFmpeg, o motor de transcrição e um navegador invisível que desenha as camadas) e baixa o modelo que entende português, cerca de 1,5 GB. Das próximas vezes começa na hora.

## O que tem na interface

- **cortes:** ritmo calmo, natural ou acelerado de reels, ajuste fino das pausas, a transcrição pra cortar ou destacar palavras com um clique e a onda do áudio pra cortar direto na linha do tempo. Cortou demais? Tem desfazer e refazer. O que o Claude cortou aparece separado por motivo, com botão pra trazer de volta.
- **camadas:** suas fotos e vídeos (é só arrastar pra dentro), palavras de impacto, desenhos que se desenham sozinhos (círculo, seta, sublinhado, xis, brilhinho), textos fixos, botão de chamada, zoom rápido, tremida, flash, efeitos sonoros (whoosh, pop, ding, clique, impacto, subida) e trilha de fundo que abaixa quando você fala. Tudo numa linha do tempo, presa à fala, e dá pra arrastar cada camada direto na prévia.
- **texto:** gancho com as sugestões do Claude e legenda com fonte, tamanho, cor, contorno, sombra, brilho, fundo, espaço entre linhas e entre letras.
- **estilo:** quatro duplas de fontes prontas (cool, star, basic e glow), troca livre das fontes, envio de fonte própria as cores da marca e a cor do vídeo (correção automática de luz e branco, filtros e ajustes).
- **exportar:** prévia rápida pra conferir e vídeo final em 1080 x 1920 com o volume nivelado no padrão do Instagram.

Também dá pra pedir no chat: "tira a parte em que eu falo do preço", "coloca aquela foto quando eu falo do produto", "quero a fonte Playfair Display". A interface atualiza sozinha.

## Requisitos

- Claude Code
- Python 3.9 ou mais novo
- FFmpeg (o Claude instala com o Homebrew no Mac, com o winget no Windows ou com o apt no Linux)

## Fontes

As fontes que vêm com o plugin (Arimo, Tinos, Anton, Inter Tight, Instrument Serif, Open Sauce Sans, Oswald, Bebas Neue, Bodoni Moda, Bricolage Grotesque, Cabin Sketch, Caveat Brush, Courier Prime, DM Serif Display, Jost, Montserrat, Open Sans, Permanent Marker, Pinyon Script, Poppins e Space Mono) têm licença aberta (SIL Open Font License ou Apache), e os arquivos de licença estão na pasta `fontes`. Helvetica, Times New Roman, Chalkduster, Futura, Bodoni 72 e Bradley Hand vêm instaladas no Mac. Em outros sistemas, entra a fonte aberta parecida. A Bootzy TM é paga e só aparece se você tiver o arquivo dela. Sem ele, entra a Inter Tight.
