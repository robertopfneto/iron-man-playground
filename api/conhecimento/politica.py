"""Política de acesso da base de conhecimento, aplicada pelo backend.

O escopo vem da sessão e do vínculo do agente com o projeto. O texto da pergunta
nunca amplia o escopo. Projetos restritos (Before) ficam fora da ingestão e da
busca até autorização explícita na fonte.
"""

from core.models import AcessoAgente

from conhecimento.models import FonteGit

CENARIOS_RESTRITOS = {"before"}


def fonte_restrita(fonte: FonteGit) -> bool:
    projeto = fonte.repositorio.projeto
    restrito = projeto.cenario.strip().lower() in CENARIOS_RESTRITOS or projeto.nome.strip().lower() in CENARIOS_RESTRITOS
    return restrito and not fonte.autorizacao_explicita


def fontes_autorizadas(projeto_id: int, agente_id: int):
    """Fontes que o agente pode consultar no projeto. Vazio se o agente não tem acesso."""
    if not AcessoAgente.objects.filter(projeto_id=projeto_id, agente_id=agente_id, ativo=True).exists():
        return FonteGit.objects.none()
    fontes = FonteGit.objects.filter(repositorio__projeto_id=projeto_id, ativa=True).select_related(
        "repositorio__projeto"
    )
    return fontes.exclude(pk__in=[f.pk for f in fontes if fonte_restrita(f)])
