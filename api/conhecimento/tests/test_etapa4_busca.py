"""Etapa 4: busca híbrida para Neto e os especialistas, com isolamento entre projetos."""

import json

from django.contrib.auth import get_user_model
from django.test import Client

from conhecimento.busca import buscar, consulta_de_diff, link_para_commit
from conhecimento.models import Relacao, Secao
from conhecimento.sincronizacao import sincronizar
from conhecimento.tests.apoio import FERRAMENTA, BaseConhecimento, EmbedderQuebrado
from core.models import AcessoAgente, Agente, Conversa, Mensagem, Projeto

SEGREDO = {
    "PROTOCOLO.md": """# Protocolo confidencial do laboratório

## Coleta

O protocolo zircônio define a coleta das imagens de campo e a nomenclatura dos lotes do laboratório.
Somente membros do projeto de visão computacional podem consultar este protocolo de coleta.
""",
}

DIFF_CLI = """--- a/src/ferramenta/cli.py
+++ b/src/ferramenta/cli.py
@@ -10,3 +10,4 @@
-    parser.add_argument("--saida", default="relatorio.json")
+    parser.add_argument("--saida", default="relatorio.csv")
+    parser.add_argument("--formato", choices=["json", "csv"])
"""


class BuscaHibridaTests(BaseConhecimento):
    def setUp(self):
        super().setUp()
        self.neto = Agente.objects.create(nome="Neto")
        self.kernighan = Agente.objects.create(nome="Kernighan")
        self.pistori = Agente.objects.create(nome="Pistori")
        for agente in (self.neto, self.kernighan):
            AcessoAgente.objects.create(projeto=self.projeto, agente=agente)
        self.fonte, self.repo = self.criar_fonte("ferramenta-cli", FERRAMENTA)
        sincronizar(self.fonte)

        self.outro = Projeto.objects.create(nome="Laboratório de teste", cenario="Catálogo")
        for agente in (self.neto, self.pistori):
            AcessoAgente.objects.create(projeto=self.outro, agente=agente)
        self.fonte_outra, _ = self.criar_fonte("protocolos-lab", SEGREDO, projeto=self.outro)
        sincronizar(self.fonte_outra)

        self.client_logado = Client()
        get_user_model().objects.create_user(username="kb", password="senha-teste-123")
        self.client_logado.login(username="kb", password="senha-teste-123")

    def _buscar(self, pergunta, **kw):
        return buscar(self.projeto.pk, self.neto.pk, pergunta, **kw)

    # ------------------------------------------------------------ resultados e referências

    def test_retorna_poucos_trechos_com_referencias_verificaveis(self):
        r = self._buscar("como instalar a ferramenta com pipx?")
        self.assertFalse(r.sem_evidencia)
        self.assertLessEqual(len(r.trechos), 4)
        t = r.trechos[0]
        self.assertEqual((t.repositorio, t.caminho), ("robertopfneto/ferramenta-cli", "README.md"))
        self.assertEqual(t.secao, "Ferramenta CLI > Instalação")
        self.assertEqual(t.commit, self.fonte.ultimo_sha)
        self.assertEqual(
            t.link, f"local:robertopfneto/ferramenta-cli/blob/{self.fonte.ultimo_sha}/README.md#L5-L14"
        )
        self.fonte.url = "https://github.com/robertopfneto/ferramenta-cli.git"
        self.assertEqual(
            link_para_commit(self.fonte, "README.md", "abc", 5, 14),
            "https://github.com/robertopfneto/ferramenta-cli/blob/abc/README.md#L5-L14",
        )
        self.assertEqual(len({x.secao_id for x in r.trechos}), len(r.trechos), "sem duplicatas")

    def test_orcamento_de_contexto_e_respeitado(self):
        r = self._buscar("ferramenta relatório json csv pytest pipx", orcamento=300, max_trechos=2)
        self.assertLessEqual(r.caracteres_contexto, 300)
        self.assertLessEqual(len(r.trechos), 2)
        self.assertEqual(r.caracteres_contexto, sum(len(t.texto) for t in r.trechos))

    def test_hibrida_encontra_com_outras_palavras_e_textual_nao(self):
        pergunta = "como preparar o setup na minha máquina"
        textual = self._buscar(pergunta, modo="textual")
        hibrida = self._buscar(pergunta, modo="hibrida")
        self.assertNotIn("Ferramenta CLI > Instalação", [t.secao for t in textual.trechos])
        self.assertEqual(hibrida.trechos[0].secao, "Ferramenta CLI > Instalação")
        self.assertEqual(hibrida.trechos[0].origem, "vetorial")

    def test_grafo_inclui_documentacao_relacionada_por_um_salto(self):
        sem_grafo = self._buscar("veja", modo="hibrida")
        com_grafo = self._buscar("veja", modo="hibrida_grafo")

        self.assertEqual([t.caminho for t in sem_grafo.trechos], ["README.md"])
        relacionados = {t.caminho: t for t in com_grafo.trechos if t.origem == "relacao"}
        self.assertIn("docs/uso.md", relacionados)
        self.assertEqual(relacionados["docs/uso.md"].secao, "Guia de uso > Execução")
        self.assertIn("[guia de uso](docs/uso.md#execução)", relacionados["docs/uso.md"].via)

    def test_falta_de_evidencia_e_informada(self):
        r = self._buscar("qual o roteiro do kubernetes com helm chart")
        self.assertTrue(r.sem_evidencia)
        self.assertEqual(r.trechos, [])
        self.assertIn("Não encontrei evidência autorizada para essa pergunta.", r.avisos)

    def test_indice_atrasado_indica_o_sha_disponivel(self):
        self.repo.escrever("docs/uso.md", FERRAMENTA["docs/uso.md"] + "\n## Novo\n\nSeção nova ainda não indexada.\n")
        sha_novo = self.repo.commit()
        sincronizar(self.fonte, embedder=EmbedderQuebrado())

        r = self._buscar("pipx")
        self.assertEqual(r.trechos[0].commit, self.fonte.ultimo_sha)
        fonte_info = r.fontes[0]
        self.assertTrue(fonte_info["atrasada"])
        self.assertEqual(fonte_info["sha_remoto"], sha_novo)
        self.assertTrue(any(self.fonte.ultimo_sha[:12] in a and sha_novo[:12] in a for a in r.avisos))

    def test_busca_vetorial_indisponivel_cai_para_texto_com_aviso(self):
        r = self._buscar("pipx", embedder=EmbedderQuebrado())
        self.assertEqual(r.trechos[0].secao, "Ferramenta CLI > Instalação")
        self.assertIn("Busca vetorial indisponível agora; usei só a busca textual.", r.avisos)

    # ------------------------------------------------------------ isolamento

    def test_pergunta_nao_amplia_escopo_para_outro_projeto(self):
        r = self._buscar("protocolo zircônio do laboratório protocolos-lab PROTOCOLO.md coleta")
        corpo = json.dumps(r.como_dict(), ensure_ascii=False)
        self.assertNotIn("zircônio", corpo)
        self.assertNotIn("Protocolo confidencial", corpo)
        self.assertNotIn("protocolos-lab", corpo)

    def test_relacao_para_outro_projeto_nao_e_criada_nem_seguida(self):
        self.repo.escrever(
            "docs/lab.md",
            "# Lab\n\nO procedimento de coleta segue o [protocolo](https://github.com/robertopfneto/protocolos-lab/blob/main/PROTOCOLO.md) "
            "definido pelo laboratório parceiro para os lotes do experimento.\n",
        )
        self.repo.commit()
        sincronizar(self.fonte)
        origem = Secao.objects.get(documento__fonte=self.fonte, documento__caminho="docs/lab.md")
        self.assertFalse(Relacao.objects.filter(origem=origem).exists(), "link para outro projeto não vira aresta")

        # Mesmo uma aresta indevida no banco é filtrada ao seguir relações.
        destino = Secao.objects.get(documento__fonte=self.fonte_outra)
        Relacao.objects.create(
            origem=origem, destino_documento=destino.documento, destino_secao=destino, trecho="aresta indevida"
        )
        r = self._buscar("procedimento de coleta dos lotes", modo="hibrida_grafo")
        self.assertIn("docs/lab.md", [t.caminho for t in r.trechos])
        self.assertNotIn(destino.pk, [t.secao_id for t in r.trechos])
        self.assertNotIn("zircônio", json.dumps(r.como_dict(), ensure_ascii=False))

    def test_agente_sem_acesso_recebe_negativa_generica_sem_confirmar_existencia(self):
        url = "/api/conhecimento/busca"
        sem_acesso = self.client_logado.get(
            url, {"projeto_id": self.projeto.pk, "agente_id": self.pistori.pk, "pergunta": "pipx"}
        )
        inexistente = self.client_logado.get(url, {"projeto_id": 999999, "agente_id": self.neto.pk, "pergunta": "pipx"})
        self.assertEqual(sem_acesso.status_code, 404)
        self.assertEqual(sem_acesso.json(), inexistente.json())
        self.assertEqual(inexistente.status_code, 404)

    def test_api_exige_sessao(self):
        r = Client().get(
            "/api/conhecimento/busca", {"projeto_id": self.projeto.pk, "agente_id": self.neto.pk, "pergunta": "x"}
        )
        self.assertIn(r.status_code, (401, 403))

    def test_api_de_busca_no_escopo_retorna_trechos(self):
        r = self.client_logado.get(
            "/api/conhecimento/busca",
            {"projeto_id": self.projeto.pk, "agente_id": self.neto.pk, "pergunta": "pytest", "modo": "textual"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["trechos"][0]["caminho"], "docs/uso.md")

    # ------------------------------------------------------------ Neto e Kernighan

    def test_neto_responde_pergunta_citando_a_versao_consultada(self):
        conversa = Conversa.objects.create(projeto=self.projeto)
        r = self.client_logado.post(
            f"/api/conversas/{conversa.pk}/mensagens",
            data={"conteudo": "Como instalo a ferramenta?"},
            content_type="application/json",
        ).json()

        self.assertEqual(r["tipo"], "resposta_documentada")
        self.assertIn(self.fonte.ultimo_sha[:12], r["resposta"])
        self.assertIn("robertopfneto/ferramenta-cli/README.md", r["resposta"])
        self.assertEqual(r["evidencias"][0]["caminho"], "README.md")
        self.assertIn("pipx install", r["prompt_copiavel"])
        resposta_salva = Mensagem.objects.filter(conversa=conversa, autor=Mensagem.AUTOR_NETO).get()
        self.assertIn(self.fonte.ultimo_sha[:12], resposta_salva.conteudo)

    def test_neto_informa_quando_falta_evidencia(self):
        conversa = Conversa.objects.create(projeto=self.projeto)
        r = self.client_logado.post(
            f"/api/conversas/{conversa.pk}/mensagens",
            data={"conteudo": "Como configuro o kubernetes com helm?"},
            content_type="application/json",
        ).json()
        self.assertEqual(r["tipo"], "sem_evidencia")
        self.assertIn("Não encontrei evidência autorizada", r["resposta"])

    def test_kernighan_localiza_guias_afetados_por_um_diff(self):
        self.assertIn("formato", consulta_de_diff(DIFF_CLI))
        r = self.client_logado.post(
            "/api/conhecimento/guias-afetados",
            data={"projeto_id": self.projeto.pk, "diff": DIFF_CLI},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        caminhos = {t["caminho"] for t in r.json()["trechos"]}
        self.assertIn("docs/uso.md", caminhos)
        self.assertIn("docs/adr/0001-formato-saida.md", caminhos)

        fora = self.client_logado.post(
            "/api/conhecimento/guias-afetados",
            data={"projeto_id": self.outro.pk, "diff": DIFF_CLI},
            content_type="application/json",
        )
        self.assertEqual(fora.status_code, 404)

    def test_fonte_restrita_sai_da_busca_quando_autorizacao_e_revogada(self):
        before = Projeto.objects.create(nome="Before", cenario="Before")
        AcessoAgente.objects.create(projeto=before, agente=self.neto)
        fonte, _ = self.criar_fonte("repo-before", FERRAMENTA, projeto=before, autorizacao_explicita=True)
        sincronizar(fonte)
        self.assertFalse(buscar(before.pk, self.neto.pk, "pipx").sem_evidencia)

        fonte.autorizacao_explicita = False
        fonte.save()
        r = buscar(before.pk, self.neto.pk, "pipx")
        self.assertTrue(r.sem_evidencia)
        self.assertEqual(r.fontes, [])
