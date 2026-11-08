# Comparação de busca: textual × híbrida × híbrida com grafo

Gerado em 2026-11-07 20:56 por `python manage.py comparar_busca`.

- Projeto: **Projeto pessoal demonstrativo**, agente **Neto**. Perguntas: 15 (12 com resposta, 3 sem resposta autorizada).
- Embeddings: `bge-m3` via Ollama local. Limiar vetorial 0.45, até 4 trechos e 2400 caracteres por consulta.
- Fontes: `ferramenta-relatorios@43ecb63503a7` (ok), `notebook-analises@8bb57c605f05` (ok), `repo-rascunho@73d0ce8ab449` (ignorada). Seções indexadas no projeto: 15.
- Tempo: mediana de 3 execuções por pergunta, depois de aquecer o modelo.

## Resumo

| Modo | Acerto no topo | Cobertura das fontes esperadas | MRR | Precisão dos trechos | Falsos positivos (sem resposta) | Tempo mediano | Contexto médio (caracteres) | Trechos médios |
|---|---|---|---|---|---|---|---|---|
| Textual (FTS5) | 58% | 75% | 0.69 | 54% | 0/3 | 2.6 ms | 329 | 1.5 |
| Híbrida (FTS5 + vetores) | 83% | 88% | 0.88 | 58% | 1/3 | 206.3 ms | 491 | 2.1 |
| Híbrida + grafo (1 salto) | 83% | 92% | 0.88 | 58% | 1/3 | 212.9 ms | 513 | 2.2 |

## Cobertura por tipo de pergunta

| Tipo | Textual (FTS5) | Híbrida (FTS5 + vetores) | Híbrida + grafo (1 salto) |
|---|---|---|---|
| comando | 100% | 100% | 100% |
| direta | 100% | 100% | 100% |
| multissalto | 75% | 75% | 100% |
| paráfrase | 17% | 67% | 67% |

## Detalhe por pergunta

