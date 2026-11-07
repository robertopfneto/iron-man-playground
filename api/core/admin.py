from django.contrib import admin

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


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cenario", "situacao", "demo", "criado_em")


@admin.register(Repositorio)
class RepositorioAdmin(admin.ModelAdmin):
    list_display = ("projeto", "nome", "demo")


@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ("nome", "especialidade", "demo")


@admin.register(AcessoAgente)
class AcessoAgenteAdmin(admin.ModelAdmin):
    list_display = ("projeto", "agente", "ativo")
    list_filter = ("projeto", "ativo")


@admin.register(ConfiguracaoModelo)
class ConfiguracaoModeloAdmin(admin.ModelAdmin):
    list_display = ("agente", "modo", "provedor", "modelo", "habilitado")


@admin.register(Contexto)
class ContextoAdmin(admin.ModelAdmin):
    list_display = ("projeto", "agente", "formato_entrega", "criado_em")
    list_filter = ("projeto", "agente")


@admin.register(Conversa)
class ConversaAdmin(admin.ModelAdmin):
    list_display = ("id", "projeto", "criado_em")


@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ("conversa", "autor", "ordem", "criado_em")
    list_filter = ("autor",)


@admin.register(Convocacao)
class ConvocacaoAdmin(admin.ModelAdmin):
    list_display = ("id", "projeto", "situacao", "criado_em")
    list_filter = ("projeto", "situacao")


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ("convocacao", "agente", "situacao", "criado_em")
    list_filter = ("agente", "situacao")


@admin.register(Decisao)
class DecisaoAdmin(admin.ModelAdmin):
    list_display = ("projeto", "situacao", "criado_em", "aprovada_em")
    list_filter = ("projeto", "situacao")
