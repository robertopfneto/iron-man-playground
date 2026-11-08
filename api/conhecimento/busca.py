"""Busca híbrida para Neto e os especialistas.

O escopo (fontes autorizadas para o agente no projeto) é calculado antes de
recuperar qualquer candidato e reaplicado ao seguir relações. O texto da pergunta
nunca amplia o escopo.
"""

import re
import time
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field

from django.conf import settings

from conhecimento import indice
from conhecimento.embeddings import EmbeddingsIndisponiveis, desempacotar, obter_embedder, similaridade
from conhecimento.models import Embedding, Relacao, Secao
from conhecimento.politica import fontes_autorizadas

MODOS = ("textual", "hibrida", "hibrida_grafo")
RRF_K = 60
MAX_CARACTERES_TRECHO = 900
CANDIDATOS_POR_CANAL = 20
MARGEM_VETORIAL = 0.1


@dataclass
class Trecho:
    secao_id: int
    repositorio: str
    caminho: str
    secao: str
    linhas: str
    commit: str
    link: str
    texto: str
    origem: str
    via: str = ""
    pontuacao: float = 0.0


@dataclass
class ResultadoBusca:
    modo: str
    trechos: list[Trecho] = field(default_factory=list)
    fontes: list[dict] = field(default_factory=list)
    sem_evidencia: bool = True
    avisos: list[str] = field(default_factory=list)
    caracteres_contexto: int = 0
    tempo_ms: float = 0.0

    def como_dict(self) -> dict:
        return asdict(self)


def link_para_commit(fonte, caminho: str, commit: str, inicio: int, fim: int) -> str:
    base = f"{fonte.conta}/{fonte.nome_repositorio}/blob/{commit}/{caminho}#L{inicio}-L{fim}"
    if fonte.url.startswith("https://github.com/"):
        return f"https://github.com/{base}"
    return f"local:{base}"  # repositório demo local: não aponta para um GitHub que não existe


def _vetorial(pergunta: str, fonte_ids: list[int], embedder) -> list[tuple[int, float]]:
    consulta = embedder.vetorizar([pergunta])[0]
    secoes = list(
        Secao.objects.filter(documento__fonte_id__in=fonte_ids, documento__incluido=True).values_list(
            "id", "hash_conteudo"
        )
    )
    vetores = dict(
        Embedding.objects.filter(
            modelo=settings.EMBEDDINGS_MODELO, hash_conteudo__in={h for _, h in secoes}
        ).values_list("hash_conteudo", "vetor")
    )
    pontuadas = [(sid, similaridade(consulta, desempacotar(vetores[h]))) for sid, h in secoes if h in vetores]
    if not pontuadas:
        return []
    # Limiar absoluto contra perguntas sem resposta; margem relativa contra vizinhos fracos do melhor trecho.
    melhor = max(p[1] for p in pontuadas)
    corte = max(settings.CONHECIMENTO_LIMIAR_VETORIAL, melhor - MARGEM_VETORIAL)
    pontuadas = [p for p in pontuadas if p[1] >= corte]
    return sorted(pontuadas, key=lambda p: -p[1])[:CANDIDATOS_POR_CANAL]


def _textual(pergunta: str, fonte_ids: list[int]) -> list[tuple[int, float]]:
    """FTS5 com OR para não perder variações, mas exigindo 2 termos quando a pergunta tem 3 ou mais."""
    candidatos = indice.buscar(pergunta, fonte_ids, CANDIDATOS_POR_CANAL)
    termos = indice.termos(pergunta)
    minimo = 1 if len(termos) <= 2 else 2
    if minimo == 1 or not candidatos:
        return candidatos
    textos = {
        s.pk: _sem_acentos(" ".join(s.titulos) + " " + s.texto + " " + s.documento.caminho)
        for s in Secao.objects.select_related("documento").filter(pk__in=[c[0] for c in candidatos])
    }
    termos_norm = [_sem_acentos(t) for t in termos]
    return [
        c for c in candidatos if sum(1 for t in termos_norm if re.search(rf"\b{re.escape(t)}", textos.get(c[0], ""))) >= minimo
    ]


def _sem_acentos(texto: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(ch) != "Mn")


def _vizinhos(ids: list[int], fonte_ids: list[int]) -> list[tuple[int, int, str]]:
    """(secao_vizinha, secao_de_origem, trecho do link), um salto, só dentro das fontes autorizadas."""
    vizinhos = []
    saida = Relacao.objects.filter(
        origem_id__in=ids, destino_documento__fonte_id__in=fonte_ids, destino_documento__incluido=True
    ).select_related("destino_documento")
    for r in saida:
        alvo = r.destino_secao_id or (
            Secao.objects.filter(documento=r.destino_documento).order_by("ordem").values_list("id", flat=True).first()
        )
        if alvo:
            vizinhos.append((alvo, r.origem_id, r.trecho))
    entrada = Relacao.objects.filter(destino_secao_id__in=ids, origem__documento__fonte_id__in=fonte_ids)
    for r in entrada:
        vizinhos.append((r.origem_id, r.destino_secao_id, r.trecho))
    return vizinhos


