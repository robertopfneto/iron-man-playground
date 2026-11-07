from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from core.models import Projeto


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
        self.assertEqual(Projeto.objects.filter(demo=True).count(), 1)

        real = Projeto.objects.create(nome="Projeto real", demo=False)
        call_command("clear_demo")
        self.assertEqual(Projeto.objects.filter(demo=True).count(), 0)
        self.assertTrue(Projeto.objects.filter(pk=real.pk).exists())
