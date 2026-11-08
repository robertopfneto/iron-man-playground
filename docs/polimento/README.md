# Polimento visual: etapas 1 e 2

Plano: `plano_polimento_visual_iron_man_playground.md`. Esta rodada cobre o diagnóstico, os tokens e a
hierarquia da tela. A arte de Neto e Pistori (etapa 3) aguarda revisão; as etapas 4 a 6 vêm depois da
aprovação desta proposta.

## Capturas (dados de demonstração)

| Tamanho | Antes | Depois |
|---|---|---|
| 1440 × 900 | `antes-1440x900.png` | `depois-1440x900.png` |
| 1024 × 768 | `antes-1024x768.png` | `depois-1024x768.png` |
| 390 × 844 (viewport emulada) | `antes-390x844.png` | `depois-390x844.png` |

## Diagnóstico do antes

- A sala ocupava uma fração da tela: a cena media a largura uma única vez, na montagem, e ficava em zoom 1
  (448 px) dentro de um card largo. Os rótulos das áreas ficavam ilegíveis.
- A hierarquia estava invertida: o chat vazio ocupava uma coluna inteira, e a ficha e as decisões ficavam
  soltas embaixo, sem indicar o próximo passo.
- Não havia ação principal visível. O azul era usado tanto nos botões quanto nos estados.
- Os turnos convocados viviam só no chat. Ao recarregar a página, sumiam da interface, embora estivessem
  salvos no banco.
- No celular, a página abria rolada para baixo, porque o chat rolava a página inteira.

## Referência de composição

```
┌ Escritório 2D │ Projeto ▾ · Recepção, reunião e trabalho │ Equipe │ [Conversar com Neto] │ usuário Sair ┐
├──────────────────────────────────────────────────────────────┬──────────────────────────────────┤
│ SALA (maior área, zoom inteiro, pixels nítidos)               │ [Conversa com Neto] [Ficha · X]  │
│  Recepção ─── Sala de reunião (ponto focal) ─── Trabalho      │                                  │
│  legenda: ○ disponível  🔔 convocado  ▶ em andamento ...       │  chat preservado ao alternar     │
├───────────────────────────┬──────────────────────────────────┤  ficha: retrato, agente,         │
│ EQUIPE (lista, teclado)   │ ATIVIDADES                       │  homenagem, papel, estado        │
│ símbolo · nome · estado   │ ▌PRÓXIMO PASSO (âmbar)           │                                  │
│                           │ turnos para colar · decisões     │  painel ~360 px                  │
└───────────────────────────┴──────────────────────────────────┴──────────────────────────────────┘
≤ 1180 px: o painel desce para baixo da sala. ≤ 760 px: a barra quebra em linhas, "Conversar com Neto" fica no topo
e a sala rola dentro do card, em zoom 1.
```

## Tokens (`web/src/styles.css`, `:root`)

| Papel | Token | Valor |
|---|---|---|
| Fundo (grafite) | `--bg` | `#15171c` |
| Superfícies (azul acinzentado) | `--surface`, `--surface-2`, `--surface-3` | `#1c222b`, `#232b36`, `#2c3643` |
| Texto | `--text`, `--text-muted` | `#e9edf2`, `#96a2b3` |
| Acento: seleção e ação primária (âmbar) | `--accent` | `#f0a83a` |
| Estados (cor + ícone + texto) | `--st-disponivel` … `--st-concluido` | cinza, azul, verde-água, lilás, verde |
| Espaçamentos | `--space-1` … `--space-6` | 4 a 24 px |

No Phaser, os mesmos valores ficam em `ESTADO_COR` e `COR_SELECAO` (`web/src/room/avatares.ts`).

**Tipografia.** Fonte do sistema para todo o texto, controles e títulos. A identidade vem do peso (800 na
marca), do tamanho e das versais com espaçamento nos títulos de seção. A fonte pixel não foi adotada: só
valeria no nome do escritório ou nas placas do mapa, e exigiria versionar uma fonte com licença. Fica como
opção para depois. Os acentos foram conferidos em "RECEPÇÃO", "SALA DE REUNIÃO", "ÁREA DE TRABALHO" e
"INOVISÃO".

## O que mudou

- A cena Phaser recalcula o zoom com `ResizeObserver` e usa sempre escala inteira. Em telas estreitas fica
  em 1× e rola dentro do card, sem rolagem horizontal da página. Os rótulos têm tamanho mínimo legível, e a
  seleção usa um anel âmbar.
- A barra superior tem o projeto, o espaço atual, o acesso à equipe e a ação principal
  **Conversar com Neto**.
- O painel de contexto tem abas (Conversa com Neto / Ficha). A conversa continua montada ao alternar.
- Equipe: lista compacta com símbolo, nome e estado, navegável com Tab, setas e Enter. Selecionar pela lista
  ou pelo mapa sincroniza os dois e abre a ficha.
- Atividades: o **próximo passo** real, os turnos abertos com campo para colar a entrega e as decisões
  propostas com "Aprovar decisão". Aprovar continua sendo uma ação separada da seleção. Vem do endpoint novo
  `GET /api/projetos/{id}/convocacoes-abertas` e sobrevive à recarga.
- O chat rola só a própria lista de mensagens.

## Verificado em execução

- 1440, 1024 e 390: sem rolagem horizontal da página (largura do conteúdo ≤ largura da janela) e página
  abrindo no topo.
- Seleção pelo teclado na equipe: destaque na lista, anel no mapa e ficha aberta.
- Volta ao chat com a conversa intacta (pergunta, resposta e 4 fontes) e foco no campo.
- INOVISÃO: as convocações abertas reapareceram depois da recarga. Ao fechar o turno de Pistori pelas
  Atividades, ele voltou ao posto com estado concluído, Kohavi seguiu convocado e o próximo passo avançou.
- Suíte do backend: 63 testes passando.

## Pendente, aguardando você

- **Arte de Neto e Pistori (etapa 3).** Não abro as fotos de referência (regra de dados pessoais). A
  fidelidade fica pendente da sua comparação privada com `docs/arte/revisao_neto_pistori.png`. Diga o que
  ajustar (cabelo, rosto, óculos, bigode, cavanhaque, roupa). As poses adicionais só depois da aprovação.
- Etapas 4 a 6: animações leves e o marcador de "revisão" no mapa, citações em Markdown renderizado com
  **Abrir fonte**, guias afetados no cartão do Kernighan e a validação final.
