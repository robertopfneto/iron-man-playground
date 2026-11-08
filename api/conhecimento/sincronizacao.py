"""Sincronização incremental do índice com a branch monitorada.

Fluxo: trava a fonte -> fetch -> calcula o plano completo (leitura, seleção,
seções, embeddings faltantes) -> publica tudo numa transação -> avança o SHA.
Falha em qualquer etapa mantém a versão anterior consultável e é registrada.
"""

import posixpath
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from conhecimento import git_leitura, indice
from conhecimento.embeddings import EmbeddingsIndisponiveis, empacotar, obter_embedder
from conhecimento.markdown import (
    SecaoParse,
    avaliar_caminho,
    avaliar_conteudo,
    dividir_em_secoes,
    e_markdown,
    extrair_links,
    resolver_alvo,
    texto_para_embedding,
    titulo_do_documento,
)
from conhecimento.models import Documento, Embedding, FonteGit, Relacao, Secao, Sincronizacao
from conhecimento.politica import fonte_restrita

TRAVA_EXPIRA = timedelta(minutes=30)


@dataclass
class DocPlanejado:
    caminho: str
    blob_sha: str
    incluido: bool
    motivo: str
    titulo: str = ""
    secoes: list[SecaoParse] = field(default_factory=list)
    existente_id: int | None = None
    conteudo_alterado: bool = True


@dataclass
class Plano:
    sha: str
    docs: list[DocPlanejado] = field(default_factory=list)
    removidos: list[int] = field(default_factory=list)
    adicionados: int = 0
    alterados: int = 0
    renomeados: int = 0
    vetorizadas: int = 0
    reaproveitadas: int = 0


# ------------------------------------------------------------------ plano


def calcular_plano(fonte: FonteGit, espelho, sha: str, embedder, sem_embeddings: bool) -> Plano:
    entradas = [e for e in git_leitura.listar_arvore(espelho, sha) if e_markdown(e.caminho)]
    existentes = {d.caminho: d for d in fonte.documentos.all()}
    renomes = {}
    if fonte.ultimo_sha and fonte.ultimo_sha != sha:
        renomes = git_leitura.renomeacoes(espelho, fonte.ultimo_sha, sha)
    caminhos_novos = {e.caminho for e in entradas}
    novo_para_antigo = {
        novo: antigo for antigo, novo in renomes.items() if antigo in existentes and antigo not in caminhos_novos
    }

    plano, usados = Plano(sha=sha), set()
    for e in entradas:
        anterior, renomeado = existentes.get(e.caminho), False
        if anterior is None and e.caminho in novo_para_antigo:
            anterior, renomeado = existentes[novo_para_antigo[e.caminho]], True
        if anterior is not None:
            usados.add(anterior.pk)

        if anterior is not None and anterior.blob_sha == e.blob_sha:
            plano.docs.append(
                DocPlanejado(
                    e.caminho,
                    e.blob_sha,
                    anterior.incluido,
                    anterior.motivo,
                    anterior.titulo,
                    existente_id=anterior.pk,
                    conteudo_alterado=False,
                )
            )
            plano.renomeados += int(renomeado)
            continue

        motivo = avaliar_caminho(e.caminho, e.modo, e.tamanho, fonte.incluir, fonte.excluir)
        secoes, titulo = [], ""
        if motivo is None:
            texto = git_leitura.ler_blob(espelho, e.blob_sha)
            motivo = avaliar_conteudo(texto)
            if motivo == "incluido":
                secoes = dividir_em_secoes(texto, e.caminho)
                motivo = "incluido" if secoes else "vazio"
                titulo = titulo_do_documento(secoes, e.caminho)
        plano.docs.append(
            DocPlanejado(
                e.caminho,
                e.blob_sha,
                motivo == "incluido",
                motivo,
                titulo,
                secoes if motivo == "incluido" else [],
                anterior.pk if anterior else None,
            )
        )
        if renomeado:
            plano.renomeados += 1
        elif anterior is None:
            plano.adicionados += 1
        else:
            plano.alterados += 1

    plano.removidos = [d.pk for d in existentes.values() if d.pk not in usados]
    if not sem_embeddings:
        _preparar_embeddings(plano, embedder)
    return plano


def _preparar_embeddings(plano: Plano, embedder) -> None:
    """Vetoriza só o conteúdo que ainda não tem vetor para o modelo atual."""
    modelo = settings.EMBEDDINGS_MODELO
    textos: dict[str, str] = {}
    for d in plano.docs:
        if not d.incluido:
            continue
        if d.conteudo_alterado:
            for s in d.secoes:
                textos[s.hash_conteudo] = texto_para_embedding(s.titulos, s.texto)
        elif d.existente_id:
            for s in Secao.objects.filter(documento_id=d.existente_id):
                textos[s.hash_conteudo] = texto_para_embedding(s.titulos, s.texto)
    if not textos:
        return
    prontos = set(
        Embedding.objects.filter(modelo=modelo, hash_conteudo__in=list(textos)).values_list("hash_conteudo", flat=True)
    )
    faltam = [h for h in textos if h not in prontos]
    plano.reaproveitadas = len(textos) - len(faltam)
    if not faltam:
        return
    vetores = embedder.vetorizar([textos[h] for h in faltam])
    Embedding.objects.bulk_create(
        [
            Embedding(hash_conteudo=h, modelo=modelo, dimensao=len(v), vetor=empacotar(v))
            for h, v in zip(faltam, vetores)
        ],
        ignore_conflicts=True,
    )
    plano.vetorizadas = len(faltam)


