/**
 * Carregador de templates de mapa (Entrega 4B). Os dados do mapa (Tiled JSON,
 * tileset, pontos e áreas) vivem em public/jogo/mapas, separados da cena Phaser.
 * Gerados por web/tools/gerar_assets.py.
 */

export const BASE_MAPAS = "/jogo/mapas";

export type TemplateMapa = {
  id: string;
  versao: string;
  nome: string;
  arquivo_mapa: string;
  tileset: string;
  nome_tileset: string;
  previa?: string;
  licenca: string;
};

type ManifestoMapas = { padrao: string; templates: TemplateMapa[] };

let cache: Promise<ManifestoMapas> | null = null;

function carregarManifesto(): Promise<ManifestoMapas> {
  if (!cache) {
    cache = fetch(`${BASE_MAPAS}/manifesto.json`).then((r) => {
      if (!r.ok) throw new Error("Manifesto de mapas indisponível");
      return r.json();
    });
  }
  return cache;
}

/** Resolve o template pelo id; id ausente ou desconhecido cai no template padrão. */
export async function resolverTemplate(templateId?: string | null): Promise<TemplateMapa> {
  const manifesto = await carregarManifesto();
  const pedido = manifesto.templates.find((t) => t.id === templateId);
  const padrao = manifesto.templates.find((t) => t.id === manifesto.padrao);
  if (!padrao) throw new Error("Template padrão ausente do manifesto");
  return pedido ?? padrao;
}
