from django.contrib import admin

from core.models import Agente, Projeto, Repositorio


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cenario", "situacao", "demo", "criado_em")


@admin.register(Repositorio)
class RepositorioAdmin(admin.ModelAdmin):
    list_display = ("projeto", "nome", "demo")


@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ("nome", "especialidade", "demo")
