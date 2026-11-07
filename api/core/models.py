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
