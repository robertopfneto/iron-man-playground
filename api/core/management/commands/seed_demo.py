from django.core.management.base import BaseCommand

from core.models import AcessoAgente, Agente, ConfiguracaoModelo, Projeto, Repositorio

AGENTES = {
    "Neto": {
        "especialidade": "Coordenação",
        "responsabilidades": "Único interlocutor direto do usuário.",
        "homenagem": "Roberto Neto",
        "direcao_arte": "Cabelo escuro curto e ondulado. Camiseta preta com acentos azul e dourado.",
        "referencia_visual": "Fotos privadas do evento (não versionadas); arte definitiva pendente.",
    },
    "Hamilton": {
        "especialidade": "Implementação",
        "responsabilidades": "Mudanças de código.",
        "homenagem": "Margaret Hamilton",
        "direcao_arte": "Jaqueta azul-ardósia, pilha vertical de pastas claras.",
        "referencia_visual": "Fotografia do Smithsonian / perfil da NASA (referência textual apenas).",
    },
    "Kernighan": {
        "especialidade": "Documentação",
        "responsabilidades": "Revisão de README e docs.",
        "homenagem": "Brian Kernighan",
        "direcao_arte": "Cardigã grafite com acento amarelo de papel e manual estreito de duas abas.",
        "referencia_visual": "Perfil da Universidade de Princeton (referência textual apenas).",
    },
    "Pistori": {
        "especialidade": "Visão computacional",
        "responsabilidades": "INOVISÃO.",
        "homenagem": "Hemerson Pistori",
        "direcao_arte": "Cabelo curto grisalho, óculos retangulares escuros, cavanhaque alongado.",
        "referencia_visual": "Fotos privadas do INOVISÃO (não versionadas); arte definitiva pendente.",
    },
    "Kohavi": {
        "especialidade": "Avaliação experimental",
        "responsabilidades": "Comparação de experimentos.",
        "homenagem": "Ron Kohavi",
        "direcao_arte": "Colete verde-lima suave e duas placas verticais lado a lado.",
        "referencia_visual": "Apresentação visual do Experiment Guide (referência textual apenas).",
    },
    "LeCun": {
        "especialidade": "Before (catálogo, sem acesso operacional)",
        "responsabilidades": "Treinamento de modelos.",
        "homenagem": "Yann LeCun",
        "direcao_arte": "Jaqueta azul-cobalto, bloco com três camadas empilhadas.",
        "referencia_visual": "Perfil da NYU (referência textual apenas).",
    },
    "Hopper": {
        "especialidade": "Before (catálogo, sem acesso operacional)",
        "responsabilidades": "Integração de APIs.",
        "homenagem": "Grace Hopper",
        "direcao_arte": "Silhueta naval, quepe branco, conector dourado de duas pontas.",
        "referencia_visual": "Fotografia da Marinha dos EUA (referência textual apenas).",
    },
    "Liskov": {
        "especialidade": "Before (catálogo, sem acesso operacional)",
        "responsabilidades": "Contratos e revisão de arquitetura.",
        "homenagem": "Barbara Liskov",
        "direcao_arte": "Jaqueta vinho, prancheta com duas caixas encaixadas.",
        "referencia_visual": "Perfil do MIT CSAIL (referência textual apenas).",
    },
    "Lamport": {
        "especialidade": "Before (catálogo, sem acesso operacional)",
        "responsabilidades": "Ordenação e assincronismo.",
        "homenagem": "Leslie Lamport",
        "direcao_arte": "Colete verde-oliva, três cartões enfileirados, relógio na ficha.",
        "referencia_visual": "Conversa da Microsoft Research (referência textual apenas).",
    },
    "Salton": {
        "especialidade": "Busca bibliográfica",
        "responsabilidades": "INOVISÃO.",
        "homenagem": "Gerard Salton",
        "direcao_arte": "Casaco ameixa, fichário fino, lupa redonda.",
        "referencia_visual": "IT History Society / memorial de Cornell (referência textual apenas).",
    },
    "Luhn": {
        "especialidade": "Triagem e extração de evidências",
        "responsabilidades": "INOVISÃO.",
        "homenagem": "Hans Peter Luhn",
        "direcao_arte": "Casaco cobre fosco, cartão com faixa perfurada.",
        "referencia_visual": "IT History Society (referência textual apenas).",
    },
    "Hamming": {
        "especialidade": "Formulação do problema",
        "responsabilidades": "INOVISÃO.",
        "homenagem": "Richard Hamming",
        "direcao_arte": "Casaco em tom de areia, peça quadrada com grade curta.",
        "referencia_visual": "Universidade de St Andrews (referência textual apenas).",
    },
    "Knuth": {
        "especialidade": "Composição e algoritmos",
        "responsabilidades": "INOVISÃO.",
        "homenagem": "Donald Knuth",
        "direcao_arte": "Casaco azul-petróleo, caderno aberto com marca de composição.",
        "referencia_visual": "Kyoto Prize (referência textual apenas).",
    },
    "Fei-Fei": {
        "especialidade": "Avaliação de predições",
        "responsabilidades": "INOVISÃO.",
        "homenagem": "Fei-Fei Li",
        "direcao_arte": "Casaco violeta, visor quadrado com ponto central.",
        "referencia_visual": "Stanford HAI (referência textual apenas).",
    },
    "Torralba": {
        "especialidade": "Curadoria e anotação",
        "responsabilidades": "INOVISÃO.",
        "homenagem": "Antonio Torralba",
        "direcao_arte": "Sobreposição ciano escuro, moldura de anotação aberta.",
        "referencia_visual": "MIT CSAIL (referência textual apenas).",
    },
    "Torvalds": {
        "especialidade": "Histórico de versões",
        "responsabilidades": "INOVISÃO.",
        "homenagem": "Linus Torvalds",
        "direcao_arte": "Camiseta cinza, sobreposição verde-menta, ramo com três nós.",
        "referencia_visual": "Galeria da Linux Foundation (referência textual apenas).",
    },
    "Papert": {
        "especialidade": "Tutoria pela experimentação",
        "responsabilidades": "Pessoal e faculdade.",
        "homenagem": "Seymour Papert",
        "direcao_arte": "Casaco azul suave, tartaruga geométrica ilustrativa.",
        "referencia_visual": "Memorial do MIT Media Lab (referência textual apenas).",
    },
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
