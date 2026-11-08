from typing import Optional

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.middleware.csrf import get_token
from ninja import NinjaAPI, Schema
from ninja.security import django_auth

from core.logic import triar_mensagem
from core.models import (
    AcessoAgente,
    Agente,
    ConfiguracaoModelo,
    Contexto,
    Convocacao,
    Conversa,
    Decisao,
    Mensagem,
    Projeto,
    Repositorio,
    Turno,
)

LIMITE_CONVOCACOES_ABERTAS_POR_PROJETO = 3
LIMITE_TAMANHO_TAREFA = 4000

api = NinjaAPI(csrf=True, title="Escritório 2D API")
api.add_router("/conhecimento", "conhecimento.api.router")


def _negativa_generica(request, status=404):
    """Negativa genérica para identificadores fora do escopo (seção 3 do plano de segurança)."""
    return api.create_response(request, {"detail": "não encontrado"}, status=status)


@api.get("/health")
def health(request):
    """Endpoint usado pelo healthcheck do Compose. Não exige sessão."""
    return {"status": "ok"}


@api.get("/auth/sessao")
def sessao(request):
    """Estado da sessão. Também garante o cookie CSRF para o login da SPA."""
    get_token(request)
    if request.user.is_authenticated:
        return {"autenticado": True, "usuario": request.user.get_username(), "precisa_cadastro": False}
    return {
        "autenticado": False,
        "usuario": None,
        "precisa_cadastro": not get_user_model().objects.exists(),
    }


class PrimeiroAcessoIn(Schema):
    usuario: str
    senha: str


@api.post("/auth/primeiro-acesso")
def primeiro_acesso(request, payload: PrimeiroAcessoIn):
    """Cria a primeira conta (administradora) enquanto não existir nenhum usuário.
    Depois disso o endpoint fica fechado; novas contas só pelo Django Admin."""
    User = get_user_model()
    with transaction.atomic():
        if User.objects.select_for_update().exists():
            return api.create_response(request, {"detail": "Cadastro inicial já realizado."}, status=403)
        try:
            validate_password(payload.senha)
        except ValidationError as exc:
            return api.create_response(request, {"detail": " ".join(exc.messages)}, status=400)
        if not payload.usuario.strip():
            return api.create_response(request, {"detail": "Informe um nome de usuário."}, status=400)
        user = User.objects.create_superuser(username=payload.usuario.strip(), password=payload.senha)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return {"autenticado": True, "usuario": user.get_username()}


class LoginIn(Schema):
    usuario: str
    senha: str


@api.post("/auth/login")
def entrar(request, payload: LoginIn):
    user = authenticate(request, username=payload.usuario, password=payload.senha)
    if user is None:
        return api.create_response(request, {"detail": "Usuário ou senha inválidos."}, status=401)
    login(request, user)
    return {"autenticado": True, "usuario": user.get_username()}


@api.post("/auth/logout", auth=django_auth)
def sair(request):
    logout(request)
    return {"autenticado": False}


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


# --- Entrega 3: chat do Neto, delegação e documentação --------------------


class ConversaIn(Schema):
    projeto_id: int


@api.post("/conversas", auth=django_auth)
def criar_conversa(request, payload: ConversaIn):
    projeto = get_object_or_404(Projeto, pk=payload.projeto_id)
    conversa = Conversa.objects.create(projeto=projeto)
    return {"id": conversa.id, "projeto_id": projeto.id}


def _proxima_ordem(conversa: Conversa) -> int:
    ultima = conversa.mensagens.order_by("-ordem").first()
    return (ultima.ordem + 1) if ultima else 1


class MensagemIn(Schema):
    conteudo: str


