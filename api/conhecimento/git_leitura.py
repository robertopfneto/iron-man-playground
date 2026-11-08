"""Leitura somente leitura do Git para a ingestão.

Usa um espelho bare por fonte e só comandos de leitura (fetch, rev-parse,
ls-tree, cat-file, diff-tree). Não faz checkout, não executa hooks nem código do
repositório. O token de leitura vai por variáveis de ambiente do Git, nunca na
linha de comando, em log ou no banco.
"""

import base64
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

TIMEOUT_GIT = 120
LIMITE_BLOB_BYTES = 512 * 1024
_URL_GITHUB = re.compile(r"^https://github\.com/(?P<conta>[A-Za-z0-9-]+)/(?P<repo>[A-Za-z0-9._-]+?)(?:\.git)?$")
_SHA = re.compile(r"^[0-9a-f]{40}$")


class ErroGit(Exception):
    """Falha de leitura Git. A mensagem não inclui token nem saída bruta do remoto."""


@dataclass(frozen=True)
class EntradaArvore:
    caminho: str
    blob_sha: str
    modo: str
    tamanho: int


def _dir_espelhos() -> Path:
    pasta = Path(settings.CONHECIMENTO_DIR_ESPELHOS)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def espelho_da_fonte(fonte) -> Path:
    return _dir_espelhos() / f"fonte-{fonte.pk}.git"


def validar_origem(fonte) -> tuple[str, str]:
    """Retorna (url, tipo). Só aceita o GitHub da conta cadastrada ou um repo demo local autorizado."""
    url = fonte.url.strip()
    casamento = _URL_GITHUB.match(url)
    if casamento:
        if (
            casamento.group("conta").lower() != fonte.conta.lower()
            or casamento.group("repo").lower() != fonte.nome_repositorio.lower()
        ):
            raise ErroGit("A URL não corresponde à conta e ao repositório cadastrados.")
        return url, "github"

    raiz_local = getattr(settings, "CONHECIMENTO_DIR_FONTES_LOCAIS", "")
    if raiz_local:
        raiz = Path(raiz_local).resolve()
        caminho = Path(url).resolve()
        if caminho.is_relative_to(raiz) and caminho.exists():
            return str(caminho), "local"
    raise ErroGit("Origem não autorizada para ingestão.")


def _ambiente(tipo: str) -> dict:
    casa = tempfile.mkdtemp(prefix="git-home-")
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": casa,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ALLOW_PROTOCOL": "file" if tipo == "local" else "https",
        "LC_ALL": "C",
    }
    token = os.environ.get("GITHUB_TOKEN_LEITURA", "")
    if tipo == "github" and token:
        credencial = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env.update(
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
                "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {credencial}",
            }
        )
    return env


def _git(espelho: Path | None, args: list[str], tipo: str = "local", binario: bool = False):
    comando = ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false"]
    if espelho is not None:
        comando += ["--git-dir", str(espelho)]
    comando += args
    try:
        resultado = subprocess.run(
            comando,
            env=_ambiente(tipo),
            capture_output=True,
            timeout=TIMEOUT_GIT,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ErroGit(f"git {args[0]} excedeu {TIMEOUT_GIT}s.") from exc
    if resultado.returncode != 0:
        raise ErroGit(f"git {args[0]} falhou (código {resultado.returncode}).")
    return resultado.stdout if binario else resultado.stdout.decode("utf-8", errors="replace")


def atualizar_espelho(fonte) -> str:
    """Faz fetch da branch monitorada e devolve o SHA atual dela."""
    url, tipo = validar_origem(fonte)
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", fonte.branch) or ".." in fonte.branch:
        raise ErroGit("Nome de branch inválido.")
    espelho = espelho_da_fonte(fonte)
    if not (espelho / "HEAD").exists():
        _git(None, ["init", "--bare", "--quiet", str(espelho)])
    ref_local = f"refs/remotes/origem/{fonte.branch}"
    _git(espelho, ["fetch", "--quiet", "--no-tags", "--force", url, f"+refs/heads/{fonte.branch}:{ref_local}"], tipo)
    sha = _git(espelho, ["rev-parse", "--verify", f"{ref_local}^{{commit}}"]).strip()
    if not _SHA.match(sha):
        raise ErroGit("SHA inválido retornado pelo Git.")
    return sha


def commit_existe(espelho: Path, sha: str) -> bool:
    if not sha or not _SHA.match(sha):
        return False
    try:
        _git(espelho, ["cat-file", "-e", f"{sha}^{{commit}}"])
        return True
    except ErroGit:
        return False


def listar_arvore(espelho: Path, sha: str) -> list[EntradaArvore]:
    saida = _git(espelho, ["ls-tree", "-r", "-l", "-z", "--full-tree", sha])
    entradas = []
    for registro in saida.split("\0"):
        if not registro:
            continue
        meta, caminho = registro.split("\t", 1)
        modo, tipo, objeto, tamanho = meta.split()
        if tipo != "blob":
            continue  # submódulos (commit) e árvores ficam de fora
        entradas.append(EntradaArvore(caminho, objeto, modo, int(tamanho) if tamanho != "-" else 0))
    return entradas


def ler_blob(espelho: Path, blob_sha: str) -> str:
    dados = _git(espelho, ["cat-file", "blob", blob_sha], binario=True)
    if len(dados) > LIMITE_BLOB_BYTES:
        raise ErroGit("Arquivo acima do limite.")
    return dados.decode("utf-8", errors="replace")


def renomeacoes(espelho: Path, sha_antigo: str, sha_novo: str) -> dict[str, str]:
    """Mapa caminho_antigo -> caminho_novo identificado pelo Git entre os dois commits."""
    if not commit_existe(espelho, sha_antigo):
        return {}
    saida = _git(espelho, ["diff-tree", "-r", "-z", "-M", "--name-status", "--no-commit-id", sha_antigo, sha_novo])
    partes = [p for p in saida.split("\0") if p]
    mapa, i = {}, 0
    while i < len(partes):
        status = partes[i]
        if status.startswith(("R", "C")):
            if status.startswith("R"):
                mapa[partes[i + 1]] = partes[i + 2]
            i += 3
        else:
            i += 2
    return mapa
