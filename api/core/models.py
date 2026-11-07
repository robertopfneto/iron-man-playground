from django.db import models


class Projeto(models.Model):
    """Domínio mínimo da Entrega 1. Entregas seguintes adicionam política de acesso detalhada."""

    nome = models.CharField(max_length=200)
    cenario = models.CharField(max_length=200, blank=True)
    objetivo = models.TextField(blank=True)
    situacao = models.CharField(max_length=50, default="ativo")
    demo = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.nome


class Repositorio(models.Model):
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="repositorios")
    nome = models.CharField(max_length=200)
    referencia_git = models.CharField(max_length=500, blank=True)
    documentacao_entrada = models.TextField(blank=True)
    demo = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.projeto.nome} / {self.nome}"


class Agente(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    especialidade = models.CharField(max_length=200, blank=True)
    responsabilidades = models.TextField(blank=True)
    formato_entrega = models.CharField(max_length=200, blank=True)
    demo = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.nome


class AcessoAgente(models.Model):
    """Vínculo de um agente autorizado em um projeto (Entrega 2)."""

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="acessos_agente")
    agente = models.ForeignKey(Agente, on_delete=models.CASCADE, related_name="acessos_projeto")
    ativo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("projeto", "agente")

    def __str__(self) -> str:
        return f"{self.agente.nome} @ {self.projeto.nome}"


class ConfiguracaoModelo(models.Model):
    """Configuração de modelo por agente. Credenciais ficam fora deste modelo (servidor)."""

    MODO_MANUAL = "manual"
    MODO_CHOICES = [(MODO_MANUAL, "Manual")]

    agente = models.OneToOneField(Agente, on_delete=models.CASCADE, related_name="configuracao_modelo")
    modo = models.CharField(max_length=20, choices=MODO_CHOICES, default=MODO_MANUAL)
    provedor = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    limite_entrada = models.PositiveIntegerField(null=True, blank=True)
    limite_saida = models.PositiveIntegerField(null=True, blank=True)
    habilitado = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Config de {self.agente.nome}"


class Contexto(models.Model):
    """Contexto de uma tarefa, escopado a um projeto e a um agente autorizado nele."""

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="contextos")
    agente = models.ForeignKey(Agente, on_delete=models.CASCADE, related_name="contextos")
    pedido = models.TextField()
    objetivo_projeto = models.TextField(blank=True)
    decisoes_relevantes = models.TextField(blank=True)
    formato_entrega = models.CharField(max_length=200, blank=True)
    referencias = models.ManyToManyField(Repositorio, blank=True, related_name="contextos")
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Contexto de {self.agente.nome} em {self.projeto.nome}"