@api.post("/conversas/{conversa_id}/mensagens", auth=django_auth)
def enviar_mensagem(request, conversa_id: int, payload: MensagemIn):
    """Triagem da mensagem do usuário por Neto. Modo manual: sem chamada de modelo."""
    conversa = get_object_or_404(Conversa, pk=conversa_id)

    with transaction.atomic():
        mensagem_usuario = Mensagem.objects.create(
            conversa=conversa,
            autor=Mensagem.AUTOR_USUARIO,
            conteudo=payload.conteudo,
            ordem=_proxima_ordem(conversa),
        )

        resultado = triar_mensagem(conversa.projeto, payload.conteudo)

        if resultado["tipo"] in ("resposta_direta", "duvida_simples", "resposta_documentada", "sem_evidencia"):
            Mensagem.objects.create(
                conversa=conversa,
                autor=Mensagem.AUTOR_NETO,
                conteudo=resultado["resposta"],
                ordem=_proxima_ordem(conversa),
            )
            return {"mensagem_id": mensagem_usuario.id, **resultado}

        convocacoes_abertas = Convocacao.objects.filter(
            projeto=conversa.projeto, situacao=Convocacao.SITUACAO_PROPOSTA
        ).count()
        if convocacoes_abertas >= LIMITE_CONVOCACOES_ABERTAS_POR_PROJETO:
            Mensagem.objects.create(
                conversa=conversa,
                autor=Mensagem.AUTOR_NETO,
                conteudo="Limite de convocações abertas atingido neste projeto. Conclua ou cancele alguma antes de propor outra.",
                ordem=_proxima_ordem(conversa),
            )
            return {"mensagem_id": mensagem_usuario.id, "tipo": "limite_atingido"}

        if len(payload.conteudo) > LIMITE_TAMANHO_TAREFA:
            return _negativa_generica(request, status=400)

        convocacao = Convocacao.objects.create(
            projeto=conversa.projeto,
            conversa=conversa,
            mensagem_origem=mensagem_usuario,
            tarefa=payload.conteudo,
        )
        Mensagem.objects.create(
            conversa=conversa,
            autor=Mensagem.AUTOR_NETO,
            conteudo=resultado["prompt_copiavel"],
            ordem=_proxima_ordem(conversa),
        )
        return {
            "mensagem_id": mensagem_usuario.id,
            "tipo": "proposta_convocacao",
            "convocacao_id": convocacao.id,
            "prompt_copiavel": resultado["prompt_copiavel"],
            "agentes_sugeridos": resultado["agentes_sugeridos"],
        }


class ConfirmarConvocacaoIn(Schema):
    agentes_ids: list[int]


@api.post("/convocacoes/{convocacao_id}/confirmar", auth=django_auth)
def confirmar_convocacao(request, convocacao_id: int, payload: ConfirmarConvocacaoIn):
    convocacao = get_object_or_404(Convocacao, pk=convocacao_id)

    if convocacao.situacao != Convocacao.SITUACAO_PROPOSTA:
        # Confirmação repetida: não duplica turnos, apenas devolve o estado atual.
        return {
            "id": convocacao.id,
            "situacao": convocacao.situacao,
            "turnos": list(convocacao.turnos.values_list("id", flat=True)),
        }

    ids_unicos = set(payload.agentes_ids)
    autorizados = set(
        AcessoAgente.objects.filter(
            projeto=convocacao.projeto, agente_id__in=ids_unicos, ativo=True
        ).values_list("agente_id", flat=True)
    )
    if autorizados != ids_unicos:
        return _negativa_generica(request)

    with transaction.atomic():
        turnos = [
            Turno.objects.create(convocacao=convocacao, agente_id=agente_id, tarefa=convocacao.tarefa)
            for agente_id in ids_unicos
        ]
        convocacao.situacao = Convocacao.SITUACAO_CONFIRMADA
        convocacao.save(update_fields=["situacao"])

    return {"id": convocacao.id, "situacao": convocacao.situacao, "turnos": [t.id for t in turnos]}


class TurnoResultadoIn(Schema):
    resultado: str
    autoria: str = ""


@api.post("/turnos/{turno_id}/resultado", auth=django_auth)
def registrar_resultado_turno(request, turno_id: int, payload: TurnoResultadoIn):
    turno = get_object_or_404(Turno, pk=turno_id)

    if turno.situacao == Turno.SITUACAO_CONCLUIDO:
        # Idempotente: não sobrescreve um turno já concluído.
        return {"id": turno.id, "situacao": turno.situacao}

    turno.resultado = payload.resultado
    turno.autoria = payload.autoria
    turno.situacao = Turno.SITUACAO_CONCLUIDO
    turno.concluido_em = timezone.now()
    turno.save(update_fields=["resultado", "autoria", "situacao", "concluido_em"])

    convocacao = turno.convocacao
    if not convocacao.turnos.exclude(situacao=Turno.SITUACAO_CONCLUIDO).exists():
        convocacao.situacao = Convocacao.SITUACAO_CONCLUIDA
        convocacao.save(update_fields=["situacao"])
        Decisao.objects.get_or_create(
            convocacao=convocacao,
            defaults={
                "projeto": convocacao.projeto,
                "texto": "\n\n".join(
                    f"{t.agente.nome}: {t.resultado}" for t in convocacao.turnos.all()
                ),
            },
        )

    return {"id": turno.id, "situacao": turno.situacao}


