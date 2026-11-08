"""Triagem de mensagens de Neto (Entrega 3). Modo manual: sem chamada de modelo.

Regras:
- Consulta explícita a uma decisão aprovada é resolvida diretamente pelo backend.
- Pedido curto sem palavras de mudança de código/repositório encerra sem convocação.
- Demais pedidos geram uma proposta de convocação com agentes sugeridos, restrita
  aos agentes autorizados no projeto (AcessoAgente ativo).
"""

from core.models import AcessoAgente, Agente, Decisao

INTERROGATIVOS = ("como", "onde", "qual", "quais", "quando", "quem", "por", "porque", "existe", "há", "posso")
MAX_EVIDENCIAS_NA_RESPOSTA = 3

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
COORDENADOR = "Neto"


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


def _e_pergunta(texto: str) -> bool:
    t = texto.strip().lower()
    return t.endswith("?") or t.startswith("o que") or t.split(" ", 1)[0] in INTERROGATIVOS


def _responder_com_documentacao(projeto, texto: str) -> dict | None:
    """Responde com evidência da base de conhecimento, no escopo de Neto neste projeto."""
    from conhecimento.busca import buscar
    from conhecimento.models import FonteGit

    neto = Agente.objects.filter(nome=COORDENADOR).first()
    indexadas = FonteGit.objects.filter(repositorio__projeto=projeto, ativa=True).exclude(ultimo_sha="")
    if neto is None or not indexadas.exists():
        return None

    resultado = buscar(projeto.id, neto.id, texto)
    if resultado.sem_evidencia:
        return {
            "tipo": "sem_evidencia",
            "resposta": "Não encontrei evidência autorizada na documentação deste projeto para responder isso. "
            "Se quiser, reformule ou peça uma convocação.",
            "avisos": resultado.avisos,
            "evidencias": [],
        }

    principal = resultado.trechos[0]
    linhas = [f"Pela documentação de {principal.repositorio} (commit {principal.commit[:12]}):", ""]
    linhas.append(principal.texto[:500])
    linhas.append("")
    linhas.append("Fontes:")
    for t in resultado.trechos[:MAX_EVIDENCIAS_NA_RESPOSTA]:
        relacionado = " (relacionado por link)" if t.origem == "relacao" else ""
        linhas.append(f"- {t.secao} | {t.repositorio}/{t.caminho} {t.linhas} @ {t.commit[:12]}{relacionado}")
    linhas.extend(resultado.avisos)

    prompt = "\n\n".join(
        [f"Pergunta: {texto}", "Responda só com base nos trechos abaixo e cite a fonte de cada afirmação."]
        + [f"[{i}] {t.repositorio}/{t.caminho} {t.linhas} @ {t.commit[:12]}\n{t.texto}" for i, t in enumerate(resultado.trechos, 1)]
    )
    return {
        "tipo": "resposta_documentada",
        "resposta": "\n".join(linhas),
        "evidencias": [t.__dict__ for t in resultado.trechos],
        "avisos": resultado.avisos,
        "prompt_copiavel": prompt,
    }


def triar_mensagem(projeto, texto: str) -> dict:
    decisao = _busca_decisao_aprovada(projeto, texto)
    if decisao is not None:
        return {
            "tipo": "resposta_direta",
            "resposta": f"Já decidimos isso: {decisao.texto}",
            "decisao_id": decisao.id,
        }

    if _e_pergunta(texto):
        documentada = _responder_com_documentacao(projeto, texto)
        if documentada is not None:
            return documentada

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

    # Neto coordena a convocação; ele não é convocado como especialista.
    agentes_sugeridos = list(
        AcessoAgente.objects.filter(projeto=projeto, ativo=True)
        .exclude(agente__nome=COORDENADOR)
        .values_list("agente_id", flat=True)
    )
    return {
        "tipo": "proposta_convocacao",
        "prompt_copiavel": f"Tarefa para triagem manual de Neto:\nPedido: {texto}",
        "agentes_sugeridos": agentes_sugeridos,
    }
