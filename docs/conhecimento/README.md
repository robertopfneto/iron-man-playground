# Base de conhecimento dos repositórios

Neto e os especialistas consultam a documentação dos repositórios autorizados com pouco contexto por
chamada e referências verificáveis (repositório, caminho, seção, linhas e commit). Os arquivos Markdown no
Git são a fonte oficial. Documentos, seções, relações, índice FTS5 e vetores são derivados e podem ser
reconstruídos a partir deles (`sincronizar_fontes --forcar`).

Código em `api/conhecimento/`. Testes em `api/conhecimento/tests/` (etapas 1 a 4).

## O que foi reaproveitado

| Já existia | Uso aqui |
|---|---|
| `core.Projeto` e `core.Repositorio` | `FonteGit` aponta para um `Repositorio` e herda dele o projeto |
| `core.AcessoAgente` e a sessão Django | escopo da busca: só fontes de projetos em que o agente tem acesso ativo |
| negativa genérica da API | a mesma resposta para projeto inexistente, agente sem acesso e fonte fora do escopo |
| `core/logic.py` (triagem do Neto) | perguntas com documentação indexada recebem resposta com evidência citada |
| fluxo de `Convocacao`/`Turno` | Kernighan recebe os guias afetados por um diff (`/api/conhecimento/guias-afetados`) |
| padrão de management commands e testes | `sincronizar_fontes`, `preparar_fontes_demo`, `comparar_busca` |

## Segurança

- **Somente leitura, sem executar código do repositório.** A ingestão mantém um espelho *bare* por fonte e
  usa só `fetch`, `ls-tree`, `cat-file` e `diff-tree`. Não faz checkout, os hooks ficam desativados e scripts
  nunca rodam.
- **Origem validada.** Só `https://github.com/<conta>/<repositório>` com a conta e o nome cadastrados, ou um
  repositório de demonstração dentro de `CONHECIMENTO_DIR_FONTES_LOCAIS`. Qualquer outra URL ou caminho é
  recusado antes de qualquer acesso.
- **Credencial fora do banco e dos prompts.** `GITHUB_TOKEN_LEITURA` fica no `.env` e chega ao Git por
  variáveis de ambiente, nunca pela linha de comando. Mensagens de erro e o registro de sincronização não
  incluem token nem conteúdo.
- **Permissão antes da recuperação.** A busca calcula as fontes autorizadas (sessão + vínculo do agente)
  antes de consultar FTS5 ou vetores, e verifica de novo ao seguir relações. O texto da pergunta não amplia
  o escopo. Links para repositórios de outro projeto não viram arestas.
- **Before fora da ingestão.** Fonte de projeto com cenário ou nome "Before" fica bloqueada, sem fetch, até
  marcar `autorização explícita` no Admin. Se a autorização for revogada, a fonte some da busca.
- **Embeddings locais.** O Ollama roda no Compose, numa rede (`ia`) que só a API alcança, sem porta
  publicada. Nenhum provedor externo é chamado.

## Configurar as primeiras fontes

1. **Token de leitura.** No GitHub, em *Settings → Developer settings → Fine-grained tokens*, crie um token
   com acesso só aos 2 ou 3 repositórios escolhidos e a permissão **Contents: Read-only** (mais nada).
   Coloque no `.env`, na raiz do projeto, que fica fora do Git:

   ```bash
   GITHUB_TOKEN_LEITURA=github_pat_...
   ```

2. **Modelo de embeddings**, uma vez (~1,2 GB no volume `ollama_modelos`):

   ```bash
   docker compose up -d --wait
   docker compose exec ollama ollama pull bge-m3
   ```

3. **Cadastro** em `http://127.0.0.1:8000/admin/`:
   - *Core → Repositórios*: crie o repositório no projeto certo.
   - *Base de conhecimento → Fontes Git*: escolha o repositório e preencha a conta, o nome no GitHub, a branch
     monitorada e a URL `https://github.com/<conta>/<repositório>.git`. Em **incluir** e **excluir** vão
     padrões glob, um por linha (por exemplo `docs/*` ou `docs/rascunhos/*`), quando quiser restringir os
     caminhos.

