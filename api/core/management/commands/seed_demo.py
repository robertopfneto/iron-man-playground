from django.core.management.base import BaseCommand

from core.models import Agente, Projeto, Repositorio


class Command(BaseCommand):
    help = "Carrega o catálogo inicial e um projeto pessoal demonstrativo (idempotente)."

    def handle(self, *args, **options):
        agente, _ = Agente.objects.get_or_create(
            nome="Neto",
            defaults={
                "especialidade": "Coordenação",
                "responsabilidades": "Único interlocutor direto do usuário.",
                "demo": True,
            },
        )

        projeto, criado = Projeto.objects.get_or_create(
            nome="Projeto pessoal demonstrativo",
            demo=True,
            defaults={
                "cenario": "Demonstração",
                "objetivo": "Dados de exemplo para validar a Entrega 1.",
                "situacao": "ativo",
            },
        )

        Repositorio.objects.get_or_create(
            projeto=projeto,
            nome="repositorio-demo",
            demo=True,
            defaults={"documentacao_entrada": "README de exemplo."},
        )

        if criado:
            self.stdout.write(self.style.SUCCESS("Dados demonstrativos criados."))
        else:
            self.stdout.write("Dados demonstrativos já existiam; nada a fazer.")
