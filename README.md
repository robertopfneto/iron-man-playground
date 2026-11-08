# Escritório 2D

Protótipo de escritório virtual 2D para conduzir sessões com Neto (coordenador), especialistas e registro de decisão. Entregas 1 a 4 do piloto estão implementadas: aplicação local reproduzível, catálogo de agentes/projetos, chat de delegação com Neto e a sala 2D (Phaser) ligada ao trabalho real.

## Fluxo completo (Entrega 4)

1. Suba a aplicação (seção abaixo).
2. Abra `http://127.0.0.1:8000`. No primeiro uso a tela pede para **criar a conta administradora**. Depois disso o cadastro fecha e a mesma tela vira o login. Escolha um projeto no topo.
3. A sala mostra os agentes autorizados nesse projeto, cada um no ponto que o mapa define. Clique em um avatar, ou no nome dele na lista da equipe, para abrir a ficha.
4. No chat com Neto, descreva um pedido. Pedidos simples encerram sem convocação; pedidos de mudança de código propõem uma convocação com agentes sugeridos (ex.: Hamilton + Kernighan).
5. Confirme a convocação com os agentes desejados. Os cartões de turno aparecem; cole o resultado de cada especialista para fechar o turno — o avatar correspondente muda de estado na sala em tempo real.
6. Quando todos os turnos de uma convocação são concluídos, uma decisão é consolidada como proposta. Aprove-a na lateral da tela.
7. Recarregue a página: o estado dos avatares, da convocação e da decisão aprovada persiste. Em uma nova conversa, pergunte sobre o mesmo assunto — Neto recupera a decisão aprovada diretamente, sem nova convocação.

### Sala e arte (Entregas 4A e 4B)

- **Mapa**: Tiled ortogonal com tiles 16×16 próprios (`web/public/jogo/mapas/recepcao_padrao/`), com as camadas `piso`, `obstaculos` e `objetos`. A camada de objetos traz as áreas nomeadas e os pontos `entrada`, `mesa_reuniao`, `assento_reuniao_N` e `trabalho_N`. O manifesto `web/public/jogo/mapas/manifesto.json` registra id, versão, mapa, tileset, prévia e licença. A cena Phaser carrega o template pelo `template_id`. Um id ausente ou desconhecido cai no padrão.
- **Posicionamento**: Neto fica na mesa de reunião. Agentes com turno convocado, em andamento ou aguardando revisão vão para os assentos da reunião. Os demais ficam nos postos de trabalho. Mudar os pontos no `mapa.json` muda o posicionamento sem mexer no código da cena.
- **Avatares**: pixel art com sprites 32×48 (apoio nos pés) e retratos 96×96. Neto e Pistori têm sprite frontal e retrato propostos, **aguardando revisão visual** (prancha em `docs/arte/revisao_neto_pistori.png`). Os outros 15 agentes usam placeholder com nome e símbolo individual. Créditos, condições de uso e referências estão em [`docs/arte/creditos.md`](docs/arte/creditos.md).
- Para regenerar a arte: `python3 web/tools/gerar_assets.py` (só biblioteca padrão). Depois, `docker compose up --build -d --wait`.

A loja de mapas e a criação de espaços (V1/V2) ficam para depois do piloto.

## Pré-requisitos

Git, Docker Engine e Docker Compose instalados no notebook. O primeiro build baixa as imagens e dependências (Python e Node são instalados durante o build, não no host).

## Como subir

```bash
git clone URL_DO_REPOSITORIO escritorio-2d
cd escritorio-2d
docker compose up --build -d --wait
curl -fsS http://127.0.0.1:8000/api/health
```

Abra `http://127.0.0.1:8000` no navegador e crie a conta administradora na tela de primeiro acesso. Não há usuário de demonstração com credencial fixa. Depois da primeira conta, o endpoint de cadastro fica fechado. Novas contas são criadas no Django Admin (`/admin/`) ou com `docker compose exec api python manage.py createsuperuser`.

Para parar a aplicação:

```bash
docker compose down
```

O volume de dados (`db_data`) é preservado entre reinicializações. Para apagar tudo, incluindo o banco: `docker compose down -v`.

## Dados de demonstração

Na primeira subida, a API carrega idempotentemente um agente (Neto) e um projeto pessoal demonstrativo, marcados com a flag `demo`. Para remover apenas esses dados, sem afetar projetos reais:

```bash
docker compose exec api python manage.py clear_demo
```

## Acesso remoto (opcional, ver Entrega 7)

Com SSH funcional no notebook, de outra máquina na mesma rede:

```bash
ssh -N -L 127.0.0.1:8000:127.0.0.1:8000 USUARIO@HOST_DO_NOTEBOOK
```

## Arquitetura desta entrega

- `api/`: Django 5.2 + Django Ninja. Serve a API em `/api/*` e o Django Admin em `/admin/*`. SQLite em volume persistente (`db_data`). Migrações e seed rodam automaticamente antes do healthcheck responder.
- `web/`: React + TypeScript + Vite, build estático servido por Caddy. Único serviço publicado em `127.0.0.1:8000`; encaminha `/api/*` e `/admin/*` para o serviço `api` internamente, e `/static/*` a partir de um volume compartilhado (`static_data`) com os arquivos do Django Admin.
- `compose.yaml`: só os serviços `web` e `api`. Nenhum mount de dataset, diretório pessoal ou socket Docker.

## Segurança

O **modo manual é o padrão deste protótipo**: não há execução automática de agentes de IA nem acesso a repositórios externos nesta entrega. Veja a política completa em [`docs/seguranca.md`](docs/seguranca.md).

A preparação do AI Jail (Entrega 6, ainda não habilitada) deve ser validada no notebook antes de qualquer execução automatizada:

```bash
command -v ai-jail
ai-jail --version
ai-jail --help
command -v bwrap
ai-jail --lockdown --no-network --no-agent-state --no-docker --dry-run claude
```

O `--dry-run` apenas inspeciona a configuração; não representa uma sessão funcional. Os testes de bloqueio com canários (seção 3 do plano original) devem passar antes de habilitar o executor da Entrega 6.

## Testes

```bash
docker compose exec api python manage.py test
```
