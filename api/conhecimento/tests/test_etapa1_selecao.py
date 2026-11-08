"""Etapa 1: cadastro e seleção de fontes."""

from conhecimento.git_leitura import espelho_da_fonte
from conhecimento.models import Documento, FonteGit, Secao
from conhecimento.sincronizacao import sincronizar
from conhecimento.tests.apoio import FERRAMENTA, SEM_DOC_UTIL, SEM_README, BaseConhecimento
from core.models import Projeto


class SelecaoDeFontesTests(BaseConhecimento):
    def test_repositorio_sem_documentacao_util_e_ignorado_com_motivo(self):
        fonte, repo = self.criar_fonte("repo-vazio", SEM_DOC_UTIL)
        registro = sincronizar(fonte)

        self.assertEqual(registro.situacao, FonteGit.SITUACAO_IGNORADA)
        self.assertEqual(fonte.situacao, FonteGit.SITUACAO_IGNORADA)
        self.assertIn("Nenhum Markdown útil", fonte.motivo_situacao)
        motivos = dict(Documento.objects.filter(fonte=fonte).values_list("caminho", "motivo"))
        self.assertEqual(motivos["README.md"], "vazio")
        self.assertEqual(motivos["CHANGELOG.md"], "gerado")
        self.assertEqual(motivos["vendor/lib/README.md"], "dependencia")
        self.assertIn(motivos["docs/TODO.md"], ("vazio", "placeholder"))
        self.assertFalse(Secao.objects.filter(documento__fonte=fonte).exists())

    def test_repositorio_sem_readme_com_guia_util_e_indexado(self):
        fonte, _ = self.criar_fonte("notas-sem-readme", SEM_README)
        sincronizar(fonte)

        self.assertEqual(fonte.situacao, FonteGit.SITUACAO_OK)
        guia = Documento.objects.get(fonte=fonte, caminho="GUIA_DE_USO.md")
        self.assertTrue(guia.incluido)
        self.assertEqual(guia.motivo, "incluido")
        self.assertTrue(guia.secoes.exists())

    def test_decisao_de_cada_arquivo_e_verificavel(self):
        fonte, _ = self.criar_fonte("ferramenta-cli", FERRAMENTA)
        sincronizar(fonte)

        decisoes = {d.caminho: (d.incluido, d.motivo) for d in Documento.objects.filter(fonte=fonte)}
        self.assertEqual(decisoes["README.md"], (True, "incluido"))
        self.assertEqual(decisoes["docs/uso.md"], (True, "incluido"))
        self.assertEqual(decisoes["node_modules/pacote/README.md"], (False, "dependencia"))
        for documento in Documento.objects.filter(fonte=fonte):
            self.assertEqual(documento.commit_sha, fonte.ultimo_sha)

    def test_filtros_de_incluir_e_excluir_por_repositorio(self):
        fonte, _ = self.criar_fonte("ferramenta-cli", FERRAMENTA, incluir="docs/*", excluir="docs/adr/*")
        sincronizar(fonte)

        decisoes = dict(Documento.objects.filter(fonte=fonte).values_list("caminho", "motivo"))
        self.assertEqual(decisoes["README.md"], "fora_do_filtro")
        self.assertEqual(decisoes["docs/adr/0001-formato-saida.md"], "excluido_por_filtro")
        self.assertEqual(decisoes["docs/uso.md"], "incluido")

    def test_fonte_da_before_fica_fora_da_ingestao_ate_autorizacao(self):
        before = Projeto.objects.create(nome="Before", cenario="Before")
        fonte, _ = self.criar_fonte("repo-before", FERRAMENTA, projeto=before)
        registro = sincronizar(fonte)

        self.assertEqual(registro.situacao, "bloqueada")
        self.assertEqual(fonte.situacao, FonteGit.SITUACAO_BLOQUEADA)
        self.assertFalse(espelho_da_fonte(fonte).exists(), "nenhum fetch deve acontecer")
        self.assertFalse(Documento.objects.filter(fonte=fonte).exists())

        fonte.autorizacao_explicita = True
        fonte.save()
        self.assertEqual(sincronizar(fonte).situacao, FonteGit.SITUACAO_OK)

    def test_origem_fora_da_area_autorizada_e_recusada(self):
        fonte, _ = self.criar_fonte("ferramenta-cli", FERRAMENTA)
        fonte.url = str(self.tmp)  # existe, mas está fora da área de fontes autorizadas
        fonte.save()
        registro = sincronizar(fonte)

        self.assertEqual(registro.situacao, "falha")
        self.assertIn("Origem não autorizada", fonte.motivo_situacao)
        self.assertEqual(fonte.ultimo_sha, "")

    def test_url_do_github_de_outra_conta_e_recusada_sem_rede(self):
        fonte, _ = self.criar_fonte("ferramenta-cli", FERRAMENTA)
        fonte.url = "https://github.com/outra-conta/ferramenta-cli.git"
        fonte.save()
        registro = sincronizar(fonte)

        self.assertEqual(registro.situacao, "falha")
        self.assertIn("não corresponde", fonte.motivo_situacao)
        self.assertFalse(espelho_da_fonte(fonte).exists())
