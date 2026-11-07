from django.contrib import admin

from core.models import (
    AcessoAgente,
    Agente,
    ConfiguracaoModelo,
    Contexto,
    Projeto,
    Repositorio,
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