@api.get("/convocacoes/{convocacao_id}", auth=django_auth)
def obter_convocacao(request, convocacao_id: int):
    convocacao = get_object_or_404(Convocacao, pk=convocacao_id)
    return {
        "id": convocacao.id,
        "situacao": convocacao.situacao,
        "tarefa": convocacao.tarefa,
        "turnos": [
            {
                "id": t.id,
                "agente_id": t.agente_id,
                "agente": t.agente.nome,
                "situacao": t.situacao,
                "resultado": t.resultado,
                "autoria": t.autoria,
            }
            for t in convocacao.turnos.all()
        ],
    }


@api.post("/decisoes/{decisao_id}/aprovar", auth=django_auth)
def aprovar_decisao(request, decisao_id: int):
    decisao = get_object_or_404(Decisao, pk=decisao_id)
    if decisao.situacao != Decisao.SITUACAO_APROVADA:
        decisao.situacao = Decisao.SITUACAO_APROVADA
        decisao.aprovada_em = timezone.now()
        decisao.save(update_fields=["situacao", "aprovada_em"])
    return {"id": decisao.id, "situacao": decisao.situacao}


@api.get("/projetos/{projeto_id}/decisoes", auth=django_auth)
def listar_decisoes(request, projeto_id: int):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    return [
        {"id": d.id, "texto": d.texto, "situacao": d.situacao}
        for d in projeto.decisoes.all()
    ]


@api.get("/projetos/{projeto_id}/convocacoes-abertas", auth=django_auth)
def listar_convocacoes_abertas(request, projeto_id: int):
    """Convocações confirmadas com turnos ainda não concluídos: o trabalho pendente do projeto,
    persistido entre recargas e independente da conversa em que nasceu."""
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    abertas = (
        Convocacao.objects.filter(projeto=projeto, situacao=Convocacao.SITUACAO_CONFIRMADA)
        .prefetch_related("turnos__agente")
        .order_by("criado_em")
    )
    return [
        {
            "id": c.id,
            "tarefa": c.tarefa,
            "turnos": [
                {
                    "id": t.id,
                    "agente_id": t.agente_id,
                    "agente": t.agente.nome,
                    "situacao": t.situacao,
                    "resultado": t.resultado,
                }
                for t in c.turnos.all()
            ],
        }
        for c in abertas
    ]


# --- Entrega 4: sala 2D ligada ao trabalho real ----------------------------

ESTADO_DISPONIVEL = "disponivel"

_SITUACAO_TURNO_PARA_ESTADO = {
    Turno.SITUACAO_CONVOCADO: "convocado",
    Turno.SITUACAO_EM_ANDAMENTO: "em_andamento",
    Turno.SITUACAO_AGUARDANDO_REVISAO: "aguardando_revisao",
    Turno.SITUACAO_CONCLUIDO: "concluido",
}

TEMPLATE_PADRAO_ID = "recepcao_padrao"


@api.get("/projetos/{projeto_id}/sala", auth=django_auth)
def obter_sala(request, projeto_id: int, template_id: Optional[str] = None):
    """Estado visual da sala (Entrega 4). O mapa é só uma escolha visual no frontend;
    aqui só resolvemos o template_id (com fallback) e o estado de cada avatar."""
    projeto = get_object_or_404(Projeto, pk=projeto_id)

    acessos = AcessoAgente.objects.filter(projeto=projeto, ativo=True).select_related("agente")
    avatares = []
    for acesso in acessos:
        ultimo_turno = (
            Turno.objects.filter(agente=acesso.agente, convocacao__projeto=projeto)
            .order_by("-criado_em")
            .first()
        )
        estado = ESTADO_DISPONIVEL
        if ultimo_turno is not None and ultimo_turno.situacao in _SITUACAO_TURNO_PARA_ESTADO:
            # "concluído" só reflete um turno concluído sem convocação nova aberta depois.
            estado = _SITUACAO_TURNO_PARA_ESTADO[ultimo_turno.situacao]

        avatares.append(
            {
                "agente_id": acesso.agente.id,
                "avatar_id": acesso.agente.nome.lower(),
                "nome": acesso.agente.nome,
                "homenagem": acesso.agente.homenagem,
                "especialidade": acesso.agente.especialidade,
                "direcao_arte": acesso.agente.direcao_arte,
                "referencia_visual": acesso.agente.referencia_visual,
                "estado": estado,
            }
        )

    template_resolvido = template_id or TEMPLATE_PADRAO_ID
    return {
        "projeto_id": projeto.id,
        "template_id": template_resolvido,
        "avatares": avatares,
    }
