from typing import Optional

from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema
from ninja.security import django_auth

from core.models import AcessoAgente, Agente, ConfiguracaoModelo, Contexto, Projeto, Repositorio

api = NinjaAPI(csrf=True, title="Escritório 2D API")


def _negativa_generica(request, status=404):
    """Negativa genérica para identificadores fora do escopo (seção 3 do plano de segurança)."""
    return api.create_response(request, {"detail": "não encontrado"}, status=status)


@api.get("/health")
def health(request):
    """Endpoint usado pelo healthcheck do Compose. Não exige sessão."""
    return {"status": "ok"}


@api.get("/projetos", auth=django_auth)
def listar_projetos(request):
    """Lista mínima de projetos. Entrega 2 aplica o escopo de acesso completo."""
    return [{"id": p.id, "nome": p.nome, "cenario": p.cenario} for p in Projeto.objects.all()]


@api.get("/projetos/{projeto_id}/agentes", auth=django_auth)
def listar_agentes_do_projeto(request, projeto_id: int):
    """Agentes autorizados em um projeto, com a configuração de modelo de cada um."""
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    acessos = AcessoAgente.objects.filter(projeto=projeto, ativo=True).select_related(
        "agente", "agente__configuracao_modelo"
    )
    resultado = []
    for acesso in acessos:
        cfg = getattr(acesso.agente, "configuracao_modelo", None)
        resultado.append(
            {
                "agente_id": acesso.agente.id,
                "nome": acesso.agente.nome,
                "especialidade": acesso.agente.especialidade,
                "configuracao": None
                if cfg is None
                else {
                    "modo": cfg.modo,
                    "provedor": cfg.provedor,
                    "modelo": cfg.modelo,
                    "limite_entrada": cfg.limite_entrada,
                    "limite_saida": cfg.limite_saida,
                    "habilitado": cfg.habilitado,
                },
            }
        )
    return resultado


class ConfiguracaoModeloIn(Schema):
    modo: str = ConfiguracaoModelo.MODO_MANUAL
    provedor: str = ""
    modelo: str = ""
    limite_entrada: Optional[int] = None
    limite_saida: Optional[int] = None
    habilitado: bool = True


@api.patch("/agentes/{agente_id}/configuracao", auth=django_auth)
def atualizar_configuracao_modelo(request, agente_id: int, payload: ConfiguracaoModeloIn):
    """Atualiza a configuração de modelo de um agente, sem afetar as demais."""
    agente = get_object_or_404(Agente, pk=agente_id)
    cfg, _ = ConfiguracaoModelo.objects.get_or_create(agente=agente)
    for campo, valor in payload.dict().items():
        setattr(cfg, campo, valor)
    cfg.save()
    return {"ok": True}


class ContextoIn(Schema):
    projeto_id: int
    agente_id: int
    pedido: str
    objetivo_projeto: str = ""
    decisoes_relevantes: str = ""
    formato_entrega: str = ""
    referencias_ids: list[int] = []


@api.post("/contextos", auth=django_auth)
def criar_contexto(request, payload: ContextoIn):
    """Cria um contexto de tarefa. O escopo de projeto e repositório é aplicado aqui,
    antes de qualquer recuperação de contexto por um agente."""
    projeto = get_object_or_404(Projeto, pk=payload.projeto_id)

    acesso = AcessoAgente.objects.filter(
        projeto=projeto, agente_id=payload.agente_id, ativo=True
    ).first()
    if acesso is None:
        return _negativa_generica(request)

    ids_unicos = set(payload.referencias_ids)
    repositorios = Repositorio.objects.filter(id__in=ids_unicos, projeto=projeto)
    if repositorios.count() != len(ids_unicos):
        # Referência a repositório inexistente ou de outro projeto: negativa genérica.
        return _negativa_generica(request)

    contexto = Contexto.objects.create(
        projeto=projeto,
        agente_id=payload.agente_id,
        pedido=payload.pedido,
        objetivo_projeto=payload.objetivo_projeto,
        decisoes_relevantes=payload.decisoes_relevantes,
        formato_entrega=payload.formato_entrega,
    )
    contexto.referencias.set(repositorios)
    return {"id": contexto.id}


@api.get("/contextos/{contexto_id}", auth=django_auth)
def obter_contexto(request, contexto_id: int):
    contexto = get_object_or_404(Contexto, pk=contexto_id)
    return {
        "id": contexto.id,
        "projeto_id": contexto.projeto_id,
        "agente_id": contexto.agente_id,
        "pedido": contexto.pedido,
        "objetivo_projeto": contexto.objetivo_projeto,
        "decisoes_relevantes": contexto.decisoes_relevantes,
        "formato_entrega": contexto.formato_entrega,
        "referencias": list(contexto.referencias.values_list("id", flat=True)),
    }
