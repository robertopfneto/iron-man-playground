"""Repositórios fictícios para demonstrar e comparar a base de conhecimento.

Nenhum dado real: os textos foram escritos para o piloto. Os repositórios reais
entram depois, cadastrados no Admin com URL do GitHub e token de leitura.
"""

FERRAMENTA_RELATORIOS = {
    "README.md": """# Ferramenta de relatórios

Converte as planilhas de resultado dos experimentos em relatórios padronizados para o grupo.

## Instalação

A ferramenta é instalada isolada do Python do sistema:

```bash
pipx install ferramenta-relatorios
ferramenta --versao
```

Se o `pipx` não existir na máquina, instale antes com `python3 -m pip install --user pipx`.

## Uso rápido

```bash
ferramenta converter resultados.csv --saida relatorio.json
```

Detalhes de cada opção estão no [guia de uso](docs/uso.md#converter). O formato de saída segue a
[decisão de arquitetura sobre JSON](docs/adr/0001-formato-saida.md). Antes de rodar um experimento novo,
siga o [protocolo experimental](docs/protocolo-experimento.md).

## Contribuindo

Rode os testes com `pytest -q` e leia as [instruções para agentes](AGENTS.md) antes de abrir um pull request.
""",
    "docs/uso.md": """# Guia de uso

## Converter

`ferramenta converter <entrada.csv> --saida <arquivo>` lê a planilha, valida as colunas obrigatórias
(`experimento`, `semente`, `metrica`, `valor`) e grava o relatório. A extensão do arquivo de saída define
o formato: `.json` (padrão) ou `.md` para uma tabela legível.

```bash
ferramenta converter resultados.csv --saida relatorio.md --titulo "Rodada de março"
```

## Comparar rodadas

`ferramenta comparar a.json b.json` mostra a diferença das métricas entre duas rodadas, com intervalo de
confiança por bootstrap (1000 reamostragens). Use para decidir se uma mudança melhorou de fato.

## Problemas comuns

Se aparecer `ColunaAusente: semente`, a planilha veio de uma versão antiga do notebook. Reexporte pelo
[notebook de análises](https://github.com/demo/notebook-analises/blob/main/GUIA_DE_USO.md#exportar-resultados).
""",
    "docs/adr/0001-formato-saida.md": """# ADR 0001: relatórios em JSON

## Contexto

Os scripts de análise do grupo consomem os resultados de várias rodadas ao mesmo tempo, e a planilha
perdia a tipagem das colunas numéricas quando passava por editores de planilha.

## Decisão

O formato padrão de saída é JSON com chaves em snake_case e números sem formatação local. A tabela em
Markdown existe só para leitura humana e nunca é usada como entrada de outro script.
""",
    "docs/protocolo-experimento.md": """# Protocolo experimental

## Antes de rodar

Fixe a semente em `config.yaml`, registre o commit do código e confira se o conjunto de validação é o
mesmo da rodada anterior. Experimentos sem semente registrada não entram na comparação.

## Repetições

Cada configuração roda com cinco sementes. Reporte média e desvio padrão, e use
[comparar rodadas](uso.md#comparar-rodadas) para checar se a diferença é real ou ruído.
""",
    "AGENTS.md": """# Instruções para agentes

Este repositório aceita mudanças pequenas e revisadas. Rode `pytest -q` antes de propor um diff, não
altere o formato de saída sem uma ADR nova e atualize o README quando um comando mudar.
""",
    "node_modules/leftpad/README.md": "# leftpad\n\nDocumentação de uma dependência JavaScript copiada por engano para o repositório.\n",
}

FERRAMENTA_ATUALIZACAO = {
    "escrever": {
        "README.md": FERRAMENTA_RELATORIOS["README.md"]
        .replace("pipx install ferramenta-relatorios", "uv tool install ferramenta-relatorios")
        .replace(
            "Se o `pipx` não existir na máquina, instale antes com `python3 -m pip install --user pipx`.",
            "Se o `uv` não existir na máquina, instale antes com `curl -LsSf https://astral.sh/uv/install.sh | sh`.",
        )
        .replace("docs/adr/0001-formato-saida.md", "docs/decisoes/0001-formato-saida.md"),
        "docs/publicacao.md": """# Publicação de versões

Para publicar uma versão, atualize o número em `pyproject.toml`, gere o pacote com `uv build` e crie a tag
`vX.Y.Z`. A publicação no índice interno é feita pela automação depois da revisão do pull request.
""",
    },
    "mover": {"docs/adr/0001-formato-saida.md": "docs/decisoes/0001-formato-saida.md"},
    "mensagem": "troca pipx por uv, move ADRs para docs/decisoes e documenta publicação",
}