# ------------------------------------------------------------------ publicação


def _publicar_secoes(doc: Documento, novas: list[SecaoParse], sha: str) -> None:
    antigas = list(doc.secoes.all())
    por_hash: dict[str, list[Secao]] = {}
    for s in antigas:
        por_hash.setdefault(s.hash_conteudo, []).append(s)

    manter, criar = [], []
    for ordem, p in enumerate(novas):
        candidatas = por_hash.get(p.hash_conteudo)
        if candidatas:
            s = candidatas.pop(0)
            s.ordem, s.titulos, s.ancora = ordem, p.titulos, p.ancora
            s.linha_inicio, s.linha_fim, s.commit_sha = p.linha_inicio, p.linha_fim, sha
            manter.append(s)
        else:
            criar.append(
                Secao(
                    documento=doc,
                    ordem=ordem,
                    titulos=p.titulos,
                    ancora=p.ancora,
                    linha_inicio=p.linha_inicio,
                    linha_fim=p.linha_fim,
                    texto=p.texto,
                    hash_conteudo=p.hash_conteudo,
                    commit_sha=sha,
                )
            )
    sobras = [s for lista in por_hash.values() for s in lista]
    indice.remover([s.pk for s in sobras] + [s.pk for s in manter])
    Secao.objects.filter(pk__in=[s.pk for s in sobras]).delete()
    if manter:
        Secao.objects.bulk_update(manter, ["ordem", "titulos", "ancora", "linha_inicio", "linha_fim", "commit_sha"])
    criadas = Secao.objects.bulk_create(criar)
    for s in manter + criadas:
        s.documento = doc
    if doc.incluido:
        indice.inserir(manter + criadas)


def reconstruir_relacoes(projeto) -> int:
    """Recria as relações REFERENCIA do projeto a partir dos links nas seções."""
    fontes = list(FonteGit.objects.filter(repositorio__projeto=projeto))
    Relacao.objects.filter(origem__documento__fonte__in=fontes).delete()
    docs = list(Documento.objects.filter(fonte__in=fontes, incluido=True))
    por_caminho = {(d.fonte_id, d.caminho): d for d in docs}
    secoes = list(
        Secao.objects.filter(documento__in=docs).select_related("documento").order_by("documento_id", "ordem")
    )
    por_ancora: dict[tuple[int, str], Secao] = {}
    for s in secoes:
        if s.ancora:
            por_ancora.setdefault((s.documento_id, s.ancora), s)
    fonte_por_repo = {(f.conta.lower(), f.nome_repositorio.lower()): f for f in fontes}

    novas = []
    for s in secoes:
        for alvo, linha in extrair_links(s.texto):
            a = resolver_alvo(alvo, s.documento.caminho)
            if a is None:
                continue
            if a.conta:
                f = fonte_por_repo.get((a.conta.lower(), (a.repositorio or "").lower().removesuffix(".git")))
                if f is None:
                    continue
                fonte_id = f.pk
            else:
                fonte_id = s.documento.fonte_id
            destino_doc = por_caminho.get((fonte_id, a.caminho)) or por_caminho.get(
                (fonte_id, posixpath.join(a.caminho, "README.md"))
            )
            if destino_doc is None:
                continue
            destino_secao = por_ancora.get((destino_doc.pk, a.ancora)) if a.ancora else None
            if destino_secao is not None and destino_secao.pk == s.pk:
                continue
            if destino_doc.pk == s.documento_id and destino_secao is None:
                continue
            novas.append(Relacao(origem=s, destino_documento=destino_doc, destino_secao=destino_secao, trecho=linha))
    Relacao.objects.bulk_create(novas)
    return len(novas)


