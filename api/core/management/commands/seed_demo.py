from django.core.management.base import BaseCommand

from core.models import AcessoAgente, Agente, ConfiguracaoModelo, Projeto, Repositorio

AGENTES = {
    "Neto": {"especialidade": "Coordenação", "responsabilidades": "Único interlocutor direto do usuário."},
    "Hamilton": {"especialidade": "Implementação", "responsabilidades": "Mudanças de código."},
    "Kernighan": {"especialidade": "Documentação", "responsabilidades": "Revisão de README e docs."},
    "Pistori": {"especialidade": "Visão computacional", "responsabilidades": "INOVISÃO."},
    "Kohavi": {"especialidade": "Avaliação experimental", "responsabilidades": "Comparação de experimentos."},
}


class Command(BaseCommand):
    help = "Carrega o catálogo inicial (agentes, projetos, acessos) de forma idempotente."

    def handle(self, *args, **options):
        agentes = {}
        for nome, dados in AGENTES.items():
            agente, _ = Agente.objects.get_or_create(nome=nome, defaults={**dados, "demo": True})
            agentes[nome] = agente
            ConfiguracaoModelo.objects.get_or_create(
                agente=agente, defaults={"modo": ConfiguracaoModelo.MODO_MANUAL, "habilitado": True}
            )

        projeto_pessoal, criado = Projeto.objects.get_or_create(
            nome="Projeto pessoal demonstrativo",
            demo=True,
            defaults={
                "cenario": "Demonstração",
                "objetivo": "Dados de exemplo para validar as Entregas 1 e 2.",
                "situacao": "ativo",
            },
        )
        Repositorio.objects.get_or_create(
            projeto=projeto_pessoal,
            nome="repositorio-demo",
            demo=True,
            defaults={"documentacao_entrada": "README de exemplo."},
        )

        projeto_educagente, _ = Projeto.objects.get_or_create(
            nome="EducaGente",
            demo=True,
            defaults={
                "cenario": "Projeto pessoal",
                "objetivo": "Cenário demonstrativo com mais de um agente autorizado.",
                "situacao": "ativo",
            },
        )

        projeto_inovisao, _ = Projeto.objects.get_or_create(
            nome="INOVISÃO",
            demo=True,
            defaults={
                "cenario": "Catálogo",
                "objetivo": "Cenário de visão computacional do grupo INOVISÃO.",
                "situacao": "ativo",
            },
        )

        vinculos = [
            (projeto_pessoal, agentes["Neto"]),
            (projeto_pessoal, agentes["Hamilton"]),
            (projeto_educagente, agentes["Neto"]),
            (projeto_educagente, agentes["Hamilton"]),
            (projeto_educagente, agentes["Kernighan"]),
            (projeto_inovisao, agentes["Neto"]),
            (projeto_inovisao, agentes["Pistori"]),
            (projeto_inovisao, agentes["Kohavi"]),
        ]
        for projeto, agente in vinculos:
            AcessoAgente.objects.get_or_create(projeto=projeto, agente=agente, defaults={"ativo": True})

        if criado:
            self.stdout.write(self.style.SUCCESS("Dados demonstrativos criados."))
        else:
            self.stdout.write("Dados demonstrativos já existiam; nada a fazer.")
