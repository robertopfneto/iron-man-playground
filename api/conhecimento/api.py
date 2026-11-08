"""Endpoints da base de conhecimento. Exigem sessão; escopo vem do vínculo do agente com o projeto."""

from django.http import JsonResponse
from ninja import Router, Schema
from ninja.security import django_auth

from conhecimento.busca import MODOS, buscar, guias_afetados
from conhecimento.politica import fontes_autorizadas
from core.models import AcessoAgente, Agente

router = Router(auth=django_auth, tags=["conhecimento"])


def _negativa_generica():
    # Mesma resposta para projeto inexistente, agente sem acesso ou fonte fora do escopo.
    return JsonResponse({"detail": "não encontrado"}, status=404)


def _tem_acesso(projeto_id: int, agente_id: int) -> bool:
    return AcessoAgente.objects.filter(projeto_id=projeto_id, agente_id=agente_id, ativo=True).exists()


@router.get("/busca")
def busca(request, projeto_id: int, agente_id: int, pergunta: str, modo: str = "hibrida_grafo"):
    if modo not in MODOS or not pergunta.strip():
        return JsonResponse({"detail": "parâmetros inválidos"}, status=400)
    if not _tem_acesso(projeto_id, agente_id):
        return _negativa_generica()
    return buscar(projeto_id, agente_id, pergunta, modo=modo).como_dict()


class DiffIn(Schema):
    projeto_id: int
    diff: str


@router.post("/guias-afetados")
def guias(request, payload: DiffIn):
    kernighan = Agente.objects.filter(nome="Kernighan").first()
    if kernighan is None or not _tem_acesso(payload.projeto_id, kernighan.pk):
        return _negativa_generica()
    return guias_afetados(payload.projeto_id, kernighan.pk, payload.diff).como_dict()


@router.get("/projetos/{projeto_id}/fontes")
def fontes(request, projeto_id: int, agente_id: int):
    if not _tem_acesso(projeto_id, agente_id):
        return _negativa_generica()
    return [
        {
            "repositorio": f"{f.conta}/{f.nome_repositorio}",
            "branch": f.branch,
            "situacao": f.situacao,
            "motivo": f.motivo_situacao,
            "sha_indexado": f.ultimo_sha,
            "sha_remoto": f.sha_remoto,
            "sincronizada_em": f.sincronizada_em.isoformat() if f.sincronizada_em else None,
        }
        for f in fontes_autorizadas(projeto_id, agente_id)
    ]
