"""Triagem de mensagens de Neto (Entrega 3). Modo manual: sem chamada de modelo.

Regras:
- Consulta explícita a uma decisão aprovada é resolvida diretamente pelo backend.
- Pedido curto sem palavras de mudança de código/repositório encerra sem convocação.
- Demais pedidos geram uma proposta de convocação com agentes sugeridos, restrita
  aos agentes autorizados no projeto (AcessoAgente ativo).
"""

from core.models import AcessoAgente, Decisao

PALAVRAS_MUDANCA_CODIGO = (
    "código",
    "codigo",
    "repositório",
    "repositorio",
    "comando de instalação",
    "comando de instalacao",
    "implementar",
    "alterar",
    "mudar",
    "readme",
)

LIMITE_TAMANHO_DUVIDA_SIMPLES = 80


def _busca_decisao_aprovada(projeto, texto: str):
    palavras = [p for p in texto.lower().split() if len(p) > 3]
    if not palavras:
        return None
    qs = Decisao.objects.filter(projeto=projeto, situacao=Decisao.SITUACAO_APROVADA)
    for decisao in qs:
        if any(p in decisao.texto.lower() for p in palavras):
            return decisao
    return None


def _menciona_mudanca_de_codigo(texto: str) -> bool:
    texto_lower = texto.lower()
    return any(p in texto_lower for p in PALAVRAS_MUDANCA_CODIGO)


def triar_mensagem(projeto, texto: str) -> dict:
    decisao = _busca_decisao_aprovada(projeto, texto)
    if decisao is not None:
        return {
            "tipo": "resposta_direta",
            "resposta": f"Já decidimos isso: {decisao.texto}",
            "decisao_id": decisao.id,
        }

    if _menciona_mudanca_de_codigo(texto):
        nomes_sugeridos = ["Hamilton", "Kernighan"]
        agentes_sugeridos = list(
            AcessoAgente.objects.filter(
                projeto=projeto, ativo=True, agente__nome__in=nomes_sugeridos
            ).values_list("agente_id", flat=True)
        )
        return {
            "tipo": "proposta_convocacao",
            "prompt_copiavel": (
                "Tarefa para triagem manual de Neto:\n"
                f"Pedido: {texto}\n"
                "Avalie se cabe uma convocação de Hamilton (implementação) e "
                "Kernighan (revisão de documentação) para este projeto."
            ),
            "agentes_sugeridos": agentes_sugeridos,
        }

    if len(texto) <= LIMITE_TAMANHO_DUVIDA_SIMPLES:
        return {
            "tipo": "duvida_simples",
            "resposta": "Anotado. Não é necessário convocar ninguém para isso.",
        }

    agentes_sugeridos = list(
        AcessoAgente.objects.filter(projeto=projeto, ativo=True).values_list("agente_id", flat=True)
    )
    return {
        "tipo": "proposta_convocacao",
        "prompt_copiavel": f"Tarefa para triagem manual de Neto:\nPedido: {texto}",
        "agentes_sugeridos": agentes_sugeridos,
    }
