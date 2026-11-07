/**
 * Manifesto de templates de mapa (Entrega 4B). Dados separados do código da
 * cena Phaser, como pede o plano. No MVP, um template local é suficiente;
 * V1/V2 (loja de mapas, criação de espaços) ficam para depois do piloto.
 */

export type PontoMapa = { x: number; y: number };

export type TemplateMapa = {
  id: string;
  versao: string;
  nome: string;
  licenca: string;
  largura: number;
  altura: number;
  pontoEntrada: PontoMapa;
  pontoMesaReuniao: PontoMapa;
  pontosTrabalho: PontoMapa[];
};

export const TEMPLATE_PADRAO_ID = "recepcao_padrao";

const TEMPLATES: Record<string, TemplateMapa> = {
  [TEMPLATE_PADRAO_ID]: {
    id: TEMPLATE_PADRAO_ID,
    versao: "1.0.0",
    nome: "Recepção padrão",
    licenca: "Elementos próprios simples (placeholder geométrico, sem asset de terceiros).",
    largura: 800,
    altura: 480,
    pontoEntrada: { x: 80, y: 420 },
    pontoMesaReuniao: { x: 400, y: 160 },
    pontosTrabalho: [
      { x: 620, y: 120 },
      { x: 680, y: 220 },
      { x: 620, y: 320 },
      { x: 520, y: 380 },
      { x: 180, y: 260 },
    ],
  },
};

export function resolverTemplate(templateId?: string | null): TemplateMapa {
  if (templateId && TEMPLATES[templateId]) {
    return TEMPLATES[templateId];
  }
  return TEMPLATES[TEMPLATE_PADRAO_ID];
}
