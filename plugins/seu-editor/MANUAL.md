# Seu Editor: manual de instalação e uso

> O Seu Editor é um editor de vídeo falado que roda dentro do Claude. Você grava do jeito que sair, com pausa, erro e frase repetida, pede a edição com a palavra mágica **tcham** e recebe a primeira versão pronta: cortes, legenda, gancho, destaques, insertos, sons e cor. Depois confere tudo numa interface no navegador e exporta em 1080 x 1920. O vídeo fica no seu computador o tempo todo e não sobe pra servidor nenhum.

## 1. O que você precisa

- **Claude com assinatura** (Pro ou Max) e o **app do Claude no Mac**, usando a aba **Code**. Também funciona no Claude Code pelo terminal.
- **Um Mac**, de preferência. Windows e Linux funcionam, mas a ferramenta foi pensada e testada no Mac.
- **Uns 2 GB livres** no computador. Na primeira vez a ferramenta instala o FFmpeg (o programa que monta o vídeo), o leitor de português e um navegador invisível que desenha os textos.
- **Homebrew** no Mac. Se você não tiver, o Claude avisa e explica como instalar em [brew.sh](https://brew.sh).

## 2. Instalar

### Pelo app do Claude no Mac (jeito mais fácil)

1. Abra o app do Claude, vá na aba **Code** e comece uma **sessão nova**, em qualquer pasta do seu computador.
2. Cole esta mensagem inteira e envie:

```
Instala o plugin "seu-editor" do marketplace "domigalvao" pra mim. O marketplace está no GitHub em dmnqgalvao/Claude, no branch claude/eager-galileo-xl2wpq.
Primeiro tenta pelo terminal:
claude plugin marketplace add dmnqgalvao/Claude#claude/eager-galileo-xl2wpq
claude plugin install seu-editor@domigalvao
Se o comando claude não existir no terminal, edita o arquivo ~/.claude/settings.json (sem apagar nada do que já tem lá) e acrescenta:
"extraKnownMarketplaces": {"domigalvao": {"source": {"source": "github", "repo": "dmnqgalvao/Claude", "ref": "claude/eager-galileo-xl2wpq"}}}
e
"enabledPlugins": {"seu-editor@domigalvao": true}
No fim me diz se deu certo.
```

3. Quando o Claude disser que deu certo, **feche essa sessão e abra outra**. É na sessão nova que o editor passa a funcionar.

### Pelo terminal (Claude Code)

Se você usa o Claude Code no terminal, rode os dois comandos dentro dele:

```
/plugin marketplace add dmnqgalvao/Claude#claude/eager-galileo-xl2wpq
/plugin install seu-editor@domigalvao
```

> No app do Mac, digitar /plugin abre a tela de configurações de plugins em vez de rodar o comando. Por isso o jeito mais simples no app é pedir pro Claude instalar, como no passo a passo acima.

## 3. A primeira edição

Na primeira vez que você pedir uma edição, o Claude prepara tudo sozinho: instala o que falta e baixa o modelo que entende português, com cerca de 1,5 GB. Isso leva alguns minutos e só acontece uma vez. Se ele pedir pra instalar o FFmpeg, pode autorizar.

## 4. Como pedir uma edição

Abra uma sessão nova na aba Code e escreva do seu jeito, usando a palavra mágica **tcham** (também vale tchan ou tchã). Ela avisa o Claude que é pra usar o Seu Editor e não outra ferramenta.

**Exemplos:**

- edita esse vídeo com tcham + o link do Google Drive
- tcham no vídeo que tá nos downloads
- edita com tcham o que eu acabei de gravar
- tcham no estilo da Marina (se você já salvou um estilo com esse nome)

**Onde pode estar o vídeo:**

- **Link do Google Drive ou Dropbox:** o arquivo precisa estar compartilhado como "qualquer pessoa com o link".
- **Caminho ou pasta do computador:** é só dizer onde está, tipo "na pasta da Tarita no desktop".
- **Nada:** o Claude procura o vídeo mais recente em Downloads, Desktop, Filmes e Documentos e te diz qual vai editar.

**O que dá pra pedir junto:**

- "bem dinâmico" ou "mais calmo"
- "sem legenda"
- "acelera um pouco" (a velocidade normal é o padrão)
- "com música"
- "coloca o print da Forbes quando eu falo do dado"
- um dos 5 estilos de fonte prontos: **cool, star, basic, glow ou domi** (Alte Haas Grotesk Bold com Open Sauce)

Se você não disser o estilo, o Claude pergunta qual dos 5 você quer enquanto o vídeo é transcrito.

Quando a primeira edição fica pronta, a interface abre sozinha no navegador. Se não abrir, o Claude te passa o endereço (normalmente http://127.0.0.1:4848).

## 5. Tipos de vídeo

### Vídeo falado pra câmera

O caso mais comum. O Claude corta pausas, "éé", regravações e gaguejos, faz uma revisão frase por frase pra não sobrar pedaço de frase errada, escreve o gancho, marca os destaques, coloca zoom nos cortes centralizando o seu rosto e aplica a cor. O zoom só muda quando começa uma frase nova, pra não quebrar o raciocínio no meio.

### Vários takes ou vlog

Mande todos os arquivos juntos, uma pasta inteira ou o link de uma pasta do Drive. Eles entram numa linha do tempo só, na ordem em que foram gravados. Quando você repetiu a mesma frase em takes diferentes, o Claude fica com a melhor versão. Clipes sem fala (paisagem, b-roll) viram trechos curtos de imagem.

### Vídeo narrado

Mande a narração (áudio do celular, mp3, m4a ou até um vídeo, do qual só o som é usado) e as imagens (clipes e fotos), por arquivo, pasta ou link. Peça, por exemplo: "tcham, vídeo narrado, a narração tá nesse link e as imagens nessa pasta". O Claude corta as pausas e os erros da narração, coloca uma imagem a cada 1 segundo mais ou menos, sempre entrando no começo de uma palavra, escolhe cada imagem pelo que a narração diz e usa a legenda empilhada palavra por palavra.

## 6. A interface, aba por aba

### 01 cortes

- **Ritmo:** seco, calmo, natural ou acelerado, mais o ajuste fino das pausas.
- **Velocidade:** normal, 1,1, 1,2, 1,3 ou um valor exato.
- **Transcrição:** clique nas palavras pra cortar, trazer de volta ou destacar na legenda.
- **Onda do áudio:** dá pra cortar direto na linha do tempo.
- **O que o Claude cortou:** aparece separado por motivo (hesitação, regravação, gaguejo), com botão pra trazer de volta.
- **Desfazer e refazer:** botões em cima da prévia.

### 02 camadas

Tudo o que entra por cima do vídeo fica aqui.

- **Seus insertos:** envie fotos e vídeos, arraste do computador ou cole um link do Drive. Clique num inserto pra colocar no ponto em que o vídeo está.
- **Botões pra adicionar:** palavra de impacto, desenho (círculo, seta, sublinhado), texto, botão de chamada, zoom/tremida/flash, cascata de palavras e efeito sonoro. Cada camada nasce no ponto atual do vídeo e fica presa àquela fala, mesmo se você cortar mais coisa depois.
- **Linha do tempo:** clique numa faixa (ou no texto na prévia) pra abrir o editor da camada. Arraste a faixa pra mudar quando entra e puxe a ponta pra mudar a duração.
- **Editor da camada:** troca texto, fonte, tamanho, cor, entrada, posição, moldura das fotos, foto atrás de você, foto esmaecendo. Tem os botões **duplicar** e **apagar** (a tecla Delete também apaga).
- **Trilha e sons:** música de fundo que abaixa quando você fala, e os sons automáticos (pop, clique, câmera). Você escolhe o som de cada momento, ouve antes, regula o volume e pode enviar seus próprios sons.

> O destaque da legenda (a palavra que você marca no texto) é diferente dos textos que entram por cima. O destaque você mexe na aba cortes ou texto. Palavras de impacto, cascatas e textos você mexe aqui na aba camadas.

### 03 texto

- **Gancho escrito:** escolha um dos seis modelos de abertura pela miniatura e troque o texto.
  - **caixa colorida:** caixa no terço de cima.
  - **só texto:** título grande no peito, com uma etiqueta que entra depois.
  - **na frente do rosto:** frase curta no meio da tela.
  - **imagens:** fotos nas bordas entrando uma a uma, com opção de ficarem atrás de você.
  - **ícones:** palavra gigante com estrelas e brilhos em volta da cabeça.
  - **palavra por palavra:** a sua fala do começo, uma palavra de cada vez.
- **Dicas do gancho:** use | pra quebrar a linha e \*asteriscos\* em volta da palavra de destaque. As sugestões do Claude aparecem logo abaixo, é só clicar.
- **Legenda:** formato corrida ou empilhada (palavra por palavra), palavras por vez, altura, cor do destaque, fonte, contorno, sombra, fundo e espaço entre linhas e letras.

### 04 estilo

- **Fontes:** os 5 estilos prontos, troca livre das fontes e envio de fonte própria.
- **Cor do vídeo:** seus filtros (quente suave, pêssego vibrante, documentário, mais frio limpo e cinema), correção automática de luz e branco e envio de filtro .cube.
- **Enquadramento:** "mexer no enquadramento" deixa você arrastar o vídeo dentro do celular e dar zoom com a rodinha do mouse. Cada arquivo guarda o seu. Sem ajuste manual, o editor já centraliza o seu rosto.
- **Formato:** preencher a tela ou vídeo inteiro com fundo desfocado.

### 05 exportar

- **Prévia rápida:** pra conferir cortes, camadas e legenda.
- **Vídeo final:** 1080 x 1920, com o volume nivelado no padrão do Instagram.

O arquivo fica na pasta exportados, dentro da pasta do projeto.

## 7. Pedidos no chat

Tudo o que dá pra fazer na interface também dá pra pedir no chat, na mesma sessão. A interface atualiza sozinha. Alguns exemplos:

- tira a parte em que eu falo do preço
- coloca aquela foto quando eu falo do produto
- muda o gancho pro modelo com ícones
- troca o som das fotos por clique
- eu fiquei cortada, centraliza
- deixa a legenda maior e amarela
- procura as regravações de novo
- quero a fonte Playfair Display

**Estilos de cliente:** depois de editar um vídeo do jeito de um cliente, peça "salva esse estilo como Marina". Das próximas vezes, "tcham no estilo da Marina" já começa com as fontes, cores, legenda e regras desse estilo. Esses estilos ficam guardados só no seu computador e não aparecem na interface.

## 8. Atualizar pra versão nova

Numa sessão da aba Code, peça: "atualiza o plugin seu-editor do marketplace domigalvao". Depois feche a sessão e abra outra. Pelo terminal, o comando é /plugin marketplace update domigalvao.

## 9. Se algo der errado

- **O "tcham" não chamou o editor:** confira se você abriu uma sessão nova depois de instalar ou atualizar.
- **O link do Drive não baixou:** mude o compartilhamento do arquivo pra "qualquer pessoa com o link".
- **A interface não abriu:** peça "abre a interface do seu editor de novo" ou copie o endereço que o Claude mostrou.
- **Sobrou erro de fala no vídeo:** peça "revisa os erros desse vídeo de novo" ou clique na palavra na aba cortes.
- **A fonte não é a esperada:** algumas fontes pagas ou do Mac (como a Alte Haas Grotesk) só aparecem se estiverem instaladas no seu computador. Sem elas, entra uma parecida. Você pode enviar o arquivo da fonte na aba estilo.
- **Qualquer outra coisa:** conte pro Claude o que aconteceu, do seu jeito. Ele olha o registro de erros do projeto e resolve.