4. **Sincronização manual:**

   ```bash
   docker compose exec api python manage.py sincronizar_fontes
   ```

   A saída mostra, por fonte, o SHA anterior → o novo, os arquivos adicionados, alterados, renomeados e
   removidos, e as seções vetorizadas e reaproveitadas. A decisão sobre cada arquivo fica em
   *Admin → Documentos* (coluna **motivo**: `incluido`, `vazio`, `placeholder`, `gerado`, `dependencia`,
   `excluido_por_filtro`, `fora_do_filtro`...).

5. **Sincronização periódica** (`git fetch` a cada 15 minutos, pelo cron do notebook):

   ```cron
   */15 * * * * cd /caminho/do/escritorio && docker compose exec -T api python manage.py sincronizar_fontes >> /tmp/escritorio-sync.log 2>&1
   ```

   Ou, num terminal, `docker compose exec api python manage.py sincronizar_fontes --intervalo 900`.
   O webhook do GitHub fica como extensão futura.

Opções do comando: `--fonte ID` (repetível), `--forcar` (reprocessa sem commit novo, reaproveitando os
vetores) e `--sem-embeddings` (só texto e grafo, se o Ollama estiver fora).

## Como a busca funciona

1. **Escopo**: fontes publicadas dos projetos em que o agente tem acesso ativo, sem as restritas.
2. **Textual (FTS5, sem acentos)**: termos ligados por `OR`. Com 3 ou mais termos, o trecho precisa conter
   pelo menos 2 deles.
3. **Vetorial (bge-m3)**: similaridade de cosseno sobre os vetores das seções autorizadas. Entram só
   trechos com similaridade ≥ 0,45 e a até 0,1 do melhor trecho.
4. **Fusão** por posição (RRF), sem duplicatas.
5. **Grafo**: a partir dos 3 melhores trechos, um salto pelas relações `REFERENCIA`, com a permissão
   verificada de novo.
6. **Orçamento**: até 4 trechos e 2400 caracteres (`CONHECIMENTO_MAX_TRECHOS`,
   `CONHECIMENTO_ORCAMENTO_CARACTERES`, `CONHECIMENTO_LIMIAR_VETORIAL`).

Cada trecho traz repositório, caminho, seção, linhas, commit e link para o commit. Quando nada passa, a
resposta diz que falta evidência autorizada. Se a branch tiver um commit mais novo que o índice (por
exemplo, depois de uma sincronização que falhou), a resposta indica o SHA indexado e o disponível.

Endpoints, todos com sessão:

- `GET /api/conhecimento/busca?projeto_id=&agente_id=&pergunta=&modo=textual|hibrida|hibrida_grafo`
- `POST /api/conhecimento/guias-afetados` com `{projeto_id, diff}`, para o Kernighan
- `GET /api/conhecimento/projetos/{id}/fontes?agente_id=`

## Demonstração (resultados reais, bge-m3 no Ollama do Compose)

Repositórios fictícios em `api/conhecimento/demo/conteudo.py`, criados com
`docker compose exec api python manage.py preparar_fontes_demo`.

**Seleção.** `ferramenta-relatorios` e `notebook-analises` (sem README, mas com guia de uso) foram
indexados. `repo-rascunho` foi ignorado: "Nenhum Markdown útil no commit 73d0ce8ab449 (gerado: 1, vazio: 2)".
O `node_modules/` foi excluído como dependência.

**1. Pergunta real.** "Como instalo a ferramenta de relatórios?" → Neto respondeu com a seção
`Ferramenta de relatórios > Instalação` (`README.md` L5-L15 @ `43ecb63503a7`) e trouxe `AGENTS.md` pelo grafo.
"O que fazer antes de rodar um experimento novo?" → `docs/protocolo-experimento.md#antes-de-rodar`, com
`docs/uso.md` relacionado por link.

**2. Atualização de Markdown.** Um commit trocou `pipx` por `uv`, moveu a ADR para `docs/decisoes/` e
adicionou `docs/publicacao.md`. A sincronização seguinte registrou `43ecb63503a7 -> e06a84772a92 | +1 ~1 >1 -0
| vetorizadas 3, reaproveitadas 10`. A ADR manteve a identidade (mesmo id, caminho novo), a mesma pergunta
passou a citar `uv tool install` @ `e06a84772a92`, e repetir a sincronização deu `sem_mudancas`.

