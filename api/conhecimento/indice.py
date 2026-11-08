"""Índice textual FTS5 sobre as seções (rowid = id da seção).

A tabela virtual é criada pela migração 0002 e pode ser reconstruída a partir de
Secao com `reconstruir_fts()`.
"""

import re

from django.db import connection

TABELA = "conhecimento_secao_fts"
PALAVRAS_VAZIAS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas", "um", "uma",
    "para", "por", "com", "que", "qual", "quais", "como", "onde", "quando", "se", "eu", "meu", "minha",
    "é", "ser", "the", "of", "to", "and", "in", "is", "how", "what", "esse", "essa", "isso", "este", "esta",
}


def inserir(secoes) -> None:
    with connection.cursor() as cur:
        for s in secoes:
            cur.execute(
                f"INSERT INTO {TABELA}(rowid, titulos, texto, caminho) VALUES (%s, %s, %s, %s)",
                [s.pk, " > ".join(s.titulos), s.texto, s.documento.caminho],
            )


def remover(ids) -> None:
    ids = list(ids)
    if not ids:
        return
    with connection.cursor() as cur:
        for i in range(0, len(ids), 500):
            lote = ids[i : i + 500]
            cur.execute(f"DELETE FROM {TABELA} WHERE rowid IN ({','.join(['%s'] * len(lote))})", lote)


def termos(pergunta: str) -> list[str]:
    vistos, saida = set(), []
    for t in re.findall(r"\w+", pergunta.lower()):
        if t not in PALAVRAS_VAZIAS and len(t) > 1 and t not in vistos:
            vistos.add(t)
            saida.append(t)
    return saida


def buscar(pergunta: str, fonte_ids: list[int], limite: int = 20) -> list[tuple[int, float]]:
    """(secao_id, pontuação bm25) restritos às fontes autorizadas antes do ranqueamento."""
    lista = termos(pergunta)
    if not lista or not fonte_ids:
        return []
    consulta = " OR ".join(f'"{t}"' for t in lista)
    marcadores = ",".join(["%s"] * len(fonte_ids))
    sql = (
        f"SELECT f.rowid, bm25({TABELA}, 2.0, 1.0, 0.5) AS pontos FROM {TABELA} f "
        "JOIN conhecimento_secao s ON s.id = f.rowid "
        "JOIN conhecimento_documento d ON d.id = s.documento_id "
        f"WHERE {TABELA} MATCH %s AND d.incluido = 1 AND d.fonte_id IN ({marcadores}) "
        "ORDER BY pontos LIMIT %s"
    )
    with connection.cursor() as cur:
        cur.execute(sql, [consulta, *fonte_ids, limite])
        return [(linha[0], linha[1]) for linha in cur.fetchall()]


def reconstruir_fts() -> int:
    from conhecimento.models import Secao

    with connection.cursor() as cur:
        cur.execute(f"DELETE FROM {TABELA}")
    secoes = list(Secao.objects.select_related("documento").filter(documento__incluido=True))
    inserir(secoes)
    return len(secoes)
