from ninja import NinjaAPI
from ninja.security import django_auth

from core.models import Projeto

api = NinjaAPI(csrf=True, title="Escritório 2D API")


@api.get("/health")
def health(request):
    """Endpoint usado pelo healthcheck do Compose. Não exige sessão."""
    return {"status": "ok"}


@api.get("/projetos", auth=django_auth)
def listar_projetos(request):
    """Lista mínima de projetos. Entrega 2 aplica o escopo de acesso completo."""
    return [{"id": p.id, "nome": p.nome, "cenario": p.cenario} for p in Projeto.objects.all()]
