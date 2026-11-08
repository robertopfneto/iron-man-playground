from django.contrib import admin

from conhecimento.models import Documento, FonteGit, Relacao, Secao, Sincronizacao


@admin.register(FonteGit)
class FonteGitAdmin(admin.ModelAdmin):
    list_display = ("__str__", "repositorio", "situacao", "ultimo_sha", "sha_remoto", "sincronizada_em")
    list_filter = ("situacao", "ativa")
    readonly_fields = (
        "ultimo_sha",
        "sha_remoto",
        "situacao",
        "motivo_situacao",
        "sincronizando_desde",
        "sincronizada_em",
    )


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ("caminho", "fonte", "incluido", "motivo", "commit_sha")
    list_filter = ("incluido", "motivo", "fonte")
    search_fields = ("caminho",)


@admin.register(Secao)
class SecaoAdmin(admin.ModelAdmin):
    list_display = ("documento", "ancora", "linha_inicio", "linha_fim", "commit_sha")
    list_filter = ("documento__fonte",)


@admin.register(Relacao)
class RelacaoAdmin(admin.ModelAdmin):
    list_display = ("origem", "tipo", "destino_documento", "destino_secao")


@admin.register(Sincronizacao)
class SincronizacaoAdmin(admin.ModelAdmin):
    list_display = (
        "fonte",
        "iniciada_em",
        "situacao",
        "sha_anterior",
        "sha_novo",
        "adicionados",
        "alterados",
        "renomeados",
        "removidos",
    )
    list_filter = ("situacao", "fonte")
