# Escritório 2D

Protótipo de escritório virtual 2D para conduzir sessões com Neto (coordenador), especialistas e registro de decisão. Esta é a **Entrega 1** do piloto: aplicação local reproduzível com Docker Compose. Entregas 2 a 4 (catálogo, chat/delegação e sala 2D) ainda não estão implementadas.

## Pré-requisitos

Git, Docker Engine e Docker Compose instalados no notebook. O primeiro build baixa as imagens e dependências (Python e Node são instalados durante o build, não no host).

## Como subir

```bash
git clone URL_DO_REPOSITORIO escritorio-2d
cd escritorio-2d
docker compose up --build -d --wait
docker compose exec api python manage.py createsuperuser
curl -fsS http://127.0.0.1:8000/api/health
```

Abra `http://127.0.0.1:8000` no navegador. Não há usuário de demonstração com credenciais fixas — crie o primeiro usuário com `createsuperuser` no primeiro uso.

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
