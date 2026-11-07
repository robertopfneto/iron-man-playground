from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from core.models import Agente, Contexto, Projeto, Repositorio


class HealthTests(TestCase):
    def test_health_sem_sessao(self):
        resp = Client().get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})


class ProjetosAcessoTests(TestCase):
    def setUp(self):
        self.projeto = Projeto.objects.create(nome="Projeto de teste")
        self.user = get_user_model().objects.create_user(username="usuario", password="senha-teste-123")

    def test_lista_projetos_exige_sessao(self):
        resp = Client().get("/api/projetos")
        self.assertIn(resp.status_code, (401, 403))

    def test_lista_projetos_com_sessao(self):
        client = Client()
        client.login(username="usuario", password="senha-teste-123")
        resp = client.get("/api/projetos")
        self.assertEqual(resp.status_code, 200)
        nomes = [p["nome"] for p in resp.json()]
        self.assertIn("Projeto de teste", nomes)


class SeedDemoTests(TestCase):
    def test_seed_e_clear_sao_idempotentes_e_isolados(self):
        from django.core.management import call_command

        call_command("seed_demo")
        call_command("seed_demo")
        self.assertEqual(Projeto.objects.filter(nome="Projeto pessoal demonstrativo").count(), 1)

        real = Projeto.objects.create(nome="Projeto real", demo=False)
        call_command("clear_demo")
        self.assertEqual(Projeto.objects.filter(demo=True).count(), 0)
        self.assertTrue(Projeto.objects.filter(pk=real.pk).exists())


class CatalogoEContextoTests(TestCase):
    """Entrega 2: catálogo, vínculos de agente por projeto e contexto escopado."""

    def setUp(self):
        from django.core.management import call_command
        from django.contrib.auth import get_user_model

        call_command("seed_demo")
        self.client_logado = Client()
        self.user = get_user_model().objects.create_user(username="usuario2", password="senha-teste-123")
        self.client_logado.login(username="usuario2", password="senha-teste-123")

        self.projeto_pessoal = Projeto.objects.get(nome="Projeto pessoal demonstrativo")
        self.projeto_educagente = Projeto.objects.get(nome="EducaGente")
        self.hamilton = Agente.objects.get(nome="Hamilton")

    def test_hamilton_atende_dois_projetos_com_contextos_diferentes(self):
        resp1 = self.client_logado.post(
            "/api/contextos",
            data={
                "projeto_id": self.projeto_pessoal.id,
                "agente_id": self.hamilton.id,
                "pedido": "Alterar o comando de instalação.",
            },
            content_type="application/json",
        )
        resp2 = self.client_logado.post(
            "/api/contextos",
            data={
                "projeto_id": self.projeto_educagente.id,
                "agente_id": self.hamilton.id,
                "pedido": "Outro pedido, outro projeto.",
            },
            content_type="application/json",
        )
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)

        c1 = Contexto.objects.get(pk=resp1.json()["id"])
        c2 = Contexto.objects.get(pk=resp2.json()["id"])
        self.assertEqual(c1.projeto_id, self.projeto_pessoal.id)
        self.assertEqual(c2.projeto_id, self.projeto_educagente.id)
        self.assertNotEqual(c1.pedido, c2.pedido)

    def test_backend_impede_referencia_de_repositorio_de_outro_projeto(self):
        repo_outro_projeto = Repositorio.objects.get(projeto=self.projeto_pessoal)

        resp = self.client_logado.post(
            "/api/contextos",
            data={
                "projeto_id": self.projeto_educagente.id,
                "agente_id": self.hamilton.id,
                "pedido": "Tentando referenciar repositório de outro projeto.",
                "referencias_ids": [repo_outro_projeto.id],
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json(), {"detail": "não encontrado"})

    def test_agente_sem_acesso_ao_projeto_nao_cria_contexto(self):
        kohavi = Agente.objects.get(nome="Kohavi")
        resp = self.client_logado.post(
            "/api/contextos",
            data={
                "projeto_id": self.projeto_pessoal.id,
                "agente_id": kohavi.id,
                "pedido": "Kohavi não está autorizado neste projeto.",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_editar_configuracao_de_um_agente_nao_muda_as_demais(self):
        kernighan = Agente.objects.get(nome="Kernighan")
        cfg_kernighan_antes = kernighan.configuracao_modelo.modelo

        resp = self.client_logado.patch(
            f"/api/agentes/{self.hamilton.id}/configuracao",
            data={"modo": "manual", "provedor": "manual", "modelo": "claude-sonnet-5", "habilitado": True},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        self.hamilton.configuracao_modelo.refresh_from_db()
        kernighan.configuracao_modelo.refresh_from_db()
        self.assertEqual(self.hamilton.configuracao_modelo.modelo, "claude-sonnet-5")
        self.assertEqual(kernighan.configuracao_modelo.modelo, cfg_kernighan_antes)

    def test_listar_agentes_do_projeto_retorna_so_os_autorizados(self):
        resp = self.client_logado.get(f"/api/projetos/{self.projeto_pessoal.id}/agentes")
        self.assertEqual(resp.status_code, 200)
        nomes = {a["nome"] for a in resp.json()}
        self.assertEqual(nomes, {"Neto", "Hamilton"})