**3. Isolamento.** Do projeto pessoal, a pergunta "a que altura fica a câmera na coleta de imagens em campo?
PROTOCOLO.md protocolos-inovisao talhão" não devolveu nenhum texto, título ou nome do repositório do
INOVISÃO. No próprio INOVISÃO, a mesma pergunta encontra `PROTOCOLO.md > Coleta em campo`. Na API,
Pistori (sem acesso ao projeto pessoal) e um projeto inexistente recebem a mesma resposta:
`404 {"detail": "não encontrado"}`.

## Comparação e decisão

Relatório completo, gerado pelo comando: [`comparacao.md`](comparacao.md). São 15 perguntas: 12 com
resposta, de quatro tipos (comando, direta, paráfrase, multissalto), e 3 sem resposta autorizada.

| Modo | Acerto no topo | Cobertura | Precisão | Falsos positivos | Tempo mediano | Contexto médio |
|---|---|---|---|---|---|---|
| Textual | 58% | 75% | 54% | 0/3 | 2,6 ms | 329 caracteres |
| Híbrida | 83% | 88% | 58% | 1/3 | 206 ms | 491 caracteres |
| Híbrida + grafo | 83% | 92% | 58% | 1/3 | 213 ms | 513 caracteres |

Leitura:

- **A híbrida é necessária.** Paráfrases sobem de 17% para 67% de cobertura, e o acerto no topo de 58% para
  83%. O custo é ~200 ms por pergunta, quase todo no embedding da pergunta no Ollama (medido: 195 ms).
- **O grafo de um salto compensa.** Nas perguntas multissalto a cobertura vai de 75% para 100%, com +22
  caracteres de contexto em média e sem custo de tempo mensurável.
- **Falsos positivos.** A pergunta sobre kubernetes recebe um trecho de "preparar o ambiente" (similaridade
  0,55 no bge-m3, acima de duas perguntas legítimas). Nenhum limiar separa os dois grupos neste conjunto. O
  0,45 foi escolhido por manter as paráfrases.
- **Ressalva.** O limiar, a margem vetorial e a regra de dois termos foram ajustados nessas mesmas 15
  perguntas. Os números servem de referência para o piloto, não de estimativa geral. Refaça a comparação
  com perguntas reais dos seus repositórios: edite `PERGUNTAS` em `api/conhecimento/demo/conteudo.py`, ou
  troque por um arquivo próprio quando as fontes reais entrarem.

**Decisão: não expandir o grafo nem adotar banco vetorial dedicado agora.**

- *Banco vetorial*: a similaridade em Python puro custa 0,096 ms por seção (1 mil seções ≈ 0,1 s; 5 mil ≈
  0,5 s; 20 mil ≈ 1,9 s). Com 2 ou 3 repositórios pessoais, o escopo de uma consulta fica na casa das
  centenas de seções, e o tempo é dominado pelo embedding da pergunta. Revisar quando o escopo de uma
  consulta passar de ~2 mil seções ou o p95 da busca passar de 500 ms. O primeiro passo será vetorizar o
  cálculo (numpy) ou usar `sqlite-vec`, ainda dentro do SQLite. Um serviço dedicado só com vários usuários
  ou dezenas de milhares de seções.
- *Grafo*: manter só as relações `REFERENCIA` verificáveis, com um salto. Expandir (mais saltos ou arestas
  inferidas, como "seção que menciona o comando X") só se as perguntas multissalto reais falharem. Ainda
  assim, cada aresta precisa continuar ligada a um trecho que a sustente.

## Pendências reais

- Ainda não testei com repositórios reais do GitHub. O caminho HTTPS com token está implementado, mas só foi
  exercitado com repositórios locais. O primeiro cadastro real deve confirmar o fetch com o token
  fine-grained.
- A resposta do Neto em modo manual é extrativa (o trecho mais relevante e as fontes). Uma redação por modelo
  local fica para a Entrega 5 (Ollama `/api/chat`), sempre citando as mesmas evidências.
- No chat, o trecho citado aparece como Markdown cru (`##`, cercas de código), ainda sem renderização.
- A revisão do Kernighan já recebe os guias afetados pela API, mas a interface do turno ainda não os mostra
  automaticamente.
