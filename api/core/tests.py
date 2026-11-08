from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from core.models import Agente, Contexto, Decisao, Projeto, Repositorio, Turno


class HealthTests(TestCase):
    def test_health_sem_sessao(self):
        resp = Client().get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})


class AuthSpaTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="spa", password="senha-teste-123")

    def test_sessao_anonima_define_cookie_csrf(self):
        client = Client()
        resp = client.get("/api/auth/sessao")
        self.assertEqual(
            resp.json(), {"autenticado": False, "usuario": None, "precisa_cadastro": False}
        )
        self.assertIn("csrftoken", resp.cookies)

    def test_primeiro_acesso_fechado_quando_ja_existe_usuario(self):
        resp = Client().post(
            "/api/auth/primeiro-acesso",
            data={"usuario": "intruso", "senha": "Outra-senha-forte-1"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(get_user_model().objects.filter(username="intruso").exists())


class PrimeiroAcessoTests(TestCase):
    def test_primeiro_acesso_cria_admin_e_fecha_cadastro(self):
        client = Client()
        self.assertTrue(client.get("/api/auth/sessao").json()["precisa_cadastro"])

        fraca = client.post(
            "/api/auth/primeiro-acesso",
            data={"usuario": "roberto", "senha": "123"},
            content_type="application/json",
        )
        self.assertEqual(fraca.status_code, 400)

        ok = client.post(
            "/api/auth/primeiro-acesso",
            data={"usuario": "roberto", "senha": "Senha-forte-escritorio-1"},
            content_type="application/json",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(get_user_model().objects.get(username="roberto").is_superuser)
        self.assertEqual(client.get("/api/projetos").status_code, 200)

        segunda = Client().post(
            "/api/auth/primeiro-acesso",
            data={"usuario": "outro", "senha": "Senha-forte-escritorio-2"},
            content_type="application/json",
        )
        self.assertEqual(segunda.status_code, 403)


class LoginSpaTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="spa", password="senha-teste-123")

    def test_login_com_csrf_e_logout(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/api/auth/sessao")
        token = client.cookies["csrftoken"].value

        ruim = client.post(
            "/api/auth/login",
            data={"usuario": "spa", "senha": "errada"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(ruim.status_code, 401)

        ok = client.post(
            "/api/auth/login",
            data={"usuario": "spa", "senha": "senha-teste-123"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(client.get("/api/projetos").status_code, 200)

        token = client.cookies["csrftoken"].value
        saiu = client.post("/api/auth/logout", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(saiu.status_code, 200)
        self.assertIn(client.get("/api/projetos").status_code, (401, 403))


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

        Agente.objects.filter(nome="Pistori").update(homenagem="")
        call_command("seed_demo")
        self.assertEqual(Agente.objects.get(nome="Pistori").homenagem, "Hemerson Pistori")

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


class ChatDelegacaoTests(TestCase):
    """Entrega 3: triagem, convocação, turnos e decisão aprovada/recuperada."""

    def setUp(self):
        from django.core.management import call_command

        call_command("seed_demo")
        self.client_logado = Client()
        get_user_model().objects.create_user(username="usuario3", password="senha-teste-123")
        self.client_logado.login(username="usuario3", password="senha-teste-123")
        self.projeto = Projeto.objects.get(nome="Projeto pessoal demonstrativo")

    def _nova_conversa(self):
        resp = self.client_logado.post(
            "/api/conversas", data={"projeto_id": self.projeto.id}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        return resp.json()["id"]

    def test_duvida_simples_encerra_sem_convocacao(self):
        conversa_id = self._nova_conversa()
        resp = self.client_logado.post(
            f"/api/conversas/{conversa_id}/mensagens",
            data={"conteudo": "Oi Neto, só testando."},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["tipo"], "duvida_simples")

    def test_pedido_de_mudanca_gera_convocacao_hamilton_e_kernighan(self):
        from core.models import Agente

        conversa_id = self._nova_conversa()
        resp = self.client_logado.post(
            f"/api/conversas/{conversa_id}/mensagens",
            data={"conteudo": "Preciso alterar o comando de instalação deste projeto pessoal."},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        corpo = resp.json()
        self.assertEqual(corpo["tipo"], "proposta_convocacao")

        hamilton = Agente.objects.get(nome="Hamilton")
        self.assertIn(hamilton.id, corpo["agentes_sugeridos"])
        # Kernighan não está autorizado no "Projeto pessoal demonstrativo" no seed,
        # então a sugestão respeita o escopo e não o inclui.
        kernighan = Agente.objects.get(nome="Kernighan")
        self.assertNotIn(kernighan.id, corpo["agentes_sugeridos"])

        resp_confirma = self.client_logado.post(
            f"/api/convocacoes/{corpo['convocacao_id']}/confirmar",
            data={"agentes_ids": [hamilton.id]},
            content_type="application/json",
        )
        self.assertEqual(resp_confirma.status_code, 200)
        turno_id = resp_confirma.json()["turnos"][0]

        resp_resultado = self.client_logado.post(
            f"/api/turnos/{turno_id}/resultado",
            data={"resultado": "Proposta de novo comando de instalação.", "autoria": "usuario3"},
            content_type="application/json",
        )
        self.assertEqual(resp_resultado.status_code, 200)

        convocacao = self.client_logado.get(f"/api/convocacoes/{corpo['convocacao_id']}").json()
        self.assertEqual(convocacao["situacao"], "concluida")

        decisao = Decisao.objects.get(convocacao_id=corpo["convocacao_id"])
        self.assertEqual(decisao.situacao, Decisao.SITUACAO_PROPOSTA)

        resp_aprova = self.client_logado.post(f"/api/decisoes/{decisao.id}/aprovar")
        self.assertEqual(resp_aprova.status_code, 200)
        decisao.refresh_from_db()
        self.assertEqual(decisao.situacao, Decisao.SITUACAO_APROVADA)

    def test_pedido_geral_nao_sugere_convocar_neto(self):
        conversa_id = self._nova_conversa()
        resp = self.client_logado.post(
            f"/api/conversas/{conversa_id}/mensagens",
            data={"conteudo": "Quero comparar duas abordagens de avaliação e saber se a diferença entre elas é real."},
            content_type="application/json",
        ).json()
        self.assertEqual(resp["tipo"], "proposta_convocacao")
        neto = Agente.objects.get(nome="Neto")
        self.assertNotIn(neto.id, resp["agentes_sugeridos"])
        self.assertIn(Agente.objects.get(nome="Hamilton").id, resp["agentes_sugeridos"])

    def test_confirmacao_repetida_nao_duplica_turnos(self):
        from core.models import Agente

        conversa_id = self._nova_conversa()
        resp = self.client_logado.post(
            f"/api/conversas/{conversa_id}/mensagens",
            data={"conteudo": "Preciso alterar o comando de instalação deste projeto."},
            content_type="application/json",
        )
        convocacao_id = resp.json()["convocacao_id"]
        hamilton = Agente.objects.get(nome="Hamilton")

        primeira = self.client_logado.post(
            f"/api/convocacoes/{convocacao_id}/confirmar",
            data={"agentes_ids": [hamilton.id]},
            content_type="application/json",
        )
        segunda = self.client_logado.post(
            f"/api/convocacoes/{convocacao_id}/confirmar",
            data={"agentes_ids": [hamilton.id]},
            content_type="application/json",
        )
        self.assertEqual(primeira.json()["turnos"], segunda.json()["turnos"])
        self.assertEqual(Turno.objects.filter(convocacao_id=convocacao_id).count(), 1)

    def test_convocacoes_abertas_sobrevivem_a_nova_conversa(self):
        conversa_id = self._nova_conversa()
        proposta = self.client_logado.post(
            f"/api/conversas/{conversa_id}/mensagens",
            data={"conteudo": "Preciso alterar o comando de instalação deste projeto."},
            content_type="application/json",
        ).json()
        hamilton = Agente.objects.get(nome="Hamilton")
        self.client_logado.post(
            f"/api/convocacoes/{proposta['convocacao_id']}/confirmar",
            data={"agentes_ids": [hamilton.id]},
            content_type="application/json",
        )
        self._nova_conversa()  # recarregar a página abre outra conversa

        abertas = self.client_logado.get(f"/api/projetos/{self.projeto.id}/convocacoes-abertas").json()
        self.assertEqual([c["id"] for c in abertas], [proposta["convocacao_id"]])
        self.assertEqual(abertas[0]["turnos"][0]["agente"], "Hamilton")
        self.assertEqual(abertas[0]["turnos"][0]["situacao"], "convocado")

        turno_id = abertas[0]["turnos"][0]["id"]
        self.client_logado.post(
            f"/api/turnos/{turno_id}/resultado",
            data={"resultado": "Feito.", "autoria": "usuario3"},
            content_type="application/json",
        )
        self.assertEqual(self.client_logado.get(f"/api/projetos/{self.projeto.id}/convocacoes-abertas").json(), [])

    def test_decisao_aprovada_e_recuperada_em_outra_conversa_no_mesmo_projeto(self):
        Decisao.objects.create(
            projeto=self.projeto,
            texto="Use docker compose up --build -d --wait para instalar.",
            situacao=Decisao.SITUACAO_APROVADA,
        )
        conversa_id = self._nova_conversa()
        resp = self.client_logado.post(
            f"/api/conversas/{conversa_id}/mensagens",
            data={"conteudo": "Qual foi a decisão sobre o comando compose de instalação?"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["tipo"], "resposta_direta")

    def test_resultado_de_turno_concluido_e_idempotente(self):
        from core.models import Agente

        conversa_id = self._nova_conversa()
        resp = self.client_logado.post(
            f"/api/conversas/{conversa_id}/mensagens",
            data={"conteudo": "Preciso alterar o comando de instalação aqui."},
            content_type="application/json",
        )
        convocacao_id = resp.json()["convocacao_id"]
        hamilton = Agente.objects.get(nome="Hamilton")
        turno_id = self.client_logado.post(
            f"/api/convocacoes/{convocacao_id}/confirmar",
            data={"agentes_ids": [hamilton.id]},
            content_type="application/json",
        ).json()["turnos"][0]

        self.client_logado.post(
            f"/api/turnos/{turno_id}/resultado",
            data={"resultado": "Primeira versão.", "autoria": "usuario3"},
            content_type="application/json",
        )
        self.client_logado.post(
            f"/api/turnos/{turno_id}/resultado",
            data={"resultado": "Tentativa de sobrescrever.", "autoria": "usuario3"},
            content_type="application/json",
        )
        turno = Turno.objects.get(pk=turno_id)
        self.assertEqual(turno.resultado, "Primeira versão.")
        self.assertEqual(Decisao.objects.filter(convocacao_id=convocacao_id).count(), 1)


class SalaTests(TestCase):
    """Entrega 4: estado visual dos avatares a partir dos turnos reais."""

    def setUp(self):
        from django.core.management import call_command

        call_command("seed_demo")
        self.client_logado = Client()
        get_user_model().objects.create_user(username="usuario4", password="senha-teste-123")
        self.client_logado.login(username="usuario4", password="senha-teste-123")
        self.projeto = Projeto.objects.get(nome="Projeto pessoal demonstrativo")

    def test_avatares_comecam_disponiveis_e_template_tem_fallback(self):
        resp = self.client_logado.get(f"/api/projetos/{self.projeto.id}/sala")
        self.assertEqual(resp.status_code, 200)
        corpo = resp.json()
        self.assertEqual(corpo["template_id"], "recepcao_padrao")
        estados = {a["nome"]: a["estado"] for a in corpo["avatares"]}
        self.assertEqual(estados, {"Neto": "disponivel", "Hamilton": "disponivel"})

    def test_template_id_invalido_ainda_cai_no_fallback_quando_vazio(self):
        resp = self.client_logado.get(f"/api/projetos/{self.projeto.id}/sala?template_id=")
        self.assertEqual(resp.json()["template_id"], "recepcao_padrao")

    def test_avatar_reflete_turno_convocado_e_depois_concluido(self):
        from core.models import Agente

        hamilton = Agente.objects.get(nome="Hamilton")
        conversa = self.client_logado.post(
            "/api/conversas", data={"projeto_id": self.projeto.id}, content_type="application/json"
        ).json()
        proposta = self.client_logado.post(
            f"/api/conversas/{conversa['id']}/mensagens",
            data={"conteudo": "Preciso alterar o comando de instalação aqui."},
            content_type="application/json",
        ).json()
        confirmada = self.client_logado.post(
            f"/api/convocacoes/{proposta['convocacao_id']}/confirmar",
            data={"agentes_ids": [hamilton.id]},
            content_type="application/json",
        ).json()

        resp_convocado = self.client_logado.get(f"/api/projetos/{self.projeto.id}/sala")
        estados = {a["nome"]: a["estado"] for a in resp_convocado.json()["avatares"]}
        self.assertEqual(estados["Hamilton"], "convocado")

        turno_id = confirmada["turnos"][0]
        self.client_logado.post(
            f"/api/turnos/{turno_id}/resultado",
            data={"resultado": "Concluído.", "autoria": "usuario4"},
            content_type="application/json",
        )
        resp_concluido = self.client_logado.get(f"/api/projetos/{self.projeto.id}/sala")
        estados2 = {a["nome"]: a["estado"] for a in resp_concluido.json()["avatares"]}
        self.assertEqual(estados2["Hamilton"], "concluido")
