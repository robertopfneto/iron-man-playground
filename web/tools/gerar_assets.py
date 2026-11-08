#!/usr/bin/env python3
"""Gera os assets de pixel art do Escritório 2D usando só a biblioteca padrão.

Saídas (versionadas):
  web/public/jogo/mapas/manifesto.json
  web/public/jogo/mapas/recepcao_padrao/{tileset.png,mapa.json,previa.png}
  web/public/jogo/avatares/{atlas.png,atlas.json,manifesto.json}
  web/public/jogo/avatares/retratos/<avatar_id>.png
  web/public/jogo/avatares/simbolos/<avatar_id>.png
  docs/arte/revisao_neto_pistori.png

A arte é desenhada por código a partir das descrições textuais de direção de
arte. Nenhuma foto de referência é lida por este script.

Uso: python3 web/tools/gerar_assets.py
"""

import json
import math
import struct
import zlib
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
JOGO = WEB / "public" / "jogo"
DOCS_ARTE = WEB.parent / "docs" / "arte"

LICENCA_ARTE = (
    "Arte própria do projeto Escritório 2D, gerada por web/tools/gerar_assets.py. "
    "Sem assets de terceiros."
)


# ---------------------------------------------------------------- cores / PNG


def cor(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def escurecer(c, f=0.75):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f), c[3])


def clarear(c, f=0.25):
    return (
        int(c[0] + (255 - c[0]) * f),
        int(c[1] + (255 - c[1]) * f),
        int(c[2] + (255 - c[2]) * f),
        c[3],
    )


