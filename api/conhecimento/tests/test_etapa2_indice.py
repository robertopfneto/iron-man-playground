"""Etapa 2: índice por seção, FTS5, vetores e grafo inicial."""

from django.test import SimpleTestCase

from conhecimento import indice
from conhecimento.embeddings import desempacotar, similaridade
from conhecimento.markdown import dividir_em_secoes
from conhecimento.models import Embedding, Relacao, Secao
from conhecimento.sincronizacao import sincronizar
from conhecimento.tests.apoio import FERRAMENTA, BaseConhecimento, vetor_falso


class DivisaoEmSecoesTests(SimpleTestCase):
    def test_divide_por_titulos_e_mantem_bloco_de_codigo_inteiro(self):
        secoes = dividir_em_secoes(FERRAMENTA["README.md"], "README.md")
        instalacao = next(s for s in secoes if s.ancora == "instalação")

        self.assertEqual(instalacao.titulos, ["Ferramenta CLI", "Instalação"])
        self.assertIn("pipx install ferramenta-cli", instalacao.texto)
        # O comentário com "#" dentro do bloco de código não vira título.
        self.assertIn("# depois confira a versão instalada", instalacao.texto)
        self.assertIn("ferramenta --versao", instalacao.texto)
        self.assertEqual(instalacao.linha_inicio, 5)
        self.assertEqual(instalacao.texto.count("```"), 2)

    def test_titulo_sem_conteudo_nao_vira_secao_vazia(self):
        secoes = dividir_em_secoes("# Projeto\n\n## Parte A\n\nTexto da parte A com conteúdo suficiente.\n", "x.md")
        self.assertEqual([s.titulos for s in secoes], [["Projeto", "Parte A"]])

    def test_ancoras_repetidas_recebem_sufixo(self):
        texto = "# Doc\n\n## Uso\n\nprimeiro\n\n## Uso\n\nsegundo\n"
        self.assertEqual([s.ancora for s in dividir_em_secoes(texto, "x.md")], ["uso", "uso-1"])


class IndiceEGrafoTests(BaseConhecimento):
    def setUp(self):
        super().setUp()
        self.fonte, self.repo = self.criar_fonte("ferramenta-cli", FERRAMENTA)
        sincronizar(self.fonte)

    def _secao(self, caminho, ancora):
        return Secao.objects.get(documento__fonte=self.fonte, documento__caminho=caminho, ancora=ancora)

    def test_secao_guarda_texto_caminho_hierarquia_linhas_commit_e_hash(self):
        s = self._secao("README.md", "instalação")
        self.assertEqual(s.titulos, ["Ferramenta CLI", "Instalação"])
        self.assertEqual(s.commit_sha, self.fonte.ultimo_sha)
        self.assertEqual((s.linha_inicio, s.linha_fim), (5, 14))
        self.assertEqual(len(s.hash_conteudo), 64)

    def test_consulta_pelo_nome_do_comando_encontra_a_secao_exata(self):
        resultados = indice.buscar("pipx install", [self.fonte.pk])
        self.assertEqual(resultados[0][0], self._secao("README.md", "instalação").pk)

        resultados = indice.buscar("pytest", [self.fonte.pk])
        self.assertEqual(resultados[0][0], self._secao("docs/uso.md", "testes").pk)

    def test_consulta_textual_ignora_acentos(self):
        resultados = indice.buscar("execucao", [self.fonte.pk])
        self.assertIn(self._secao("docs/uso.md", "execução").pk, [r[0] for r in resultados])

    def test_consulta_semantica_encontra_a_mesma_secao_com_outras_palavras(self):
        pergunta = "como preparar o setup na minha máquina"
        consulta = vetor_falso(pergunta)
        melhor = max(
            Secao.objects.filter(documento__fonte=self.fonte),
            key=lambda s: similaridade(
                consulta, desempacotar(Embedding.objects.get(hash_conteudo=s.hash_conteudo, modelo="falso-v1").vetor)
            ),
        )
        self.assertEqual(melhor.pk, self._secao("README.md", "instalação").pk)
        # A mesma pergunta não tem nenhum termo em comum com o comando da seção.
        self.assertNotIn(self._secao("README.md", "instalação").pk, [r[0] for r in indice.buscar(pergunta, [self.fonte.pk])])

    def test_modelo_de_embedding_fica_registrado(self):
        self.assertTrue(Embedding.objects.filter(modelo="falso-v1").exists())
        self.assertEqual(Embedding.objects.first().dimensao, 16)

    def test_link_interno_resolvido_vira_relacao_com_o_trecho(self):
        origem = self._secao("README.md", "uso")
        relacoes = {r.destino_documento.caminho: r for r in Relacao.objects.filter(origem=origem)}

        para_uso = relacoes["docs/uso.md"]
        self.assertEqual(para_uso.tipo, Relacao.TIPO_REFERENCIA)
        self.assertEqual(para_uso.destino_secao, self._secao("docs/uso.md", "execução"))
        self.assertIn("[guia de uso](docs/uso.md#execução)", para_uso.trecho)

        para_adr = relacoes["docs/adr/0001-formato-saida.md"]
        self.assertIsNone(para_adr.destino_secao)

    def test_link_para_arquivo_fora_do_indice_nao_vira_relacao(self):
        self.repo.escrever(
            "docs/extra.md",
            "# Extra\n\nVeja [a dependência](../node_modules/pacote/README.md) e [um arquivo inexistente](nao-existe.md) "
            "antes de alterar o formato de saída do relatório.\n",
        )
        self.repo.commit()
        sincronizar(self.fonte)
        extra = Secao.objects.get(documento__caminho="docs/extra.md")
        self.assertFalse(Relacao.objects.filter(origem=extra).exists())
