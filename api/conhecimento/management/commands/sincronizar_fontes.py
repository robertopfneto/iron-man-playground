import time

from django.core.management.base import BaseCommand

from conhecimento.models import FonteGit
from conhecimento.sincronizacao import sincronizar


class Command(BaseCommand):
    help = (
        "Sincroniza o índice com as branches monitoradas (git fetch + atualização incremental). "
        "Use manualmente ou por agendamento (cron)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--fonte", type=int, action="append", help="Id da fonte (repita para várias).")
        parser.add_argument("--forcar", action="store_true", help="Reprocessa mesmo sem commit novo.")
        parser.add_argument("--sem-embeddings", action="store_true", help="Indexa só texto e grafo.")
        parser.add_argument("--intervalo", type=int, default=0, help="Repete a cada N segundos (0 = uma vez).")

    def handle(self, *args, **opcoes):
        while True:
            fontes = FonteGit.objects.filter(ativa=True)
            if opcoes["fonte"]:
                fontes = fontes.filter(pk__in=opcoes["fonte"])
            for fonte in fontes.order_by("pk"):
                r = sincronizar(fonte, sem_embeddings=opcoes["sem_embeddings"], forcar=opcoes["forcar"])
                self.stdout.write(
                    f"{fonte}: {r.situacao} | {r.sha_anterior[:12] or '-'} -> {r.sha_novo[:12] or '-'} | "
                    f"+{r.adicionados} ~{r.alterados} >{r.renomeados} -{r.removidos} | "
                    f"vetorizadas {r.secoes_vetorizadas}, reaproveitadas {r.secoes_reaproveitadas}"
                    + (f" | {r.detalhe}" if r.detalhe else "")
                )
            if not opcoes["intervalo"]:
                break
            time.sleep(opcoes["intervalo"])