class Tela:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[None] * w for _ in range(h)]

    def p(self, x, y, c):
        if c is not None and 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def apagar(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = None

    def g(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y][x]
        return None

    def ret(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.p(x, y, c)

    def moldura(self, x0, y0, x1, y1, c, esp=1):
        for e in range(esp):
            self.ret(x0 + e, y0 + e, x1 - e, y0 + e, c)
            self.ret(x0 + e, y1 - e, x1 - e, y1 - e, c)
            self.ret(x0 + e, y0 + e, x0 + e, y1 - e, c)
            self.ret(x1 - e, y0 + e, x1 - e, y1 - e, c)

    def elipse(self, cx, cy, rx, ry, c, filtro=None):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                dx = (x + 0.5 - cx) / rx
                dy = (y + 0.5 - cy) / ry
                if dx * dx + dy * dy <= 1.0 and (filtro is None or filtro(x, y)):
                    self.p(x, y, c)

    def trocar(self, filtro, de, para):
        """Recolore pixels iguais a `de` (ou qualquer pixel opaco se `de` for None)."""
        for y in range(self.h):
            for x in range(self.w):
                atual = self.px[y][x]
                if atual is not None and (de is None or atual == de) and filtro(x, y):
                    self.px[y][x] = para

    def contornar(self, fator=0.38):
        """Contorno seletivo: cada pixel de borda recebe a cor vizinha escurecida."""
        novos = []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] is not None:
                    continue
                viz = [self.g(x + 1, y), self.g(x - 1, y), self.g(x, y + 1), self.g(x, y - 1)]
                viz = [v for v in viz if v is not None and v[3] == 255]
                if viz:
                    base = min(viz, key=lambda v: v[0] + v[1] + v[2])
                    novos.append((x, y, escurecer(base, fator)))
        for x, y, c in novos:
            self.p(x, y, c)

    def sombra_chao(self, cx, cy, rx, ry, alfa=85):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                dx = (x + 0.5 - cx) / rx
                dy = (y + 0.5 - cy) / ry
                if dx * dx + dy * dy <= 1.0 and self.g(x, y) is None:
                    self.p(x, y, (8, 10, 16, alfa))

    def colar(self, outra, ox, oy, escala=1):
        for y in range(outra.h):
            for x in range(outra.w):
                c = outra.px[y][x]
                if c is None:
                    continue
                for sy in range(escala):
                    for sx in range(escala):
                        dx, dy = ox + x * escala + sx, oy + y * escala + sy
                        base = self.g(dx, dy)
                        if c[3] == 255 or base is None:
                            self.p(dx, dy, c)
                        else:
                            a = c[3] / 255
                            self.p(
                                dx,
                                dy,
                                (
                                    int(c[0] * a + base[0] * (1 - a)),
                                    int(c[1] * a + base[1] * (1 - a)),
                                    int(c[2] * a + base[2] * (1 - a)),
                                    base[3],
                                ),
                            )

    def icone(self, linhas, paleta, ox, oy, escala=1):
        for y, linha in enumerate(linhas):
            for x, ch in enumerate(linha):
                if ch != ".":
                    self.ret(
                        ox + x * escala,
                        oy + y * escala,
                        ox + x * escala + escala - 1,
                        oy + y * escala + escala - 1,
                        paleta[ch],
                    )


def salvar_png(caminho, tela):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    bruto = bytearray()
    for y in range(tela.h):
        bruto.append(0)
        for x in range(tela.w):
            bruto.extend(tela.px[y][x] or (0, 0, 0, 0))

    def chunk(tipo, dados):
        return (
            struct.pack(">I", len(dados))
            + tipo
            + dados
            + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", tela.w, tela.h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(bruto), 9))
        + chunk(b"IEND", b"")
    )
    caminho.write_bytes(png)


def salvar_json(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- paletas

PRETO = cor("#121214")
BRANCO_OLHO = cor("#f3efe8")
BRILHO = cor("#ffffff")
OLHO_SPRITE = cor("#2a1f1d")
LABIO = cor("#9a5446")
DENTES = cor("#f4f0e8")
CALCA_PADRAO = cor("#2a2f3a")
SAPATO_PADRAO = cor("#141519")
MANEQUIM = cor("#c3c9d4")
MANEQUIM_S = cor("#9aa2b0")
PLACA = cor("#eef1f6")

NETO = {
    "pele": cor("#e0ac85"),
    "pele_s": cor("#c38a66"),
    "cabelo": cor("#2b2220"),
    "cabelo_l": cor("#4d3c34"),
    "cabelo_s": cor("#1a1413"),
    "roupa": cor("#1d1f24"),
    "roupa_s": cor("#131418"),
    "azul": cor("#3f86ec"),
    "dourado": cor("#e0b13c"),
    "calca": cor("#2a2f3a"),
    "sapato": cor("#141519"),
    "relogio": cor("#0b0b0d"),
    "iris": cor("#3b2a20"),
}

PISTORI = {
    "pele": cor("#e6b593"),
    "pele_s": cor("#c79374"),
    "cabelo": cor("#a9acb2"),
    "cabelo_l": cor("#d4d6da"),
    "cabelo_s": cor("#7c7f86"),
    "barba": cor("#8f9197"),
    "barba_l": cor("#b5b7bc"),
    "barba_s": cor("#6c6e74"),
    "armacao": cor("#17171b"),
    "lente": cor("#dceaf4"),
    "roupa": cor("#1d1f24"),
    "roupa_s": cor("#131418"),
    "azul": cor("#3f86ec"),
    "laranja": cor("#ee8a3c"),
    "calca": cor("#30343d"),
    "sapato": cor("#141519"),
    "iris": cor("#4a3a2c"),
}

# Símbolos individuais 7x7 (objeto de cada ficha de direção de arte).
SIMBOLOS = {
    "neto": (
        [".BBBBB.", "BBBBBBB", "BYBYBYB", "BBBBBBB", ".BBBBB.", "..BB...", ".B....."],
        {"B": cor("#3f86ec"), "Y": cor("#e0b13c")},
    ),
    "pistori": (
        [".......", ".......", "FFF.FFF", "FLFFFLF", "FFF.FFF", ".......", "......."],
        {"F": cor("#17171b"), "L": cor("#9cc7e6")},
    ),
    "kernighan": (
        [".CCCCY.", ".CPPPCY", ".CPPPC.", ".CPPPCY", ".CPPPC.", ".CPPPC.", ".CCCCC."],
        {"C": cor("#4a4d55"), "P": cor("#f3efe2"), "Y": cor("#e8c547")},
    ),
    "lecun": (
        ["..AAA..", ".AAAAA.", "..BBB..", ".BBBBB.", "..CCC..", ".CCCCC.", "......."],
        {"A": cor("#7fa3ec"), "B": cor("#3f6fd6"), "C": cor("#24459a")},
    ),
    "hopper": (
        [".G...G.", ".G...G.", "GGGGGGG", "GGGGGGG", "..GGG..", "...G...", "...G..."],
        {"G": cor("#e0b13c")},
    ),
    "liskov": (
        ["..KKK..", "PPPPPPP", "PRRRPPP", "PRVVVVP", "PRRVPVP", "PPPVVVP", "PPPPPPP"],
        {"K": cor("#6b6f78"), "P": cor("#efe7d6"), "R": cor("#7a2337"), "V": cor("#b5475f")},
    ),
    "lamport": (
        [".......", "AAA....", "ABBB...", "ABCCC..", ".BCCC..", "..CCC..", "......."],
        {"A": cor("#d8dcc0"), "B": cor("#a7b06a"), "C": cor("#6b7238")},
    ),
    "salton": (
        [".GGG...", "G...G..", "G.L.G..", "G...G..", ".GGG...", "....HH.", ".....HH"],
        {"G": cor("#5b3a55"), "L": cor("#bfe1f2"), "H": cor("#8a5a3a")},
    ),
    "luhn": (
        [".......", "CCCCCCC", "CKCKCKC", "CCCCCCC", "CCCCCCC", "CCCCCCC", "......."],
        {"C": cor("#e9c9a3"), "K": cor("#7a4428")},
    ),
    "hamming": (
        ["FFFFFFF", "FLFLFLF", "FFFFFFF", "FLFHFLF", "FFFFFFF", "FLFLFLF", "FFFFFFF"],
        {"F": cor("#8c7650"), "L": cor("#e8dcc0"), "H": cor("#ee8a3c")},
    ),
    "knuth": (
        [".......", "PPPBPPP", "PMPBPPP", "PPPBPMP", "PMPBPPP", "PPPBPPP", "BBBBBBB"],
        {"P": cor("#f5f2ea"), "M": cor("#1f6b7a"), "B": cor("#174e59")},
    ),
    "kohavi": (
        [".LL.DD.", ".LL.DD.", ".WW.KK.", ".LL.DD.", ".LL.DD.", ".LL.DD.", "......."],
        {"L": cor("#d9ecb0"), "D": cor("#4f6a2a"), "W": cor("#ffffff"), "K": cor("#1b2410")},
    ),
    "fei-fei": (
        ["VVVVVVV", "VIIIIIV", "VIIIIIV", "VIIDIIV", "VIIIIIV", "VIIIIIV", "VVVVVVV"],
        {"V": cor("#6f4bb8"), "I": cor("#d9ccf5"), "D": cor("#2a1a52")},
    ),
    "torralba": (
        ["CCC....", "C......", "C......", "...D...", "......C", "......C", "....CCC"],
        {"C": cor("#1f8f9a"), "D": cor("#ee6b5a")},
    ),
    "torvalds": (
        ["..N....", "..B....", "..B.N..", "..BB...", "..B....", "..N....", "......."],
        {"N": cor("#7fd1b1"), "B": cor("#3b8f72")},
    ),
    "hamilton": (
        [".LFFFF.", ".LFFFF.", ".LGGGG.", ".LGGGG.", ".LFFFF.", ".LFFFF.", "......."],
        {"L": cor("#eef1f6"), "F": cor("#4f6d8f"), "G": cor("#7a93b0")},
    ),
    "papert": (
        ["...H...", "L.SSS.L", ".SPSPS.", ".SSPSS.", ".SPSPS.", "L.SSS.L", "...T..."],
        {"H": cor("#5c9a4a"), "L": cor("#5c9a4a"), "S": cor("#3f7a3a"), "P": cor("#a6d28a"), "T": cor("#5c9a4a")},
    ),
}

# Elenco (id, nome, cor principal da roupa de jogo) na ordem do catálogo.
# Neto e Pistori têm arte própria; os demais usam placeholder com o símbolo individual.
ELENCO = [
    ("neto", "Neto", None),
    ("pistori", "Pistori", None),
    ("kernighan", "Kernighan", cor("#4a4d55")),
    ("lecun", "LeCun", cor("#2f5dc2")),
    ("hopper", "Hopper", cor("#1f2d55")),
    ("liskov", "Liskov", cor("#7a2337")),
    ("lamport", "Lamport", cor("#6b7238")),
    ("salton", "Salton", cor("#6e3b62")),
    ("luhn", "Luhn", cor("#a5623a")),
    ("hamming", "Hamming", cor("#b39a68")),
    ("knuth", "Knuth", cor("#1f6b7a")),
    ("kohavi", "Kohavi", cor("#8fb049")),
    ("fei-fei", "Fei-Fei", cor("#6f4bb8")),
    ("torralba", "Torralba", cor("#1f6f78")),
    ("torvalds", "Torvalds", cor("#7d838c")),
    ("hamilton", "Hamilton", cor("#4f6d8f")),
    ("papert", "Papert", cor("#6f98cc")),
]

# ---------------------------------------------------------------- sprites 32x48
# Base comum: mesmas proporções, apoio nos pés em y=45 e luz vinda de cima/esquerda.


def corpo_frente(t, roupa, roupa_s, calca, sapato, pele, pele_s):
    calca_s = escurecer(calca, 0.78)
    t.ret(12, 36, 19, 38, calca)
    t.ret(12, 39, 14, 42, calca)
    t.ret(17, 39, 19, 42, calca)
    t.ret(14, 39, 14, 42, calca_s)
    t.ret(19, 36, 19, 42, calca_s)
    t.ret(11, 43, 14, 44, sapato)
    t.ret(17, 43, 20, 44, sapato)
    t.ret(10, 25, 21, 35, roupa)
    t.apagar(10, 25)
    t.apagar(21, 25)
    t.ret(20, 26, 21, 35, roupa_s)
    t.ret(8, 26, 9, 30, roupa)
    t.ret(22, 26, 23, 30, roupa_s)
    t.apagar(8, 26)
    t.apagar(23, 26)
    t.ret(8, 31, 9, 34, pele)
    t.ret(22, 31, 23, 34, pele_s)
    t.ret(14, 23, 17, 24, pele_s)


def cabeca_frente(t, pele, pele_s):
    t.elipse(16, 15, 7.5, 8.2, pele)
    t.trocar(lambda x, y: x >= 21, pele, pele_s)


def rosto_frente(t, pele_s):
    for x in (12, 19):
        t.p(x, 16, OLHO_SPRITE)
        t.p(x, 17, OLHO_SPRITE)
    t.p(16, 19, pele_s)


def sprite_neto():
    t = Tela(32, 48)
    p = NETO
    corpo_frente(t, p["roupa"], p["roupa_s"], p["calca"], p["sapato"], p["pele"], p["pele_s"])
    t.ret(13, 25, 18, 25, p["dourado"])
    t.ret(15, 25, 16, 25, p["pele_s"])
    t.ret(8, 30, 9, 30, p["azul"])
    t.ret(22, 30, 23, 30, escurecer(p["azul"], 0.8))
    t.ret(8, 33, 9, 33, p["relogio"])
    # Emblema circular de conversa (coordenação).
    t.ret(16, 28, 18, 30, p["azul"])
    for x, y in ((16, 28), (18, 28), (16, 30), (18, 30)):
        t.p(x, y, p["roupa"])
    t.p(17, 29, p["dourado"])
    t.p(16, 31, p["azul"])

    cabeca_frente(t, p["pele"], p["pele_s"])
    rosto_frente(t, p["pele_s"])
    t.ret(11, 14, 13, 14, p["cabelo"])
    t.ret(18, 14, 20, 14, p["cabelo"])
    t.p(13, 20, LABIO)
    t.ret(14, 21, 17, 21, LABIO)
    t.p(18, 20, LABIO)

    c, cl, cs = p["cabelo"], p["cabelo_l"], p["cabelo_s"]
    t.elipse(16, 10.5, 8.6, 6.4, c, filtro=lambda x, y: (y <= 12 or x <= 9 or x >= 22) and y <= 15)
    for x, y in ((10, 4), (11, 3), (12, 3), (15, 3), (16, 2), (17, 3), (20, 3), (21, 4)):
        t.p(x, y, c)
    for x, y in ((12, 5), (13, 6), (16, 4), (17, 5), (19, 6), (11, 8), (14, 9), (18, 9)):
        t.p(x, y, cl)
    t.trocar(lambda x, y: x >= 21 and y <= 15, c, cs)
    t.p(13, 13, c)
    t.p(14, 13, c)

    t.contornar()
    t.sombra_chao(16, 46, 8, 2)
    return t


def sprite_pistori():
    t = Tela(32, 48)
    p = PISTORI
    corpo_frente(t, p["roupa"], p["roupa_s"], p["calca"], p["sapato"], p["pele"], p["pele_s"])
    t.ret(13, 25, 18, 25, p["laranja"])
    t.ret(15, 25, 16, 25, p["pele_s"])
    t.ret(8, 30, 9, 30, p["azul"])
    t.ret(22, 30, 23, 30, escurecer(p["azul"], 0.8))
    t.ret(12, 28, 13, 28, p["azul"])
    t.ret(12, 29, 13, 29, p["laranja"])

    cabeca_frente(t, p["pele"], p["pele_s"])
    rosto_frente(t, p["pele_s"])

    c, cl, cs = p["cabelo"], p["cabelo_l"], p["cabelo_s"]
    t.elipse(16, 10.8, 8.0, 5.4, c, filtro=lambda x, y: (y <= 11 or x <= 9 or x >= 22) and y <= 14)
    for y in range(4, 10):
        for x in range(32):
            if t.g(x, y) == c:
                if (x * 3 + y * 5) % 7 == 0:
                    t.p(x, y, cl)
                elif (x + y * 3) % 6 == 0:
                    t.p(x, y, cs)
    t.trocar(lambda x, y: x >= 21 and y <= 14, c, cs)
    t.ret(11, 13, 13, 13, cs)
    t.ret(18, 13, 20, 13, cs)

    arm = p["armacao"]
    t.moldura(10, 15, 14, 18, arm)
    t.moldura(17, 15, 21, 18, arm)
    t.ret(15, 16, 16, 16, arm)
    t.p(9, 16, arm)
    t.p(22, 16, arm)
    t.p(11, 16, p["lente"])
    t.p(18, 16, p["lente"])

    cav, cav_s = p["barba"], p["barba_s"]
    t.ret(13, 20, 18, 20, cav)
    t.p(12, 21, cav)
    t.p(19, 21, cav)
    t.ret(15, 21, 16, 21, LABIO)
    t.ret(14, 22, 17, 23, cav)
    t.ret(15, 24, 16, 24, cav)
    t.trocar(lambda x, y: x >= 17 and y >= 20, cav, cav_s)

    t.contornar()
    t.sombra_chao(16, 46, 8, 2)
    return t


def sprite_placeholder(avatar_id, roupa):
    t = Tela(32, 48)
    corpo_frente(t, roupa, escurecer(roupa, 0.78), CALCA_PADRAO, SAPATO_PADRAO, MANEQUIM, MANEQUIM_S)
    cabeca_frente(t, MANEQUIM, MANEQUIM_S)
    if avatar_id in SIMBOLOS:
        linhas, paleta = SIMBOLOS[avatar_id]
        t.ret(11, 26, 19, 34, PLACA)
        t.icone(linhas, paleta, 12, 27)
    t.contornar()
    t.sombra_chao(16, 46, 8, 2)
    return t


# ---------------------------------------------------------------- retratos 96x96


def busto(t, roupa, roupa_s, pele, pele_s, gola):
    t.elipse(48, 106, 42, 33, roupa)
    t.trocar(lambda x, y: x >= 70, roupa, roupa_s)
    t.ret(39, 58, 56, 80, pele)
    t.trocar(lambda x, y: x >= 52 or y <= 64, pele, pele_s)
    t.elipse(48, 76, 12.5, 7.4, gola, filtro=lambda x, y: y >= 73)
    t.elipse(48, 76, 10.5, 6, pele, filtro=lambda x, y: y >= 73)
    t.trocar(lambda x, y: x >= 52 and y >= 73, pele, pele_s)


def rosto_retrato(t, pele, pele_s):
    t.elipse(26.5, 48, 3.2, 6, pele)
    t.elipse(69.5, 48, 3.2, 6, pele_s)
    cx, cy, ry = 48, 44, 25
    for y in range(18, 72):
        base = 21 * math.sqrt(max(0.0, 1 - ((y + 0.5 - cy) / ry) ** 2))
        if y > 48:
            base = min(base, 21 - (y - 48) * 0.42)
        for x in range(20, 76):
            d = x + 0.5 - cx
            if abs(d) <= base:
                t.p(x, y, pele_s if d > base * 0.55 else pele)


def olhos_retrato(t, pele_s, iris, cilio):
    for cx in (39, 57):
        y = 45
        t.ret(cx - 3, y, cx + 2, y + 2, BRANCO_OLHO)
        t.ret(cx - 1, y, cx + 1, y + 2, iris)
        t.p(cx, y + 1, PRETO)
        t.p(cx - 1, y, BRILHO)
        t.ret(cx - 4, y - 1, cx + 3, y - 1, cilio)
        t.ret(cx - 3, y + 3, cx + 2, y + 3, pele_s)


def nariz_retrato(t, pele_s):
    t.ret(49, 47, 49, 54, pele_s)
    t.ret(46, 56, 50, 56, pele_s)
    t.p(45, 55, pele_s)
    t.p(51, 55, pele_s)


def costura_ombros(t, c):
    for i in range(15):
        x, y = 16 + i, 88 - (i * 8) // 14
        t.p(x, y, c)
        t.p(x, y + 1, c)
        x2 = 79 - i
        t.p(x2, y, escurecer(c, 0.8))
        t.p(x2, y + 1, escurecer(c, 0.8))


def retrato_neto():
    t = Tela(96, 96)
    p = NETO
    busto(t, p["roupa"], p["roupa_s"], p["pele"], p["pele_s"], p["dourado"])
    costura_ombros(t, p["azul"])
    t.elipse(64, 87, 5.5, 5.5, p["azul"])
    t.elipse(64, 87, 3.6, 3.6, p["roupa"])
    for x in (62, 64, 66):
        t.p(x, 87, p["dourado"])
    t.p(60, 92, p["azul"])
    t.p(59, 93, p["azul"])

    rosto_retrato(t, p["pele"], p["pele_s"])
    olhos_retrato(t, p["pele_s"], p["iris"], p["cabelo_s"])
    nariz_retrato(t, p["pele_s"])

    for x0, x1 in ((32, 44), (52, 64)):
        for x in range(x0, x1 + 1):
            arco = 1 if x0 + 3 <= x <= x1 - 3 else 0
            esp = 3 if x0 + 2 <= x <= x1 - 2 else 2
            t.ret(x, 40 - arco, x, 40 - arco + esp - 1, p["cabelo"])

    for x in range(40, 57):
        d = (x + 0.5 - 48.5) / 8.5
        yb = 61 + round(3 * (1 - d * d))
        for y in range(62, yb):
            t.p(x, y, DENTES)
        t.p(x, yb, LABIO)
    t.ret(41, 61, 56, 61, LABIO)
    t.p(39, 60, LABIO)
    t.p(57, 60, LABIO)

    c, cl, cs = p["cabelo"], p["cabelo_l"], p["cabelo_s"]

    def linha(x):
        return 33 + 0.012 * (x - 48) ** 2

    t.elipse(48, 31, 26.5, 17.5, c, filtro=lambda x, y: y <= linha(x) or ((x <= 28 or x >= 68) and y <= 51))
    ondas = ((27, 24, 6), (34, 17, 7), (44, 13, 7), (55, 13, 7), (64, 17, 7), (70, 25, 6))
    for bx, by, r in ondas:
        t.elipse(bx, by, r, r * 0.8, c)
    for bx, by, r in ondas:
        for ang in range(200, 340, 6):
            a = math.radians(ang)
            t.p(int(bx + (r - 2.2) * math.cos(a)), int(by + (r - 2.2) * 0.8 * math.sin(a)), cl)
    t.trocar(lambda x, y: x >= 64, c, cs)
    t.trocar(lambda x, y: linha(x) - 2 <= y <= linha(x) and 30 < x < 66, c, cs)
    for x0, comp in ((38, 3), (46, 4), (54, 3)):
        for i in range(comp):
            t.p(x0 + (i % 2), int(linha(x0)) + 1 + i, c)

    t.contornar(0.4)
    return t


def retrato_pistori():
    t = Tela(96, 96)
    p = PISTORI
    busto(t, p["roupa"], p["roupa_s"], p["pele"], p["pele_s"], p["laranja"])
    costura_ombros(t, p["azul"])
    t.ret(58, 84, 70, 85, p["laranja"])
    t.ret(58, 86, 70, 87, p["azul"])

    rosto_retrato(t, p["pele"], p["pele_s"])
    olhos_retrato(t, p["pele_s"], p["iris"], p["cabelo_s"])
    nariz_retrato(t, p["pele_s"])

    for x0, x1 in ((33, 44), (52, 63)):
        for x in range(x0, x1 + 1):
            arco = 1 if x0 + 3 <= x <= x1 - 3 else 0
            t.ret(x, 38 - arco, x, 39 - arco, p["cabelo_s"])

    c, cl, cs = p["cabelo"], p["cabelo_l"], p["cabelo_s"]

    def linha(x):
        return 29 + 0.011 * (x - 48) ** 2

    t.elipse(48, 30, 23.5, 13.5, c, filtro=lambda x, y: y <= linha(x) or ((x <= 28 or x >= 68) and y <= 46))
    for y in range(96):
        for x in range(96):
            if t.g(x, y) == c:
                v = (x * 13 + y * 7) % 11
                if v == 0 or (y <= 22 and (x + y) % 4 == 0):
                    t.p(x, y, cl)
                elif v == 5:
                    t.p(x, y, cs)
    t.trocar(lambda x, y: x >= 64 and y <= 46, c, cs)

    arm = p["armacao"]
    t.moldura(30, 40, 46, 53, arm, 2)
    t.moldura(50, 40, 66, 53, arm, 2)
    t.ret(47, 44, 49, 45, arm)
    t.ret(26, 44, 29, 45, arm)
    t.ret(67, 44, 70, 45, arm)
    for i in range(4):
        t.p(33 + i, 50 - i, p["lente"])
        t.p(53 + i, 50 - i, p["lente"])

    cav, cav_l, cav_s = p["barba"], p["barba_l"], p["barba_s"]
    for x in range(38, 59):
        topo = 58 + (1 if x in (38, 39, 57, 58) else 0)
        t.ret(x, topo, x, 60, cav)
    # Pontas curvadas do bigode.
    for x, y in ((37, 60), (36, 61), (35, 61), (34, 60), (34, 59)):
        t.p(x, y, cav)
    for x, y in ((59, 60), (60, 61), (61, 61), (62, 60), (62, 59)):
        t.p(x, y, cav)
    t.ret(45, 62, 51, 62, LABIO)
    t.ret(46, 63, 50, 63, escurecer(p["pele"], 0.85))
    # Cavanhaque alongado, concentrado no queixo.
    for y in range(65, 78):
        meia = 6.5 - (y - 65) * 0.32
        for x in range(36, 60):
            if abs(x + 0.5 - 48) <= meia:
                t.p(x, y, cav)
    for y in range(56, 80):
        for x in range(30, 66):
            if t.g(x, y) == cav:
                if x >= 50:
                    t.p(x, y, cav_s)
                elif (x + y) % 3 == 0:
                    t.p(x, y, cav_l)

    t.contornar(0.4)
    return t


def retrato_placeholder(avatar_id, roupa):
    t = Tela(96, 96)
    raio, m = 20, 4
    for y in range(m, 96 - m):
        for x in range(m, 96 - m):
            cx = min(max(x, m + raio), 96 - m - raio - 1)
            cy = min(max(y, m + raio), 96 - m - raio - 1)
            if (x - cx) ** 2 + (y - cy) ** 2 <= raio * raio:
                t.p(x, y, clarear(roupa, 0.08) if y < 48 else roupa)
    borda = escurecer(roupa, 0.7)
    for y in range(96):
        for x in range(96):
            if t.g(x, y) is not None and any(
                t.g(x + dx, y + dy) is None for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            ):
                t.p(x, y, borda)
    t.elipse(48, 48, 32, 32, PLACA)
    if avatar_id in SIMBOLOS:
        linhas, paleta = SIMBOLOS[avatar_id]
        t.icone(linhas, paleta, 27, 27, 6)
    return t


# ---------------------------------------------------------------- tileset 16x16


def _tile():
    return Tela(16, 16)


def tile_madeira():
    t = _tile()
    base, esc, luz = cor("#8a6a4a"), cor("#6f533a"), cor("#9e7c57")
    for y in range(16):
        for x in range(16):
            emenda = ((y // 4) * 5 + 3) % 16
            c = base
            if y % 4 == 3 or x == emenda:
                c = esc
            elif y % 4 == 0:
                c = luz
            t.p(x, y, c)
    return t


def tile_carpete():
    t = _tile()
    base, alt, luz = cor("#3b4a6b"), cor("#35435f"), cor("#43537a")
    for y in range(16):
        for x in range(16):
            c = base
            if (x + y) % 4 == 0:
                c = alt
            elif (x * 3 + y) % 7 == 0:
                c = luz
            t.p(x, y, c)
    return t


def tile_piso_claro():
    t = _tile()
    base, linha, luz = cor("#aab3be"), cor("#959eaa"), cor("#bac2cc")
    for y in range(16):
        for x in range(16):
            if x % 8 == 7 or y % 8 == 7:
                c = linha
            elif x % 8 == 0 or y % 8 == 0:
                c = luz
            else:
                c = base
            t.p(x, y, c)
    return t


def tile_parede_topo():
    t = _tile()
    t.ret(0, 0, 15, 15, cor("#262c3a"))
    t.ret(0, 0, 15, 0, cor("#323a4c"))
    t.ret(0, 14, 15, 15, cor("#1c212c"))
    return t


def tile_parede_frente():
    t = _tile()
    t.ret(0, 0, 15, 15, cor("#56607a"))
    t.ret(0, 0, 15, 1, cor("#68738f"))
    t.ret(0, 7, 15, 7, cor("#505a73"))
    t.ret(0, 13, 15, 15, cor("#363d4e"))
    t.ret(0, 12, 15, 12, cor("#7a849d"))
    return t


def tile_parede_janela():
    t = tile_parede_frente()
    t.ret(2, 2, 13, 11, cor("#d9dde6"))
    t.ret(3, 3, 12, 10, cor("#7fb2d9"))
    t.ret(7, 3, 8, 10, cor("#d9dde6"))
    for i in range(4):
        t.p(4 + i, 9 - i, cor("#b4d4ee"))
        t.p(9 + i, 9 - i, cor("#b4d4ee"))
    return t


def tile_quadro():
    t = tile_parede_frente()
    t.ret(1, 2, 14, 10, cor("#9aa3b2"))
    t.ret(2, 3, 13, 9, cor("#eef1f5"))
    t.ret(3, 4, 8, 4, cor("#3f86ec"))
    t.ret(3, 6, 10, 6, cor("#4a4f5c"))
    t.ret(3, 8, 6, 8, cor("#d0524a"))
    t.ret(2, 11, 13, 11, cor("#7e8796"))
    return t


def tile_tapete():
    t = _tile()
    t.ret(0, 0, 15, 15, cor("#6d2f2f"))
    t.ret(1, 1, 14, 14, cor("#8a3d3d"))
    for y in range(3, 13, 3):
        t.ret(3, y, 12, y, cor("#a95454"))
    return t


def tile_mesa_topo():
    t = _tile()
    t.ret(0, 0, 15, 15, cor("#a87a4f"))
    t.ret(0, 0, 15, 1, cor("#c09166"))
    for y in (5, 10):
        t.ret(0, y, 15, y, cor("#9a6e46"))
    return t


def tile_mesa_frente():
    t = _tile()
    t.ret(0, 0, 15, 4, cor("#6e4c2f"))
    t.ret(0, 0, 15, 0, cor("#8a6040"))
    t.ret(0, 5, 15, 8, (8, 10, 16, 70))
    return t


def tile_mesa_trab_monitor():
    t = _tile()
    t.ret(0, 0, 15, 15, cor("#b58e62"))
    t.ret(0, 0, 15, 0, cor("#c9a479"))
    t.ret(3, 1, 12, 8, cor("#1e2330"))
    t.ret(4, 2, 11, 7, cor("#4f8fd6"))
    t.ret(5, 3, 9, 3, cor("#a8cdf2"))
    t.ret(5, 5, 8, 5, cor("#a8cdf2"))
    t.ret(7, 9, 8, 10, cor("#1e2330"))
    t.ret(4, 12, 11, 13, cor("#dfe3ea"))
    return t


def tile_mesa_trab():
    t = _tile()
    t.ret(0, 0, 15, 15, cor("#b58e62"))
    t.ret(0, 0, 15, 0, cor("#c9a479"))
    t.ret(3, 4, 8, 10, cor("#f1efe8"))
    t.ret(4, 6, 7, 6, cor("#9aa3b2"))
    t.ret(4, 8, 6, 8, cor("#9aa3b2"))
    t.ret(11, 5, 12, 7, cor("#d05a4a"))
    return t


def tile_mesa_trab_frente():
    t = _tile()
    t.ret(0, 0, 15, 4, cor("#8a6845"))
    t.ret(0, 0, 15, 0, cor("#a07a52"))
    t.ret(0, 5, 15, 8, (8, 10, 16, 70))
    return t


def tile_cadeira():
    t = _tile()
    t.ret(4, 2, 11, 4, cor("#283654"))
    t.ret(4, 5, 11, 12, cor("#34466b"))
    t.ret(5, 6, 10, 6, cor("#41578a"))
    t.ret(5, 13, 10, 14, (8, 10, 16, 70))
    return t


def tile_planta():
    t = _tile()
    t.elipse(8, 6, 6.5, 6, cor("#3f9a5b"))
    for x, y in ((5, 3), (8, 2), (11, 4), (4, 7), (12, 8), (7, 5), (10, 7)):
        t.p(x, y, cor("#5cbf77"))
    for x, y in ((6, 9), (9, 10), (11, 10), (3, 6)):
        t.p(x, y, cor("#2e7445"))
    for y in range(10, 16):
        recuo = (y - 10) // 3
        t.ret(5 + recuo, y, 10 - recuo, y, cor("#b5653d"))
    t.ret(5, 10, 10, 10, cor("#cf7a4f"))
    return t


def tile_balcao_topo():
    t = _tile()
    t.ret(0, 2, 15, 15, cor("#d9d2c3"))
    t.ret(0, 2, 15, 3, cor("#efe9dc"))
    t.ret(0, 15, 15, 15, cor("#b8b0a0"))
    return t


def tile_balcao_frente():
    t = _tile()
    t.ret(0, 0, 15, 12, cor("#7e6a55"))
    t.ret(0, 0, 15, 0, cor("#5d4c3b"))
    t.moldura(2, 2, 13, 10, cor("#6c5a47"))
    t.ret(0, 13, 15, 15, (8, 10, 16, 70))
    return t


def tile_estante():
    t = _tile()
    t.ret(0, 0, 15, 15, cor("#5a4330"))
    t.ret(1, 1, 14, 14, cor("#3b2c20"))
    livros = [cor("#d0524a"), cor("#3f86ec"), cor("#e0b13c"), cor("#4fa36b"), cor("#9b6bd1")]
    for prateleira, y0 in enumerate((1, 8)):
        x = 2
        i = prateleira * 2
        while x < 14:
            larg = 1 + (i % 2)
            alt = 5 - (1 if i % 3 == 0 else 0)
            t.ret(x, y0 + (6 - alt), min(x + larg - 1, 13), y0 + 5, livros[i % len(livros)])
            x += larg + 1
            i += 1
        t.ret(1, y0 + 6, 14, y0 + 6, cor("#5a4330"))
    return t


def tile_sofa():
    t = _tile()
    t.ret(0, 3, 15, 13, cor("#4f63a0"))
    t.ret(0, 3, 15, 6, cor("#3f5088"))
    t.ret(0, 3, 1, 13, cor("#3f5088"))
    t.ret(14, 3, 15, 13, cor("#3f5088"))
    t.ret(2, 7, 13, 12, cor("#5b70b0"))
    t.ret(7, 7, 8, 12, cor("#4f63a0"))
    t.ret(1, 14, 14, 15, (8, 10, 16, 70))
    return t


TILES = [
    ("madeira", tile_madeira),
    ("carpete", tile_carpete),
    ("piso_claro", tile_piso_claro),
    ("parede_topo", tile_parede_topo),
    ("parede_frente", tile_parede_frente),
    ("parede_janela", tile_parede_janela),
    ("tapete", tile_tapete),
    ("mesa_topo", tile_mesa_topo),
    ("mesa_frente", tile_mesa_frente),
    ("mesa_trab_monitor", tile_mesa_trab_monitor),
    ("mesa_trab", tile_mesa_trab),
    ("mesa_trab_frente", tile_mesa_trab_frente),
    ("cadeira", tile_cadeira),
    ("planta", tile_planta),
    ("balcao_topo", tile_balcao_topo),
    ("balcao_frente", tile_balcao_frente),
    ("estante", tile_estante),
    ("sofa", tile_sofa),
    ("quadro", tile_quadro),
]
INDICE = {nome: i for i, (nome, _) in enumerate(TILES)}
COLUNAS_TILESET = 8


def gid(nome):
    return INDICE[nome] + 1


def gerar_tileset():
    linhas = (len(TILES) + COLUNAS_TILESET - 1) // COLUNAS_TILESET
    t = Tela(16 * COLUNAS_TILESET, 16 * linhas)
    imagens = {}
    for i, (nome, fn) in enumerate(TILES):
        tile = fn()
        imagens[nome] = tile
        t.colar(tile, (i % COLUNAS_TILESET) * 16, (i // COLUNAS_TILESET) * 16)
    return t, imagens


# ---------------------------------------------------------------- mapa Tiled

L, A = 28, 17  # largura e altura em tiles


def gerar_mapa():
    piso = [[0] * L for _ in range(A)]
    obs = [[0] * L for _ in range(A)]

    for x in range(L):
        obs[0][x] = gid("parede_topo")
        obs[A - 1][x] = gid("parede_topo")
    for x in range(L):
        if x in (0, 9, 19, 27):
            obs[1][x] = gid("parede_topo")
        elif x in (3, 6, 12, 16, 22, 25):
            obs[1][x] = gid("parede_janela")
        elif x == 14:
            obs[1][x] = gid("quadro")
        else:
            obs[1][x] = gid("parede_frente")
    for y in range(2, A - 1):
        for x in (0, 27):
            obs[y][x] = gid("parede_topo")
        for x in (9, 19):
            if not 7 <= y <= 9:
                obs[y][x] = gid("parede_topo")

    for y in range(2, A - 1):
        for x in range(1, 27):
            if x <= 9:
                piso[y][x] = gid("madeira")
            elif x <= 18:
                piso[y][x] = gid("carpete")
            else:
                piso[y][x] = gid("piso_claro")
    # Entrada: abertura na parede de baixo da recepção, com tapete.
    for x in (3, 4):
        obs[A - 1][x] = 0
        piso[A - 1][x] = gid("madeira")
        piso[A - 2][x] = gid("tapete")

    def mobilia(x, y, nome):
        obs[y][x] = gid(nome)

    # Recepção
    for x in range(2, 6):
        mobilia(x, 4, "balcao_topo")
        mobilia(x, 5, "balcao_frente")
    mobilia(7, 2, "estante")
    mobilia(8, 2, "estante")
    mobilia(1, 2, "planta")
    mobilia(8, 14, "planta")
    mobilia(6, 12, "sofa")
    mobilia(7, 12, "sofa")
    # Sala de reunião
    for x in range(12, 16):
        mobilia(x, 6, "mesa_topo")
        mobilia(x, 7, "mesa_frente")
    mobilia(10, 2, "planta")
    mobilia(18, 2, "planta")
    mobilia(18, 14, "planta")
    # Área de trabalho: quatro mesas
    for x0, y0 in ((21, 4), (24, 4), (21, 10), (24, 10)):
        mobilia(x0, y0, "mesa_trab_monitor")
        mobilia(x0 + 1, y0, "mesa_trab")
        mobilia(x0, y0 + 1, "mesa_trab_frente")
        mobilia(x0 + 1, y0 + 1, "mesa_trab_frente")
    mobilia(20, 2, "planta")
    mobilia(26, 2, "planta")
    mobilia(26, 14, "planta")

    objetos = []

    def ponto(nome, tipo, x, y, direcao="baixo"):
        objetos.append(
            {
                "id": len(objetos) + 1,
                "name": nome,
                "type": tipo,
                "point": True,
                "x": x,
                "y": y,
                "width": 0,
                "height": 0,
                "rotation": 0,
                "visible": True,
                "properties": [{"name": "direcao", "type": "string", "value": direcao}],
            }
        )

    def area(nome, x, y, w, h):
        objetos.append(
            {
                "id": len(objetos) + 1,
                "name": nome,
                "type": "area",
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "rotation": 0,
                "visible": True,
            }
        )

    area("Recepção", 16, 32, 128, 224)
    area("Sala de reunião", 160, 32, 144, 224)
    area("Área de trabalho", 320, 32, 112, 224)
    ponto("entrada", "entrada", 64, 262, "cima")
    ponto("mesa_reuniao", "mesa_reuniao", 180, 126, "direita")
    ponto("assento_reuniao_1", "assento_reuniao", 268, 126, "esquerda")
    ponto("assento_reuniao_2", "assento_reuniao", 208, 182, "cima")
    ponto("assento_reuniao_3", "assento_reuniao", 240, 182, "cima")
    ponto("assento_reuniao_4", "assento_reuniao", 272, 194, "cima")
    ponto("trabalho_1", "trabalho", 352, 118, "cima")
    ponto("trabalho_2", "trabalho", 400, 118, "cima")
    ponto("trabalho_3", "trabalho", 352, 214, "cima")
    ponto("trabalho_4", "trabalho", 400, 214, "cima")
    ponto("trabalho_5", "trabalho", 88, 166, "baixo")
    ponto("trabalho_6", "trabalho", 120, 166, "baixo")

    def camada(id_, nome, grade):
        return {
            "id": id_,
            "name": nome,
            "type": "tilelayer",
            "width": L,
            "height": A,
            "x": 0,
            "y": 0,
            "opacity": 1,
            "visible": True,
            "data": [v for linha in grade for v in linha],
        }

    linhas = (len(TILES) + COLUNAS_TILESET - 1) // COLUNAS_TILESET
    mapa = {
        "type": "map",
        "version": "1.10",
        "tiledversion": "1.10.2",
        "orientation": "orthogonal",
        "renderorder": "right-down",
        "infinite": False,
        "width": L,
        "height": A,
        "tilewidth": 16,
        "tileheight": 16,
        "compressionlevel": -1,
        "nextlayerid": 4,
        "nextobjectid": len(objetos) + 1,
        "layers": [
            camada(1, "piso", piso),
            camada(2, "obstaculos", obs),
            {
                "id": 3,
                "name": "objetos",
                "type": "objectgroup",
                "draworder": "topdown",
                "opacity": 1,
                "visible": True,
                "x": 0,
                "y": 0,
                "objects": objetos,
            },
        ],
        "tilesets": [
            {
                "firstgid": 1,
                "name": "escritorio",
                "image": "tileset.png",
                "imagewidth": 16 * COLUNAS_TILESET,
                "imageheight": 16 * linhas,
                "tilewidth": 16,
                "tileheight": 16,
                "tilecount": len(TILES),
                "columns": COLUNAS_TILESET,
                "margin": 0,
                "spacing": 0,
            }
        ],
    }
    return mapa, piso, obs


def renderizar_mapa(piso, obs, imagens):
    nomes = {i + 1: nome for i, (nome, _) in enumerate(TILES)}
    t = Tela(L * 16, A * 16)
    for grade in (piso, obs):
        for y in range(A):
            for x in range(L):
                if grade[y][x]:
                    t.colar(imagens[nomes[grade[y][x]]], x * 16, y * 16)
    return t


# ---------------------------------------------------------------- atlas


def gerar_atlas(quadros):
    colunas = 9
    linhas = (len(quadros) + colunas - 1) // colunas
    atlas = Tela(32 * colunas, 48 * linhas)
    frames = {}
    for i, (nome, tela) in enumerate(quadros):
        x, y = (i % colunas) * 32, (i // colunas) * 48
        atlas.colar(tela, x, y)
        frames[nome] = {
            "frame": {"x": x, "y": y, "w": 32, "h": 48},
            "rotated": False,
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": 32, "h": 48},
            "sourceSize": {"w": 32, "h": 48},
        }
    dados = {
        "frames": frames,
        "meta": {
            "image": "atlas.png",
            "size": {"w": atlas.w, "h": atlas.h},
            "scale": "1",
            "app": "web/tools/gerar_assets.py",
        },
    }
    return atlas, dados


def prancha_revisao(neto, pistori, ret_neto, ret_pistori, carpete):
    """Neto e Pistori lado a lado: sprites x6, retratos x2, e na escala do mapa (x2 e x1)."""
    t = Tela(960, 520)
    t.ret(0, 0, 959, 519, cor("#0e1218"))
    t.ret(24, 24, 456, 336, cor("#151b24"))
    t.colar(neto, 40, 40, 6)
    t.colar(pistori, 248, 40, 6)
    t.ret(480, 24, 936, 248, cor("#151b24"))
    t.colar(ret_neto, 496, 40, 2)
    t.colar(ret_pistori, 720, 40, 2)
    for ty in range(4):
        for tx in range(12):
            t.colar(carpete, 24 + tx * 32, 360 + ty * 32, 2)
    t.colar(neto, 24 + 112, 360 + 128 - 96 - 6, 2)
    t.colar(pistori, 24 + 200, 360 + 128 - 96 - 6, 2)
    for ty in range(4):
        for tx in range(10):
            t.colar(carpete, 432 + tx * 16, 392 + ty * 16, 1)
    t.colar(neto, 432 + 48, 392 + 64 - 48 - 3, 1)
    t.colar(pistori, 432 + 88, 392 + 64 - 48 - 3, 1)
    t.ret(624, 272, 936, 496, cor("#151b24"))
    t.colar(ret_neto, 656, 336, 1)
    t.colar(ret_pistori, 800, 336, 1)
    return t


# ---------------------------------------------------------------- principal


def main():
    tileset, imagens = gerar_tileset()
    mapa, piso, obs = gerar_mapa()
    pasta_mapa = JOGO / "mapas" / "recepcao_padrao"
    salvar_png(pasta_mapa / "tileset.png", tileset)
    salvar_json(pasta_mapa / "mapa.json", mapa)
    salvar_png(pasta_mapa / "previa.png", renderizar_mapa(piso, obs, imagens))
    salvar_json(
        JOGO / "mapas" / "manifesto.json",
        {
            "padrao": "recepcao_padrao",
            "templates": [
                {
                    "id": "recepcao_padrao",
                    "versao": "1.0.0",
                    "nome": "Recepção, reunião e trabalho",
                    "arquivo_mapa": "recepcao_padrao/mapa.json",
                    "tileset": "recepcao_padrao/tileset.png",
                    "nome_tileset": "escritorio",
                    "previa": "recepcao_padrao/previa.png",
                    "licenca": LICENCA_ARTE,
                }
            ],
        },
    )

    neto, pistori = sprite_neto(), sprite_pistori()
    ret_neto, ret_pistori = retrato_neto(), retrato_pistori()
    pasta_av = JOGO / "avatares"
    quadros = [("neto_baixo", neto), ("pistori_baixo", pistori)]
    avatares = []
    for avatar_id, nome, roupa in ELENCO:
        linhas, paleta = SIMBOLOS[avatar_id]
        simbolo = Tela(7, 7)
        simbolo.icone(linhas, paleta, 0, 0)
        salvar_png(pasta_av / "simbolos" / f"{avatar_id}.png", simbolo)
        if roupa is None:
            retrato = ret_neto if avatar_id == "neto" else ret_pistori
            arte, quadro = "em_revisao", f"{avatar_id}_baixo"
        else:
            retrato = retrato_placeholder(avatar_id, roupa)
            arte, quadro = "placeholder", f"placeholder_{avatar_id}"
            quadros.append((quadro, sprite_placeholder(avatar_id, roupa)))
        salvar_png(pasta_av / "retratos" / f"{avatar_id}.png", retrato)
        avatares.append(
            {
                "avatar_id": avatar_id,
                "nome": nome,
                "arte": arte,
                "retrato": f"retratos/{avatar_id}.png",
                "simbolo": f"simbolos/{avatar_id}.png",
                "quadros": {"baixo": quadro},
                "animacoes": [],
            }
        )
    quadros.append(("placeholder_generico", sprite_placeholder("", cor("#5d6678"))))
    atlas, dados_atlas = gerar_atlas(quadros)
    salvar_png(pasta_av / "atlas.png", atlas)
    salvar_json(pasta_av / "atlas.json", dados_atlas)
    salvar_json(
        pasta_av / "manifesto.json",
        {
            "versao": "0.1.0",
            "quadro": {"largura": 32, "altura": 48, "apoio": {"x": 16, "y": 45}},
            "retrato": {"largura": 96, "altura": 96},
            "atlas": {"imagem": "atlas.png", "dados": "atlas.json"},
            "licenca": LICENCA_ARTE,
            "padrao": {"quadros": {"baixo": "placeholder_generico"}},
            "avatares": avatares,
        },
    )

    salvar_png(
        DOCS_ARTE / "revisao_neto_pistori.png",
        prancha_revisao(neto, pistori, ret_neto, ret_pistori, imagens["carpete"]),
    )
    print(f"Assets gerados em {JOGO.relative_to(WEB.parent)} e {DOCS_ARTE.relative_to(WEB.parent)}")


if __name__ == "__main__":
    main()
