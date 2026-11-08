"""Base de conhecimento a partir do Markdown versionado em Git.

Os arquivos Markdown do Git são a fonte oficial. Documento, Seção, Relação e
Embedding são derivados e podem ser reconstruídos a partir deles.
"""

from django.db import models

from core.models import Repositorio


class FonteGit(models.Model):
    """Repositório autorizado e branch monitorada. Acesso somente leitura."""

    SITUACAO_NUNCA = "nunca"
    SITUACAO_OK = "ok"
    SITUACAO_IGNORADA = "ignorada"
    SITUACAO_FALHA = "falha"
    SITUACAO_BLOQUEADA = "bloqueada"
    SITUACAO_CHOICES = [
        (SITUACAO_NUNCA, "Nunca sincronizada"),
        (SITUACAO_OK, "Sincronizada"),
        (SITUACAO_IGNORADA, "Ignorada: sem Markdown útil"),
        (SITUACAO_FALHA, "Falha na última sincronização"),
        (SITUACAO_BLOQUEADA, "Bloqueada pela política de acesso"),
    ]

    repositorio = models.OneToOneField(Repositorio, on_delete=models.CASCADE, related_name="fonte_git")
    conta = models.CharField(max_length=100, help_text="Conta ou organização no GitHub.")
    nome_repositorio = models.CharField(max_length=100)
    branch = models.CharField(max_length=200, default="main")
    url = models.CharField(
        max_length=500,
        help_text="https://github.com/<conta>/<repositorio>.git ou caminho de repositório demo local autorizado.",
    )
    incluir = models.TextField(blank=True, help_text="Padrões glob de caminhos a incluir, um por linha.")
    excluir = models.TextField(blank=True, help_text="Padrões glob de caminhos a excluir, um por linha.")
    autorizacao_explicita = models.BooleanField(
        default=False, help_text="Exigida para fontes de projetos restritos (Before)."
    )
    ativa = models.BooleanField(default=True)

    ultimo_sha = models.CharField(max_length=64, blank=True, help_text="Commit publicado no índice.")
    sha_remoto = models.CharField(max_length=64, blank=True, help_text="Último commit visto na branch.")
    situacao = models.CharField(max_length=20, choices=SITUACAO_CHOICES, default=SITUACAO_NUNCA)
    motivo_situacao = models.TextField(blank=True)
    sincronizando_desde = models.DateTimeField(null=True, blank=True)
    sincronizada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "fonte Git"
        verbose_name_plural = "fontes Git"

    def __str__(self) -> str:
        return f"{self.conta}/{self.nome_repositorio}@{self.branch}"

    @property
    def projeto(self):
        return self.repositorio.projeto


class Documento(models.Model):
    """Arquivo Markdown visto na árvore da branch. Guarda a decisão de inclusão."""

    fonte = models.ForeignKey(FonteGit, on_delete=models.CASCADE, related_name="documentos")
    caminho = models.CharField(max_length=500)
    blob_sha = models.CharField(max_length=64)
    commit_sha = models.CharField(max_length=64)
    incluido = models.BooleanField(default=False)
    motivo = models.CharField(max_length=60, help_text="Por que o arquivo foi incluído ou excluído.")
    titulo = models.CharField(max_length=300, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["fonte", "caminho"], name="documento_unico_por_caminho")]
        ordering = ["caminho"]

    def __str__(self) -> str:
        return f"{self.fonte} :: {self.caminho}"


class Secao(models.Model):
    """Trecho do Markdown delimitado por títulos, com blocos de código inteiros."""

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="secoes")
    ordem = models.PositiveIntegerField()
    titulos = models.JSONField(default=list, help_text="Hierarquia de títulos até esta seção.")
    ancora = models.CharField(max_length=200, blank=True)
    linha_inicio = models.PositiveIntegerField()
    linha_fim = models.PositiveIntegerField()
    texto = models.TextField()
    hash_conteudo = models.CharField(max_length=64, db_index=True)
    commit_sha = models.CharField(max_length=64)

    class Meta:
        ordering = ["documento_id", "ordem"]

    def __str__(self) -> str:
        return f"{self.documento.caminho}#{self.ancora}"


class Relacao(models.Model):
    """Aresta verificável do grafo: um link Markdown que resolve para um documento autorizado."""

    TIPO_REFERENCIA = "REFERENCIA"

    origem = models.ForeignKey(Secao, on_delete=models.CASCADE, related_name="relacoes_saida")
    destino_documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="relacoes_entrada")
    destino_secao = models.ForeignKey(
        Secao, on_delete=models.CASCADE, related_name="relacoes_entrada", null=True, blank=True
    )
    tipo = models.CharField(max_length=30, default=TIPO_REFERENCIA)
    trecho = models.TextField(help_text="Linha com o link que sustenta a relação.")

    def __str__(self) -> str:
        return f"{self.origem} -{self.tipo}-> {self.destino_documento.caminho}"


class Embedding(models.Model):
    """Vetor por conteúdo e modelo. Conteúdo idêntico com o mesmo modelo reaproveita o vetor."""

    hash_conteudo = models.CharField(max_length=64)
    modelo = models.CharField(max_length=100)
    dimensao = models.PositiveIntegerField()
    vetor = models.BinaryField(help_text="float32 little-endian.")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["hash_conteudo", "modelo"], name="embedding_unico_por_modelo")
        ]


class Sincronizacao(models.Model):
    """Registro de cada execução. Não guarda conteúdo, token ou caminhos fora da fonte."""

    fonte = models.ForeignKey(FonteGit, on_delete=models.CASCADE, related_name="sincronizacoes")
    iniciada_em = models.DateTimeField(auto_now_add=True)
    terminada_em = models.DateTimeField(null=True, blank=True)
    sha_anterior = models.CharField(max_length=64, blank=True)
    sha_novo = models.CharField(max_length=64, blank=True)
    situacao = models.CharField(max_length=20)
    adicionados = models.PositiveIntegerField(default=0)
    alterados = models.PositiveIntegerField(default=0)
    renomeados = models.PositiveIntegerField(default=0)
    removidos = models.PositiveIntegerField(default=0)
    secoes_vetorizadas = models.PositiveIntegerField(default=0)
    secoes_reaproveitadas = models.PositiveIntegerField(default=0)
    detalhe = models.TextField(blank=True)

    class Meta:
        ordering = ["-iniciada_em"]