def buscar(
    projeto_id: int,
    agente_id: int,
    pergunta: str,
    modo: str = "hibrida_grafo",
    max_trechos: int | None = None,
    orcamento: int | None = None,
    embedder=None,
) -> ResultadoBusca:
    if modo not in MODOS:
        raise ValueError(f"Modo de busca inválido: {modo}")
    inicio = time.perf_counter()
    max_trechos = max_trechos or settings.CONHECIMENTO_MAX_TRECHOS
    orcamento = orcamento or settings.CONHECIMENTO_ORCAMENTO_CARACTERES
    resultado = ResultadoBusca(modo=modo)

    fontes = {f.pk: f for f in fontes_autorizadas(projeto_id, agente_id) if f.ultimo_sha}
    for f in fontes.values():
        atrasada = bool(f.sha_remoto) and f.sha_remoto != f.ultimo_sha
        resultado.fontes.append(
            {
                "repositorio": f"{f.conta}/{f.nome_repositorio}",
                "branch": f.branch,
                "sha_indexado": f.ultimo_sha,
                "sha_remoto": f.sha_remoto,
                "atrasada": atrasada,
            }
        )
        if atrasada:
            resultado.avisos.append(
                f"O índice de {f.conta}/{f.nome_repositorio} está no commit {f.ultimo_sha[:12]}; "
                f"a branch {f.branch} já tem {f.sha_remoto[:12]}."
            )
    if not fontes:
        resultado.avisos.append("Não há documentação indexada e autorizada para este agente neste projeto.")
        resultado.tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
        return resultado
    fonte_ids = list(fontes)

    pontos: Counter = Counter()
    canais: dict[int, set[str]] = {}
    for pos, (sid, _) in enumerate(_textual(pergunta, fonte_ids)):
        pontos[sid] += 1 / (RRF_K + pos + 1)
        canais.setdefault(sid, set()).add("textual")
    if modo != "textual":
        try:
            vetorial = _vetorial(pergunta, fonte_ids, embedder or obter_embedder())
        except EmbeddingsIndisponiveis:
            vetorial = []
            resultado.avisos.append("Busca vetorial indisponível agora; usei só a busca textual.")
        for pos, (sid, _) in enumerate(vetorial):
            pontos[sid] += 1 / (RRF_K + pos + 1)
            canais.setdefault(sid, set()).add("vetorial")

    ordenados = [sid for sid, _ in pontos.most_common()]
    reservar_para_grafo = 1 if modo == "hibrida_grafo" and len(ordenados) >= max_trechos else 0
    principais = ordenados[: max_trechos - reservar_para_grafo]
    candidatos: list[tuple[int, str, str, float]] = [
        (sid, "ambos" if len(canais[sid]) > 1 else next(iter(canais[sid])), "", pontos[sid]) for sid in principais
    ]
    if modo == "hibrida_grafo" and principais:
        ja = set(principais)
        for vizinho, pai, trecho in _vizinhos(principais[:3], fonte_ids):
            if vizinho not in ja:
                ja.add(vizinho)
                candidatos.append((vizinho, "relacao", trecho, pontos.get(pai, 0) * 0.5))

    secoes = Secao.objects.select_related("documento__fonte").in_bulk([c[0] for c in candidatos])
    usados = 0
    for sid, origem, via, ponto in candidatos:
        s = secoes.get(sid)
        if s is None or s.documento.fonte_id not in fontes or not s.documento.incluido:
            continue
        texto = s.texto if len(s.texto) <= MAX_CARACTERES_TRECHO else s.texto[: MAX_CARACTERES_TRECHO - 1] + "…"
        if len(resultado.trechos) >= max_trechos or usados + len(texto) > orcamento:
            if resultado.trechos:
                break
            texto = texto[: orcamento - 1] + "…"
        fonte = s.documento.fonte
        resultado.trechos.append(
            Trecho(
                secao_id=s.pk,
                repositorio=f"{fonte.conta}/{fonte.nome_repositorio}",
                caminho=s.documento.caminho,
                secao=" > ".join(s.titulos),
                linhas=f"L{s.linha_inicio}-L{s.linha_fim}",
                commit=s.commit_sha,
                link=link_para_commit(fonte, s.documento.caminho, s.commit_sha, s.linha_inicio, s.linha_fim),
                texto=texto,
                origem=origem,
                via=via,
                pontuacao=round(ponto, 5),
            )
        )
        usados += len(texto)

    resultado.sem_evidencia = not resultado.trechos
    if resultado.sem_evidencia:
        resultado.avisos.append("Não encontrei evidência autorizada para essa pergunta.")
    resultado.caracteres_contexto = usados
    resultado.tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
    return resultado


# ------------------------------------------------------------------ Kernighan

PALAVRAS_DE_CODIGO = {
    "def", "class", "return", "import", "from", "self", "true", "false", "none", "null", "const", "let",
    "function", "async", "await", "elif", "else", "for", "while", "with", "print", "pass", "and", "not",
}


def consulta_de_diff(diff: str) -> str:
    """Resume um diff unificado em termos de busca: arquivos, comandos e identificadores alterados."""
    arquivos, termos = [], Counter()
    for linha in diff.splitlines():
        if linha.startswith(("+++ ", "--- ")):
            caminho = linha[4:].strip().removeprefix("a/").removeprefix("b/")
            if caminho != "/dev/null":
                arquivos.append(caminho)
            continue
        if linha.startswith(("+", "-")) and not linha.startswith(("++", "--")):
            for t in re.findall(r"--?[a-z][\w-]+|[A-Za-z_][\w]{2,}", linha[1:]):
                t = t.lower()
                if t not in PALAVRAS_DE_CODIGO:
                    termos[t] += 1
    nomes = {re.sub(r"\.\w+$", "", c.rsplit("/", 1)[-1]) for c in arquivos}
    return " ".join(list(nomes) + [t.lstrip("-") for t, _ in termos.most_common(12)])


def guias_afetados(projeto_id: int, agente_id: int, diff: str, embedder=None) -> ResultadoBusca:
    """Mesma busca do Neto, a partir de um diff: guias que provavelmente precisam de revisão."""
    return buscar(projeto_id, agente_id, consulta_de_diff(diff), modo="hibrida_grafo", embedder=embedder)