| Pergunta | Tipo | Modo | Primeiro trecho | Cobertura | Via grafo | Tempo | Caracteres |
|---|---|---|---|---|---|---|---|
| pipx install | comando | textual | `ferramenta-relatorios/README.md#instalação` | 100% | 0 | 1.6 ms | 230 |
| pipx install | comando | hibrida | `ferramenta-relatorios/README.md#instalação` | 100% | 0 | 179.4 ms | 230 |
| pipx install | comando | hibrida_grafo | `ferramenta-relatorios/README.md#instalação` | 100% | 0 | 164.5 ms | 230 |
| Como instalo a ferramenta de relatórios? | direta | textual | `ferramenta-relatorios/README.md#ferramenta-de-relatórios` | 100% | 0 | 2.9 ms | 828 |
| Como instalo a ferramenta de relatórios? | direta | hibrida | `ferramenta-relatorios/README.md#instalação` | 100% | 0 | 194.7 ms | 828 |
| Como instalo a ferramenta de relatórios? | direta | hibrida_grafo | `ferramenta-relatorios/README.md#instalação` | 100% | 1 | 201.8 ms | 691 |
| o que preciso fazer para deixar o programa pronto no meu computador | paráfrase | textual | `—` | 0% | 0 | 1.3 ms | 0 |
| o que preciso fazer para deixar o programa pronto no meu computador | paráfrase | hibrida | `notebook-analises/GUIA_DE_USO.md#preparar-o-ambiente` | 0% | 0 | 206.3 ms | 1161 |
| o que preciso fazer para deixar o programa pronto no meu computador | paráfrase | hibrida_grafo | `notebook-analises/GUIA_DE_USO.md#preparar-o-ambiente` | 0% | 1 | 221.8 ms | 1161 |
| ferramenta comparar | comando | textual | `ferramenta-relatorios/docs/uso.md#comparar-rodadas` | 100% | 0 | 2.8 ms | 753 |
| ferramenta comparar | comando | hibrida | `ferramenta-relatorios/docs/uso.md#comparar-rodadas` | 100% | 0 | 180.5 ms | 753 |
| ferramenta comparar | comando | hibrida_grafo | `ferramenta-relatorios/docs/uso.md#comparar-rodadas` | 100% | 0 | 182.7 ms | 633 |
| como saber se a melhora entre duas execuções não foi sorte? | paráfrase | textual | `ferramenta-relatorios/docs/uso.md#comparar-rodadas` | 50% | 0 | 2.2 ms | 221 |
| como saber se a melhora entre duas execuções não foi sorte? | paráfrase | hibrida | `ferramenta-relatorios/docs/uso.md#comparar-rodadas` | 100% | 0 | 227.4 ms | 403 |
| como saber se a melhora entre duas execuções não foi sorte? | paráfrase | hibrida_grafo | `ferramenta-relatorios/docs/uso.md#comparar-rodadas` | 100% | 0 | 229.4 ms | 403 |
| Por que os relatórios saem em JSON e não em planilha? | direta | textual | `ferramenta-relatorios/docs/adr/0001-formato-saida.md#contexto` | 100% | 0 | 2.7 ms | 1000 |
| Por que os relatórios saem em JSON e não em planilha? | direta | hibrida | `ferramenta-relatorios/docs/adr/0001-formato-saida.md#contexto` | 100% | 0 | 231.0 ms | 1122 |
| Por que os relatórios saem em JSON e não em planilha? | direta | hibrida_grafo | `ferramenta-relatorios/docs/adr/0001-formato-saida.md#contexto` | 100% | 1 | 234.9 ms | 1122 |
| quantas sementes cada configuração precisa? | direta | textual | `ferramenta-relatorios/docs/protocolo-experimento.md#repetições` | 100% | 0 | 2.1 ms | 182 |
| quantas sementes cada configuração precisa? | direta | hibrida | `ferramenta-relatorios/docs/protocolo-experimento.md#repetições` | 100% | 0 | 203.2 ms | 390 |
| quantas sementes cada configuração precisa? | direta | hibrida_grafo | `ferramenta-relatorios/docs/protocolo-experimento.md#repetições` | 100% | 1 | 200.3 ms | 611 |
| erro ColunaAusente semente na conversão | multissalto | textual | `ferramenta-relatorios/docs/uso.md#problemas-comuns` | 50% | 0 | 3.0 ms | 235 |
| erro ColunaAusente semente na conversão | multissalto | hibrida | `ferramenta-relatorios/docs/uso.md#problemas-comuns` | 50% | 0 | 219.8 ms | 235 |
| erro ColunaAusente semente na conversão | multissalto | hibrida_grafo | `ferramenta-relatorios/docs/uso.md#problemas-comuns` | 100% | 1 | 212.9 ms | 456 |
| como ativar o ambiente conda do notebook? | direta | textual | `notebook-analises/GUIA_DE_USO.md#preparar-o-ambiente` | 100% | 0 | 3.6 ms | 222 |
| como ativar o ambiente conda do notebook? | direta | hibrida | `notebook-analises/GUIA_DE_USO.md#preparar-o-ambiente` | 100% | 0 | 205.1 ms | 222 |
| como ativar o ambiente conda do notebook? | direta | hibrida_grafo | `notebook-analises/GUIA_DE_USO.md#preparar-o-ambiente` | 100% | 0 | 205.9 ms | 222 |
| que cuidado tomar com as cores dos gráficos impressos? | paráfrase | textual | `—` | 0% | 0 | 2.4 ms | 0 |
| que cuidado tomar com as cores dos gráficos impressos? | paráfrase | hibrida | `notebook-analises/docs/figuras.md#figuras-do-artigo` | 100% | 0 | 213.8 ms | 242 |
| que cuidado tomar com as cores dos gráficos impressos? | paráfrase | hibrida_grafo | `notebook-analises/docs/figuras.md#figuras-do-artigo` | 100% | 0 | 215.5 ms | 242 |
| o que fazer antes de rodar um experimento novo com a ferramenta? | multissalto | textual | `ferramenta-relatorios/README.md#uso-rápido` | 100% | 0 | 3.2 ms | 916 |
| o que fazer antes de rodar um experimento novo com a ferramenta? | multissalto | hibrida | `ferramenta-relatorios/docs/protocolo-experimento.md#antes-de-rodar` | 100% | 0 | 228.7 ms | 1005 |
| o que fazer antes de rodar um experimento novo com a ferramenta? | multissalto | hibrida_grafo | `ferramenta-relatorios/docs/protocolo-experimento.md#antes-de-rodar` | 100% | 1 | 225.9 ms | 1154 |
| regras para agentes antes de propor um diff | direta | textual | `ferramenta-relatorios/AGENTS.md#instruções-para-agentes` | 100% | 0 | 3.2 ms | 341 |
| regras para agentes antes de propor um diff | direta | hibrida | `ferramenta-relatorios/AGENTS.md#instruções-para-agentes` | 100% | 0 | 204.6 ms | 341 |
| regras para agentes antes de propor um diff | direta | hibrida_grafo | `ferramenta-relatorios/AGENTS.md#instruções-para-agentes` | 100% | 0 | 202.9 ms | 341 |
| como configurar o kubernetes com helm? | sem resposta | textual | `—` | ok: sem evidência | 0 | 1.8 ms | 0 |
| como configurar o kubernetes com helm? | sem resposta | hibrida | `notebook-analises/GUIA_DE_USO.md#preparar-o-ambiente` | vazou evidência | 0 | 200.1 ms | 430 |
| como configurar o kubernetes com helm? | sem resposta | hibrida_grafo | `notebook-analises/GUIA_DE_USO.md#preparar-o-ambiente` | vazou evidência | 0 | 205.7 ms | 430 |
| qual a política de reembolso de viagens do grupo? | sem resposta | textual | `—` | ok: sem evidência | 0 | 2.6 ms | 0 |
| qual a política de reembolso de viagens do grupo? | sem resposta | hibrida | `—` | ok: sem evidência | 0 | 213.6 ms | 0 |
| qual a política de reembolso de viagens do grupo? | sem resposta | hibrida_grafo | `—` | ok: sem evidência | 0 | 219.2 ms | 0 |
| a que altura fica a câmera na coleta de imagens em campo? | isolamento | textual | `—` | ok: sem evidência | 0 | 1.4 ms | 0 |
| a que altura fica a câmera na coleta de imagens em campo? | isolamento | hibrida | `—` | ok: sem evidência | 0 | 229.7 ms | 0 |
| a que altura fica a câmera na coleta de imagens em campo? | isolamento | hibrida_grafo | `—` | ok: sem evidência | 0 | 225.0 ms | 0 |
