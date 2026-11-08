import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from conhecimento.demo.conteudo import CONTA_DEMO, FERRAMENTA_ATUALIZACAO, REPOSITORIOS
from conhecimento.models import FonteGit
from conhecimento.sincronizacao import sincronizar
from core.models import Projeto, Repositorio


def _git(pasta: Path, *args) -> str:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(pasta.parent),
        "GIT_AUTHOR_NAME": "Demo",
        "GIT_AUTHOR_EMAIL": "demo@example.com",
        "GIT_COMMITTER_NAME": "Demo",
        "GIT_COMMITTER_EMAIL": "demo@example.com",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    resultado = subprocess.run(["git", "-C", str(pasta), *args], env=env, check=True, capture_output=True)
    return resultado.stdout.decode().strip()


def _escrever(pasta: Path, caminho: str, texto: str) -> None:
    alvo = pasta / caminho
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(texto, encoding="utf-8")


class Command(BaseCommand):
    help = "Cria repositórios Git fictícios de demonstração, cadastra as fontes e sincroniza."

    def add_arguments(self, parser):
        parser.add_argument("--atualizar", action="store_true", help="Aplica o commit de atualização de Markdown.")
        parser.add_argument("--sem-sincronizar", action="store_true")

    def handle(self, *args, **opcoes):
        raiz = Path(settings.CONHECIMENTO_DIR_FONTES_LOCAIS)
        raiz.mkdir(parents=True, exist_ok=True)

        for nome, nome_projeto, arquivos in REPOSITORIOS:
            projeto = Projeto.objects.filter(nome=nome_projeto).first()
            if projeto is None:
                raise CommandError(f"Projeto '{nome_projeto}' não existe. Rode `python manage.py seed_demo` antes.")
            pasta = raiz / nome
            if not (pasta / ".git").exists():
                pasta.mkdir(parents=True, exist_ok=True)
                _git(pasta, "init", "--quiet", "--initial-branch=main")
                for caminho, texto in arquivos.items():
                    _escrever(pasta, caminho, texto)
                _git(pasta, "add", "-A")
                _git(pasta, "commit", "-q", "-m", "documentação inicial")
                self.stdout.write(f"Repositório demo criado: {nome}")
            repositorio, _ = Repositorio.objects.get_or_create(projeto=projeto, nome=nome, defaults={"demo": True})
            FonteGit.objects.get_or_create(
                repositorio=repositorio,
                defaults={"conta": CONTA_DEMO, "nome_repositorio": nome, "branch": "main", "url": str(pasta)},
            )

        if opcoes["atualizar"]:
            pasta = raiz / "ferramenta-relatorios"
            for de, para in FERRAMENTA_ATUALIZACAO["mover"].items():
                if (pasta / de).exists():
                    (pasta / para).parent.mkdir(parents=True, exist_ok=True)
                    _git(pasta, "mv", de, para)
            for caminho, texto in FERRAMENTA_ATUALIZACAO["escrever"].items():
                _escrever(pasta, caminho, texto)
            _git(pasta, "add", "-A")
            if _git(pasta, "status", "--porcelain"):
                _git(pasta, "commit", "-q", "-m", FERRAMENTA_ATUALIZACAO["mensagem"])
                sha = _git(pasta, "rev-parse", "HEAD")
                self.stdout.write(f"Atualização commitada em ferramenta-relatorios: {sha[:12]}")
            else:
                self.stdout.write("Atualização já aplicada; nada a commitar.")

        if opcoes["sem_sincronizar"]:
            return
        for fonte in FonteGit.objects.filter(conta=CONTA_DEMO).order_by("pk"):
            r = sincronizar(fonte)
            self.stdout.write(
                f"{fonte}: {r.situacao} | {r.sha_anterior[:12] or '-'} -> {r.sha_novo[:12] or '-'} | "
                f"+{r.adicionados} ~{r.alterados} >{r.renomeados} -{r.removidos} | "
                f"vetorizadas {r.secoes_vetorizadas}, reaproveitadas {r.secoes_reaproveitadas}"
                + (f" | {r.detalhe}" if r.detalhe else "")
            )
