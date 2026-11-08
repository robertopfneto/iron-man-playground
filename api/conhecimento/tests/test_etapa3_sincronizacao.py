"""Etapa 3: sincronização incremental com Git."""

from datetime import timedelta
from unittest import mock

from django.utils import timezone

from conhecimento import indice
from conhecimento.models import Documento, Embedding, FonteGit, Secao, Sincronizacao
from conhecimento.sincronizacao import sincronizar
from conhecimento.tests.apoio import FERRAMENTA, BaseConhecimento, EmbedderFalso, EmbedderQuebrado

ANTIGO = "# Notas antigas\n\nProcedimento xilofone descontinuado que explicava a calibração manual do sensor antigo.\n"
NOVO = "# Publicação\n\nPara publicar uma versão, gere o pacote com o comando de build e envie com a ferramenta de release.\n"


class SincronizacaoIncrementalTests(BaseConhecimento):
    def setUp(self):
        super().setUp()
        self.fonte, self.repo = self.criar_fonte("ferramenta-cli", {**FERRAMENTA, "docs/antigo.md": ANTIGO})
        self.primeiro = sincronizar(self.fonte)
        self.sha1 = self.fonte.ultimo_sha

    def _ids(self, caminho):
        return {s.ancora: s.pk for s in Secao.objects.filter(documento__fonte=self.fonte, documento__caminho=caminho)}

    def test_inclusao_alteracao_renomeacao_e_exclusao(self):
        adr = Documento.objects.get(fonte=self.fonte, caminho="docs/adr/0001-formato-saida.md")
        secoes_uso = self._ids("docs/uso.md")

        self.repo.escrever("docs/publicacao.md", NOVO)
        self.repo.escrever("docs/uso.md", FERRAMENTA["docs/uso.md"].replace("pytest -q", "pytest -q --maxfail=1"))
        self.repo.mover("docs/adr/0001-formato-saida.md", "docs/decisoes/0001-formato-saida.md")
        self.repo.remover("docs/antigo.md")
        sha2 = self.repo.commit("reorganiza a documentação")
        EmbedderFalso.chamadas = []
        registro = sincronizar(self.fonte)

        self.assertEqual(registro.situacao, FonteGit.SITUACAO_OK)
        self.assertEqual(
            (registro.adicionados, registro.alterados, registro.renomeados, registro.removidos), (1, 1, 1, 1)
        )
        self.assertEqual(self.fonte.ultimo_sha, sha2)

        # Renomeação preserva a identidade do documento e só atualiza o caminho.
        adr.refresh_from_db()
        self.assertEqual(adr.caminho, "docs/decisoes/0001-formato-saida.md")
        self.assertEqual(adr.commit_sha, sha2)

        # Só a seção alterada muda; a seção intacta mantém id e não é vetorizada de novo.
        novas_uso = self._ids("docs/uso.md")
        self.assertEqual(novas_uso["execução"], secoes_uso["execução"])
        self.assertNotEqual(novas_uso["testes"], secoes_uso["testes"])
        self.assertEqual(registro.secoes_vetorizadas, 2)  # seção "Testes" alterada + documento novo
        self.assertEqual(sum(EmbedderFalso.chamadas), 2)

        # Exclusão remove o documento, as seções e as entradas do índice textual.
        self.assertFalse(Documento.objects.filter(fonte=self.fonte, caminho="docs/antigo.md").exists())
        self.assertEqual(indice.buscar("xilofone", [self.fonte.pk]), [])
        self.assertTrue(indice.buscar("maxfail", [self.fonte.pk]))
        self.assertTrue(indice.buscar("release", [self.fonte.pk]))

    def test_repeticao_nao_duplica_registros_nem_revetoriza(self):
        contagem = (Documento.objects.count(), Secao.objects.count(), Embedding.objects.count())

        repeticao = sincronizar(self.fonte)
        self.assertEqual(repeticao.situacao, "sem_mudancas")

        EmbedderFalso.chamadas = []
        forcada = sincronizar(self.fonte, forcar=True)
        self.assertEqual(forcada.situacao, FonteGit.SITUACAO_OK)
        self.assertEqual(forcada.secoes_vetorizadas, 0)
        self.assertGreater(forcada.secoes_reaproveitadas, 0)
        self.assertEqual(EmbedderFalso.chamadas, [])
        self.assertEqual((Documento.objects.count(), Secao.objects.count(), Embedding.objects.count()), contagem)
        self.assertEqual(len(indice.buscar("pipx", [self.fonte.pk])), 1)

    def test_falha_nos_embeddings_mantem_a_versao_anterior_consultavel(self):
        self.repo.escrever("docs/uso.md", FERRAMENTA["docs/uso.md"].replace("pytest -q", "tox -e testes"))
        sha2 = self.repo.commit()

        falha = sincronizar(self.fonte, embedder=EmbedderQuebrado())
        self.assertEqual(falha.situacao, "falha")
        self.assertIn("Ollama indisponível", falha.detalhe)
        self.assertEqual(self.fonte.situacao, FonteGit.SITUACAO_FALHA)
        self.assertEqual(self.fonte.ultimo_sha, self.sha1, "o SHA só avança depois de publicar")
        self.assertEqual(self.fonte.sha_remoto, sha2, "o SHA disponível na branch fica registrado")
        self.assertTrue(indice.buscar("pytest", [self.fonte.pk]), "versão anterior continua consultável")
        self.assertEqual(indice.buscar("tox", [self.fonte.pk]), [])

        recuperada = sincronizar(self.fonte)
        self.assertEqual(recuperada.situacao, FonteGit.SITUACAO_OK)
        self.assertEqual(self.fonte.ultimo_sha, sha2)
        self.assertTrue(indice.buscar("tox", [self.fonte.pk]))

    def test_falha_durante_a_publicacao_desfaz_tudo(self):
        self.repo.escrever("docs/publicacao.md", NOVO)
        self.repo.commit()
        documentos_antes = Documento.objects.count()

        with mock.patch("conhecimento.sincronizacao.reconstruir_relacoes", side_effect=RuntimeError("queda simulada")):
            falha = sincronizar(self.fonte)

        self.assertEqual(falha.situacao, "falha")
        self.assertEqual(Documento.objects.count(), documentos_antes)
        self.assertEqual(self.fonte.ultimo_sha, self.sha1)
        self.assertEqual(indice.buscar("release", [self.fonte.pk]), [])
        self.assertIsNone(self.fonte.sincronizando_desde, "a trava é liberada mesmo na falha")

    def test_trava_impede_duas_sincronizacoes_simultaneas_da_mesma_fonte(self):
        FonteGit.objects.filter(pk=self.fonte.pk).update(sincronizando_desde=timezone.now())
        self.repo.escrever("docs/publicacao.md", NOVO)
        self.repo.commit()

        bloqueada = sincronizar(self.fonte)
        self.assertEqual(bloqueada.situacao, "ja_em_andamento")
        self.assertEqual(self.fonte.ultimo_sha, self.sha1)

        FonteGit.objects.filter(pk=self.fonte.pk).update(sincronizando_desde=timezone.now() - timedelta(hours=1))
        self.assertEqual(sincronizar(self.fonte).situacao, FonteGit.SITUACAO_OK, "trava expirada é retomada")

    def test_historico_reescrito_e_reconciliado_com_a_arvore_atual(self):
        self.repo.escrever("README.md", FERRAMENTA["README.md"].replace("pipx", "uv tool"))
        sha_reescrito = self.repo.reescrever_ultimo_commit("reescreve o primeiro commit")
        # Simula um índice cujo commit anterior não existe mais no espelho.
        FonteGit.objects.filter(pk=self.fonte.pk).update(ultimo_sha="0" * 40)
        self.fonte.refresh_from_db()

        registro = sincronizar(self.fonte)
        self.assertEqual(registro.situacao, FonteGit.SITUACAO_OK)
        self.assertEqual(self.fonte.ultimo_sha, sha_reescrito)
        self.assertEqual(Documento.objects.filter(fonte=self.fonte, caminho="README.md").count(), 1)
        self.assertTrue(indice.buscar("uv tool", [self.fonte.pk]))
        self.assertEqual(indice.buscar("pipx", [self.fonte.pk]), [])

    def test_registro_da_sincronizacao_nao_guarda_conteudo(self):
        registro = Sincronizacao.objects.filter(fonte=self.fonte).first()
        self.assertEqual(registro.sha_novo, self.sha1)
        self.assertNotIn("pipx", registro.detalhe)
