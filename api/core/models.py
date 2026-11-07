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

    # Metadados de direção de arte da Entrega 4A. Nenhuma foto ou dado pessoal
    # é armazenado aqui — só texto descritivo de identidade visual e a fonte
    # pública consultada, conforme docs/seguranca.md.
    homenagem = models.CharField(max_length=200, blank=True)
    direcao_arte = models.TextField(blank=True)
    referencia_visual = models.TextField(blank=True)

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


class Conversa(models.Model):
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="conversas")
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Conversa #{self.id} ({self.projeto.nome})"


class Mensagem(models.Model):
    AUTOR_USUARIO = "usuario"
    AUTOR_NETO = "neto"
    AUTOR_CHOICES = [(AUTOR_USUARIO, "Usuário"), (AUTOR_NETO, "Neto")]

    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="mensagens")
    autor = models.CharField(max_length=20, choices=AUTOR_CHOICES)
    conteudo = models.TextField()
    ordem = models.PositiveIntegerField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ordem"]

    def __str__(self) -> str:
        return f"{self.autor}: {self.conteudo[:40]}"


class Convocacao(models.Model):
    SITUACAO_PROPOSTA = "proposta"
    SITUACAO_CONFIRMADA = "confirmada"
    SITUACAO_CONCLUIDA = "concluida"
    SITUACAO_CHOICES = [
        (SITUACAO_PROPOSTA, "Proposta"),
        (SITUACAO_CONFIRMADA, "Confirmada"),
        (SITUACAO_CONCLUIDA, "Concluída"),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="convocacoes")
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="convocacoes")
    mensagem_origem = models.ForeignKey(Mensagem, on_delete=models.CASCADE, related_name="convocacoes")
    tarefa = models.TextField()
    situacao = models.CharField(max_length=20, choices=SITUACAO_CHOICES, default=SITUACAO_PROPOSTA)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Convocação #{self.id} ({self.get_situacao_display()})"


class Turno(models.Model):
    SITUACAO_CONVOCADO = "convocado"
    SITUACAO_EM_ANDAMENTO = "em_andamento"
    SITUACAO_AGUARDANDO_REVISAO = "aguardando_revisao"
    SITUACAO_CONCLUIDO = "concluido"
    SITUACAO_CHOICES = [
        (SITUACAO_CONVOCADO, "Convocado"),
        (SITUACAO_EM_ANDAMENTO, "Em andamento"),
        (SITUACAO_AGUARDANDO_REVISAO, "Aguardando revisão"),
        (SITUACAO_CONCLUIDO, "Concluído"),
    ]

    convocacao = models.ForeignKey(Convocacao, on_delete=models.CASCADE, related_name="turnos")
    agente = models.ForeignKey(Agente, on_delete=models.CASCADE, related_name="turnos")
    tarefa = models.TextField()
    formato_entrega = models.CharField(max_length=200, blank=True)
    situacao = models.CharField(max_length=20, choices=SITUACAO_CHOICES, default=SITUACAO_CONVOCADO)
    resultado = models.TextField(blank=True)
    autoria = models.CharField(max_length=100, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    concluido_em = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Turno de {self.agente.nome} ({self.get_situacao_display()})"


class Decisao(models.Model):
    SITUACAO_PROPOSTA = "proposta"
    SITUACAO_APROVADA = "aprovada"
    SITUACAO_REJEITADA = "rejeitada"
    SITUACAO_CHOICES = [
        (SITUACAO_PROPOSTA, "Proposta"),
        (SITUACAO_APROVADA, "Aprovada"),
        (SITUACAO_REJEITADA, "Rejeitada"),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="decisoes")
    convocacao = models.ForeignKey(
        Convocacao, on_delete=models.SET_NULL, related_name="decisoes", null=True, blank=True
    )
    texto = models.TextField()
    situacao = models.CharField(max_length=20, choices=SITUACAO_CHOICES, default=SITUACAO_PROPOSTA)
    criado_em = models.DateTimeField(auto_now_add=True)
    aprovada_em = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Decisão #{self.id} ({self.get_situacao_display()})"


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
