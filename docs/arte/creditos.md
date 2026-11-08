# Arte do Escritório 2D — autoria, condições de uso e referências

## Autoria e licença

Toda a arte em `web/public/jogo/` (tileset, mapa, sprites, retratos e símbolos) é própria do projeto,
desenhada por código em `web/tools/gerar_assets.py` (só biblioteca padrão do Python). Não há assets de
terceiros. Para regenerar depois de mudar a arte:

```bash
python3 web/tools/gerar_assets.py
```

## Fotos de referência

As fotos de referência são privadas e **não entram no repositório**. Guarde-as em `referencias_privadas/`
(ignorado pelo Git). O gerador não lê fotos: a arte parte das descrições textuais abaixo, e a semelhança
é conferida por revisão humana. Fundos, cartazes, nomes de terceiros e dados visíveis nas fotos ficam fora
dos sprites e das prévias.

## Situação por avatar

| Agente | Homenagem | Arte | Fonte indicada na direção de arte | Imagem escolhida |
|---|---|---|---|---|
| Neto | Roberto Neto | Sprite frontal + retrato propostos, **aguardando revisão** | Fotos privadas do evento | Revisão pendente |
| Pistori | Hemerson Pistori | Sprite frontal + retrato propostos, **aguardando revisão** | Fotos privadas | Revisão pendente |
| Kernighan | Brian Kernighan | Placeholder com símbolo (manual com abas) | Perfil da Universidade de Princeton | Pendente |
| LeCun | Yann LeCun | Placeholder (três camadas) | Perfil da NYU | Pendente |
| Hopper | Grace Hopper | Placeholder (conector de duas pontas) | Fotografia da Marinha dos EUA | Pendente |
| Liskov | Barbara Liskov | Placeholder (caixas encaixadas) | MIT CSAIL | Pendente |
| Lamport | Leslie Lamport | Placeholder (cartões enfileirados) | Conversa da Microsoft Research | Pendente |
| Salton | Gerard Salton | Placeholder (lupa) | IT History Society / memorial de Cornell | Pendente |
| Luhn | Hans Peter Luhn | Placeholder (cartão perfurado) | IT History Society | Pendente |
| Hamming | Richard Hamming | Placeholder (grade com bloco destacado) | Arquivo visual da Univ. de St Andrews | Pendente |
| Knuth | Donald Knuth | Placeholder (caderno aberto) | Kyoto Prize | Pendente |
| Kohavi | Ron Kohavi | Placeholder (duas placas) | Experiment Guide | Pendente |
| Fei-Fei | Fei-Fei Li | Placeholder (visor fechado com ponto) | Stanford HAI | Pendente |
| Torralba | Antonio Torralba | Placeholder (moldura aberta com marcação) | MIT CSAIL | Pendente |
| Torvalds | Linus Torvalds | Placeholder (ramo com três nós) | Galeria da Linux Foundation | Pendente |
| Hamilton | Margaret Hamilton | Placeholder (pilha de pastas) | Smithsonian / NASA | Pendente |
| Papert | Seymour Papert | Placeholder (tartaruga geométrica) | Memorial do MIT Media Lab | Pendente |

Para cada homenagem, quando a arte definitiva for produzida, registre aqui a página consultada, a imagem
escolhida e a autoria ou condição de uso informada.

## Especificação técnica

- Sprites: quadros de 32×48 px, apoio nos pés em (16, 45), mesma proporção corporal e luz de cima/esquerda.
- Retratos: 96×96 px. PNG transparente, exibidos em escala inteira com `image-rendering: pixelated`.
- Poses: só a frontal (`baixo`) existe. As outras três direções aguardam a revisão visual de Neto e Pistori,
  conforme o passo 1 da etapa 4A.
- Prancha de revisão: `docs/arte/revisao_neto_pistori.png` (sprites ×6, retratos ×2, e na escala do mapa ×2 e ×1).
