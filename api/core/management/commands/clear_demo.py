from django.core.management.base import BaseCommand

from core.models import Agente, Projeto, Repositorio


class Command(BaseCommand):
    help = "Remove somente os registros marcados como demo=True. Projetos reais não são afetados."

    def handle(self, *args, **options):
        repos, _ = Repositorio.objects.filter(demo=True).delete()
        projs, _ = Projeto.objects.filter(demo=True).delete()
        agentes, _ = Agente.objects.filter(demo=True).delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Removidos: {projs or 0} projeto(s), {repos or 0} repositório(s), "
                f"{agentes or 0} agente(s) demo."
            )
        )
