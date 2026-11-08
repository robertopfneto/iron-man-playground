import statistics
from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from conhecimento.busca import MODOS, buscar
from conhecimento.demo.conteudo import PERGUNTAS
from conhecimento.models import FonteGit, Secao
from core.models import Agente, Projeto

ROTULOS = {
    "textual": "Textual (FTS5)",
    "hibrida": "Híbrida (FTS5 + vetores)",
    "hibrida_grafo": "Híbrida + grafo (1 salto)",
}


def _casa(chave: str, esperado: str) -> bool:
    alvo, ancora = esperado.split("#", 1)
    caminho, ancora_chave = chave.split("#", 1)
    return caminho == alvo and (ancora == "" or ancora == ancora_chave)


def _pct(valores) -> str:
    valores = [v for v in valores if v is not None]
    return f"{100 * statistics.mean(valores):.0f}%" if valores else "—"


class Command(BaseCommand):
    help = "Compara busca textual, híbrida e híbrida com grafo nas perguntas de demonstração (saída em Markdown)."

    def add_arguments(self, parser):
        parser.add_argument("--projeto", default="Projeto pessoal demonstrativo")
        parser.add_argument("--agente", default="Neto")
        parser.add_argument("--repeticoes", type=int, default=3)

    def handle(self, *args, **opcoes):
        projeto = Projeto.objects.get(nome=opcoes["projeto"])
        agente = Agente.objects.get(nome=opcoes["agente"])
        buscar(projeto.pk, agente.pk, "aquecimento do modelo", modo="hibrida")  # carrega o modelo no Ollama

        ancoras = dict(Secao.objects.values_list("pk", "ancora"))
        linhas = []
        for p in PERGUNTAS:
            for modo in MODOS:
                tempos, r = [], None
                for _ in range(opcoes["repeticoes"]):
                    r = buscar(projeto.pk, agente.pk, p["pergunta"], modo=modo)
                    tempos.append(r.tempo_ms)
                chaves = [
                    f"{t.repositorio.split('/', 1)[1]}/{t.caminho}#{ancoras.get(t.secao_id, '')}" for t in r.trechos
                ]
                esperado = p["esperado"]
                linha = {
                    "pergunta": p["pergunta"],
                    "tipo": p["tipo"],
                    "modo": modo,
                    "tempo_ms": statistics.median(tempos),
                    "caracteres": r.caracteres_contexto,
                    "trechos": len(chaves),
                    "topo": chaves[0] if chaves else "—",
                    "relacionados": sum(1 for t in r.trechos if t.origem == "relacao"),
                }
                if esperado:
                    rank = next((i + 1 for i, c in enumerate(chaves) if any(_casa(c, e) for e in esperado)), None)
                    uteis = sum(1 for c in chaves if any(_casa(c, e) for e in esperado))
                    linha.update(
                        acerto_topo=rank == 1,
                        cobertura=sum(any(_casa(c, e) for c in chaves) for e in esperado) / len(esperado),
                        rr=1 / rank if rank else 0.0,
                        precisao=uteis / len(chaves) if chaves else 0.0,
                        falso_positivo=None,
                    )
                else:
                    linha.update(acerto_topo=None, cobertura=None, rr=None, precisao=None, falso_positivo=bool(chaves))
                linhas.append(linha)

        por_modo = defaultdict(list)
        for linha in linhas:
            por_modo[linha["modo"]].append(linha)

        saida = []
        escrever = saida.append
        escrever("# Comparação de busca: textual × híbrida × híbrida com grafo\n")
        escrever(f"Gerado em {timezone.localtime():%Y-%m-%d %H:%M} por `python manage.py comparar_busca`.\n")
        escrever(
            f"- Projeto: **{projeto.nome}**, agente **{agente.nome}**. Perguntas: {len(PERGUNTAS)} "
            f"({sum(1 for p in PERGUNTAS if p['esperado'])} com resposta, "
            f"{sum(1 for p in PERGUNTAS if not p['esperado'])} sem resposta autorizada)."
        )
        escrever(
            f"- Embeddings: `{settings.EMBEDDINGS_MODELO}` via Ollama local. Limiar vetorial "
            f"{settings.CONHECIMENTO_LIMIAR_VETORIAL}, até {settings.CONHECIMENTO_MAX_TRECHOS} trechos e "
            f"{settings.CONHECIMENTO_ORCAMENTO_CARACTERES} caracteres por consulta."
        )
        fontes = FonteGit.objects.filter(repositorio__projeto=projeto).order_by("nome_repositorio")
        escrever(
            "- Fontes: "
            + ", ".join(f"`{f.nome_repositorio}@{f.ultimo_sha[:12] or '—'}` ({f.situacao})" for f in fontes)
            + f". Seções indexadas no projeto: {Secao.objects.filter(documento__fonte__in=fontes).count()}."
        )
        escrever(f"- Tempo: mediana de {opcoes['repeticoes']} execuções por pergunta, depois de aquecer o modelo.\n")

        escrever("## Resumo\n")
        escrever(
            "| Modo | Acerto no topo | Cobertura das fontes esperadas | MRR | Precisão dos trechos | "
            "Falsos positivos (sem resposta) | Tempo mediano | Contexto médio (caracteres) | Trechos médios |"
        )
        escrever("|---|---|---|---|---|---|---|---|---|")
        for modo in MODOS:
            ls = por_modo[modo]
            com = [x for x in ls if x["cobertura"] is not None]
            sem = [x for x in ls if x["falso_positivo"] is not None]
            escrever(
                f"| {ROTULOS[modo]} | {_pct(x['acerto_topo'] for x in com)} | {_pct(x['cobertura'] for x in com)} | "
                f"{statistics.mean(x['rr'] for x in com):.2f} | {_pct(x['precisao'] for x in com)} | "
                f"{sum(x['falso_positivo'] for x in sem)}/{len(sem)} | "
                f"{statistics.median(x['tempo_ms'] for x in ls):.1f} ms | "
                f"{statistics.mean(x['caracteres'] for x in ls):.0f} | {statistics.mean(x['trechos'] for x in ls):.1f} |"
            )

        escrever("\n## Cobertura por tipo de pergunta\n")
        tipos = sorted({p["tipo"] for p in PERGUNTAS if p["esperado"]})
        escrever("| Tipo | " + " | ".join(ROTULOS[m] for m in MODOS) + " |")
        escrever("|---|" + "---|" * len(MODOS))
        for tipo in tipos:
            celulas = [_pct(x["cobertura"] for x in por_modo[m] if x["tipo"] == tipo) for m in MODOS]
            escrever(f"| {tipo} | " + " | ".join(celulas) + " |")

        escrever("\n## Detalhe por pergunta\n")
        escrever("| Pergunta | Tipo | Modo | Primeiro trecho | Cobertura | Via grafo | Tempo | Caracteres |")
        escrever("|---|---|---|---|---|---|---|---|")
        for x in linhas:
            if x["cobertura"] is not None:
                cobertura = f"{100 * x['cobertura']:.0f}%"
            else:
                cobertura = "vazou evidência" if x["falso_positivo"] else "ok: sem evidência"
            escrever(
                f"| {x['pergunta']} | {x['tipo']} | {x['modo']} | `{x['topo']}` | {cobertura} | "
                f"{x['relacionados']} | {x['tempo_ms']:.1f} ms | {x['caracteres']} |"
            )
        self.stdout.write("\n".join(saida))
