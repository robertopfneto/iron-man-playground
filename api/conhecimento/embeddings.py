"""Embeddings locais via Ollama e armazenamento simples em float32.

O endpoint do Ollama fica do lado do plano de controle (rede interna do Compose,
acessível só pela API). Nenhum provedor externo é chamado.
"""

import array
import json
import math
import urllib.error
import urllib.request

from django.conf import settings
from django.utils.module_loading import import_string

TAMANHO_LOTE = 16


class EmbeddingsIndisponiveis(Exception):
    pass


class OllamaEmbedder:
    def __init__(self, url: str | None = None, modelo: str | None = None, timeout: int = 120):
        self.url = (url or settings.OLLAMA_URL).rstrip("/")
        self.modelo = modelo or settings.EMBEDDINGS_MODELO
        self.timeout = timeout

    def vetorizar(self, textos: list[str]) -> list[list[float]]:
        vetores: list[list[float]] = []
        for i in range(0, len(textos), TAMANHO_LOTE):
            lote = textos[i : i + TAMANHO_LOTE]
            corpo = json.dumps({"model": self.modelo, "input": lote}).encode()
            pedido = urllib.request.Request(
                f"{self.url}/api/embed", data=corpo, headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(pedido, timeout=self.timeout) as resposta:
                    dados = json.loads(resposta.read())
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                raise EmbeddingsIndisponiveis(f"Ollama indisponível em {self.url}.") from exc
            except json.JSONDecodeError as exc:
                raise EmbeddingsIndisponiveis("Resposta inválida do Ollama.") from exc
            novos = dados.get("embeddings") or []
            if len(novos) != len(lote):
                raise EmbeddingsIndisponiveis(f"Modelo {self.modelo} não retornou embeddings.")
            vetores.extend(novos)
        return vetores


def obter_embedder():
    return import_string(settings.CONHECIMENTO_EMBEDDER)()


def empacotar(vetor: list[float]) -> bytes:
    return array.array("f", vetor).tobytes()


def desempacotar(dados: bytes) -> array.array:
    vetor = array.array("f")
    vetor.frombytes(bytes(dados))
    return vetor


def similaridade(a, b) -> float:
    produto = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return produto / (na * nb)
