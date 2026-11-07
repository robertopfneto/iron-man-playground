# Segurança do Escritório 2D

Política e matriz de acesso aprovadas para o piloto. Não inventariar caminhos sensíveis nem credenciais aqui.

## Regra de arquitetura

O agente recebe somente a tarefa, os trechos selecionados e uma área de trabalho preparada para aquela execução. Um item fora do escopo deve estar ausente do prompt, da busca, do catálogo visível ao agente e do sistema de arquivos da execução. A API retorna negativa genérica para identificadores fora do escopo, sem revelar se o recurso existe.

As regras são aplicadas pelo backend e pelo isolamento do sistema operacional. Prompts, arquivos de instrução, hooks e filtros de texto podem ajudar no fluxo, mas não concedem acesso e não são barreiras de segurança.

## Fronteiras de execução (Entrega 1)

| Componente | Estado nesta entrega |
|---|---|
| Django e banco | Serviço `api` sem mounts de dataset, diretório pessoal ou socket Docker (ver `compose.yaml`). |
| Modo manual | Único modo disponível. Nenhuma chamada a modelo ou provedor externo nesta entrega. |
| Before | Não modelada ainda. Quando entrar, fica como catálogo sem acesso operacional. |
| Sandbox por tarefa / AI Jail | Não habilitado. Ver seção 3 do plano original e a Entrega 6. |

## Política de negação por padrão

Negação por padrão por projeto, tipo de dado, agente, operação e destino. Separar leitura, edição, execução e envio para um provedor. A Before é catálogo sem acesso operacional. Dados sigilosos, biometria, credenciais e dados pessoais são classificados como restritos e ficam fora do notebook pessoal quando a política do projeto não autorizar a hospedagem.

## Critérios de aceite de segurança (a validar a partir da Entrega 6)

- Arquivos fora do escopo não aparecem na listagem nem são acessíveis, mesmo quando o teste conhece o caminho.
- Sem saída de rede da sandbox. Sockets de Docker/SSH e variáveis de credencial ausentes.
- Requisição de outro projeto ou configuração de provedor incompatível falha antes da leitura ou do envio, sem confirmar existência do item.
- Supervisor rejeita symlinks, hard links, arquivos especiais e paths fora do escopo. Log sem segredos ou conteúdo sensível.
- Falha de perfil/sandbox bloqueia o trabalho; não há retentativa fora da sandbox.

Ver o documento original (`plano_implementacao_escritorio_2d.md`, seção 3) para o detalhamento completo da preparação do AI Jail e dos frameworks de execução candidatos.