def publicar(fonte: FonteGit, plano: Plano) -> None:
    with transaction.atomic():
        ids_removidas = list(Secao.objects.filter(documento_id__in=plano.removidos).values_list("pk", flat=True))
        indice.remover(ids_removidas)
        Documento.objects.filter(pk__in=plano.removidos).delete()

        for d in plano.docs:  # libera os caminhos antes de aplicar renomeações cruzadas
            if d.existente_id:
                Documento.objects.filter(pk=d.existente_id).exclude(caminho=d.caminho).update(
                    caminho=f"__renomeando__/{d.existente_id}"
                )

        for d in plano.docs:
            doc = Documento.objects.get(pk=d.existente_id) if d.existente_id else Documento(fonte=fonte)
            caminho_mudou = bool(d.existente_id) and doc.caminho != d.caminho
            doc.caminho, doc.blob_sha, doc.commit_sha = d.caminho, d.blob_sha, plano.sha
            if d.conteudo_alterado:
                doc.incluido, doc.motivo, doc.titulo = d.incluido, d.motivo, d.titulo
            doc.save()
            if d.conteudo_alterado:
                _publicar_secoes(doc, d.secoes, plano.sha)
                continue
            Secao.objects.filter(documento=doc).update(commit_sha=plano.sha)
            if caminho_mudou and doc.incluido:
                secoes = list(doc.secoes.all())
                for s in secoes:
                    s.documento = doc
                indice.remover([s.pk for s in secoes])
                indice.inserir(secoes)

        reconstruir_relacoes(fonte.repositorio.projeto)

        if any(d.incluido for d in plano.docs):
            fonte.situacao, fonte.motivo_situacao = FonteGit.SITUACAO_OK, ""
        else:
            motivos: dict[str, int] = {}
            for d in plano.docs:
                motivos[d.motivo] = motivos.get(d.motivo, 0) + 1
            resumo = ", ".join(f"{m}: {n}" for m, n in sorted(motivos.items())) or "nenhum arquivo Markdown"
            fonte.situacao = FonteGit.SITUACAO_IGNORADA
            fonte.motivo_situacao = f"Nenhum Markdown útil no commit {plano.sha[:12]} ({resumo})."
        fonte.ultimo_sha = plano.sha
        fonte.sincronizada_em = timezone.now()
        fonte.save(update_fields=["situacao", "motivo_situacao", "ultimo_sha", "sincronizada_em"])


# ------------------------------------------------------------------ execução


def _mensagem_segura(exc: Exception) -> str:
    if isinstance(exc, (git_leitura.ErroGit, EmbeddingsIndisponiveis)):
        return str(exc)[:500]
    return f"{type(exc).__name__}: {str(exc)[:300]}"


def sincronizar(fonte: FonteGit, embedder=None, sem_embeddings: bool = False, forcar: bool = False) -> Sincronizacao:
    registro = Sincronizacao.objects.create(fonte=fonte, situacao="em_andamento", sha_anterior=fonte.ultimo_sha)

    def encerrar(situacao: str, detalhe: str = "") -> Sincronizacao:
        registro.situacao, registro.detalhe, registro.terminada_em = situacao, detalhe, timezone.now()
        registro.save()
        return registro

    if not fonte.ativa:
        return encerrar("inativa")
    if fonte_restrita(fonte):
        FonteGit.objects.filter(pk=fonte.pk).update(
            situacao=FonteGit.SITUACAO_BLOQUEADA,
            motivo_situacao="Projeto restrito: a ingestão exige autorização explícita.",
        )
        fonte.refresh_from_db()
        return encerrar("bloqueada")

    agora = timezone.now()
    travou = (
        FonteGit.objects.filter(pk=fonte.pk)
        .filter(Q(sincronizando_desde__isnull=True) | Q(sincronizando_desde__lt=agora - TRAVA_EXPIRA))
        .update(sincronizando_desde=agora)
    )
    if not travou:
        return encerrar("ja_em_andamento", "Outra sincronização desta fonte está em andamento.")

    try:
        sha = git_leitura.atualizar_espelho(fonte)
        FonteGit.objects.filter(pk=fonte.pk).update(sha_remoto=sha)
        fonte.sha_remoto = sha
        registro.sha_novo = sha
        if (
            sha == fonte.ultimo_sha
            and not forcar
            and fonte.situacao in (FonteGit.SITUACAO_OK, FonteGit.SITUACAO_IGNORADA)
        ):
            return encerrar("sem_mudancas")
        if not sem_embeddings and embedder is None:
            embedder = obter_embedder()
        plano = calcular_plano(fonte, git_leitura.espelho_da_fonte(fonte), sha, embedder, sem_embeddings)
        publicar(fonte, plano)
        registro.adicionados, registro.alterados = plano.adicionados, plano.alterados
        registro.renomeados, registro.removidos = plano.renomeados, len(plano.removidos)
        registro.secoes_vetorizadas, registro.secoes_reaproveitadas = plano.vetorizadas, plano.reaproveitadas
        return encerrar(fonte.situacao, fonte.motivo_situacao)
    except Exception as exc:  # noqa: BLE001 - toda falha vira registro; o índice anterior segue publicado
        motivo = _mensagem_segura(exc)
        FonteGit.objects.filter(pk=fonte.pk).update(situacao=FonteGit.SITUACAO_FALHA, motivo_situacao=motivo)
        return encerrar("falha", motivo)
    finally:
        FonteGit.objects.filter(pk=fonte.pk).update(sincronizando_desde=None)
        fonte.refresh_from_db()