NOTEBOOK_ANALISES = {
    "GUIA_DE_USO.md": """# Guia do notebook de análises

## Preparar o ambiente

Crie o ambiente com `conda env create -f ambiente.yml` e ative com `conda activate analises`. O kernel do
Jupyter se chama `analises` e precisa estar selecionado antes de abrir o notebook principal.

## Exportar resultados

Execute todas as células de `principal.ipynb` em ordem. A última célula grava `resultados.csv` com as
colunas `experimento`, `semente`, `metrica` e `valor`, prontas para a ferramenta de relatórios.
""",
    "docs/figuras.md": """# Figuras do artigo

As figuras são geradas pela função `gerar_figuras()` no fim do notebook e gravadas em `figuras/` com 300 dpi.
Use a paleta acessível definida em `estilo.mplstyle` para que as cores funcionem em impressão em tons de cinza.
""",
}

REPO_RASCUNHO = {
    "README.md": "# repo-rascunho\n",
    "notas/TODO.md": "# Em breve\n\nTODO: documentar.\n",
    "CHANGELOG.md": "<!-- generated by release-please -->\n# Changelog\n\n## 0.1.0\n- versão inicial gerada automaticamente.\n",
}

PROTOCOLOS_INOVISAO = {
    "PROTOCOLO.md": """# Protocolo de coleta de imagens

## Coleta em campo

As imagens são capturadas com a câmera fixa a 1,5 m, entre 9h e 11h, para reduzir sombras. Cada lote
recebe o código do talhão e a data no nome do arquivo.

## Anotação

A anotação segue o guia de classes do laboratório, com revisão cruzada de 10% das imagens por outro anotador.
""",
}

CONTA_DEMO = "demo"

# (nome, projeto, arquivos)
REPOSITORIOS = [
    ("ferramenta-relatorios", "Projeto pessoal demonstrativo", FERRAMENTA_RELATORIOS),
    ("notebook-analises", "Projeto pessoal demonstrativo", NOTEBOOK_ANALISES),
    ("repo-rascunho", "Projeto pessoal demonstrativo", REPO_RASCUNHO),
    ("protocolos-inovisao", "INOVISÃO", PROTOCOLOS_INOVISAO),
]

# Perguntas da comparação, com as seções que respondem (repositório/caminho#âncora; âncora vazia = qualquer seção).
PERGUNTAS = [
    {"pergunta": "pipx install", "esperado": ["ferramenta-relatorios/README.md#instalação"], "tipo": "comando"},
    {
        "pergunta": "Como instalo a ferramenta de relatórios?",
        "esperado": ["ferramenta-relatorios/README.md#instalação"],
        "tipo": "direta",
    },
    {
        "pergunta": "o que preciso fazer para deixar o programa pronto no meu computador",
        "esperado": ["ferramenta-relatorios/README.md#instalação"],
        "tipo": "paráfrase",
    },
    {"pergunta": "ferramenta comparar", "esperado": ["ferramenta-relatorios/docs/uso.md#comparar-rodadas"], "tipo": "comando"},
    {
        "pergunta": "como saber se a melhora entre duas execuções não foi sorte?",
        "esperado": [
            "ferramenta-relatorios/docs/uso.md#comparar-rodadas",
            "ferramenta-relatorios/docs/protocolo-experimento.md#repetições",
        ],
        "tipo": "paráfrase",
    },
    {
        "pergunta": "Por que os relatórios saem em JSON e não em planilha?",
        "esperado": ["ferramenta-relatorios/docs/adr/0001-formato-saida.md#decisão"],
        "tipo": "direta",
    },
    {
        "pergunta": "quantas sementes cada configuração precisa?",
        "esperado": ["ferramenta-relatorios/docs/protocolo-experimento.md#repetições"],
        "tipo": "direta",
    },
    {
        "pergunta": "erro ColunaAusente semente na conversão",
        "esperado": [
            "ferramenta-relatorios/docs/uso.md#problemas-comuns",
            "notebook-analises/GUIA_DE_USO.md#exportar-resultados",
        ],
        "tipo": "multissalto",
    },
    {
        "pergunta": "como ativar o ambiente conda do notebook?",
        "esperado": ["notebook-analises/GUIA_DE_USO.md#preparar-o-ambiente"],
        "tipo": "direta",
    },
    {
        "pergunta": "que cuidado tomar com as cores dos gráficos impressos?",
        "esperado": ["notebook-analises/docs/figuras.md#"],
        "tipo": "paráfrase",
    },
    {
        "pergunta": "o que fazer antes de rodar um experimento novo com a ferramenta?",
        "esperado": ["ferramenta-relatorios/docs/protocolo-experimento.md#antes-de-rodar"],
        "tipo": "multissalto",
    },
    {
        "pergunta": "regras para agentes antes de propor um diff",
        "esperado": ["ferramenta-relatorios/AGENTS.md#"],
        "tipo": "direta",
    },
    # Sem resposta autorizada: a busca deve dizer que falta evidência.
    {"pergunta": "como configurar o kubernetes com helm?", "esperado": [], "tipo": "sem resposta"},
    {"pergunta": "qual a política de reembolso de viagens do grupo?", "esperado": [], "tipo": "sem resposta"},
    # Existe só no projeto INOVISÃO: do projeto pessoal, nada pode vazar.
    {"pergunta": "a que altura fica a câmera na coleta de imagens em campo?", "esperado": [], "tipo": "isolamento"},
]
