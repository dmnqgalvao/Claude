# Corte Seco

Um estúdio de edição de vídeo que roda dentro do Claude Code. Você grava o vídeo falando do jeito que sair, com pausa, erro e frase repetida, e o Claude faz a primeira edição: tira as pausas, as regravações e os "éé", coloca legenda animada com a palavra falada em destaque e escreve opções de gancho pro começo. Depois abre uma interface no navegador onde você confere tudo e ajusta com o mouse antes de exportar em 1080 x 1920.

Tudo roda no seu computador. O vídeo não sobe pra servidor nenhum e não tem custo além da sua assinatura do Claude.

## Instalar

No Claude Code:

```
/plugin marketplace add dmnqgalvao/Claude
/plugin install corte-seco@domigalvao
```

Depois é só pedir: `edita esse vídeo pra mim: /caminho/do/video.mp4`, ou chamar `/corte-seco:estudio`.

Na primeira vez o Claude instala o que falta (FFmpeg e o motor de transcrição) e baixa o modelo que entende português, cerca de 1,5 GB. Das próximas vezes começa na hora.

## O que dá pra fazer na interface

- **cortes:** três ritmos prontos (calmo, natural e acelerado de reels) e ajuste fino da pausa máxima e do respiro em volta da fala. Clique ou arraste por cima das palavras pra cortar ou destacar. O que o Claude cortou aparece separado por motivo, com botão pra trazer de volta.
- **texto:** gancho escrito no começo, com as sugestões do Claude a um clique, legenda com número de palavras por vez e altura, e títulos de seção.
- **estilo:** cinco estilos de legenda (pop, caixinha, editorial, manuscrito e impacto), cores da marca e enquadramento pra vídeo gravado na horizontal. Dá pra salvar como padrão da marca.
- **exportar:** prévia rápida pra conferir e vídeo final em 1080 x 1920 com o volume nivelado no padrão do Instagram.

Você também pode pedir ajustes no chat, como "tira a parte em que eu falo do preço" ou "deixa mais rápido", e a interface atualiza sozinha.

## Requisitos

- Claude Code
- Python 3.9 ou mais novo (o Mac e a maioria dos Linux já têm)
- FFmpeg com suporte a legendas. O Claude instala com o Homebrew no Mac, com o winget no Windows ou com o apt no Linux

## Fontes

As fontes das legendas (Poppins, Anton, DM Serif Display e Caveat Brush) e a da interface (Public Sans) têm licença SIL Open Font License, e os arquivos de licença estão junto delas.
