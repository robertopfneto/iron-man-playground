/**
 * Manifesto de avatares (Entrega 4A): atlas de sprites 32x48, retratos 96x96 e
 * símbolos individuais, gerados por web/tools/gerar_assets.py. O vínculo é feito
 * pelo avatar_id estável de cada agente.
 */

export const BASE_AVATARES = "/jogo/avatares";

export type AvatarManifesto = {
  avatar_id: string;
  nome: string;
  arte: "em_revisao" | "definitiva" | "placeholder";
  retrato: string;
  simbolo: string;
  quadros: Partial<Record<Direcao, string>>;
  animacoes: string[];
};

export type Direcao = "baixo" | "cima" | "esquerda" | "direita";

export type ManifestoAvatares = {
  versao: string;
  quadro: { largura: number; altura: number; apoio: { x: number; y: number } };
  retrato: { largura: number; altura: number };
  atlas: { imagem: string; dados: string };
  licenca: string;
  padrao: { quadros: Partial<Record<Direcao, string>> };
  avatares: AvatarManifesto[];
};

let cache: Promise<ManifestoAvatares> | null = null;

export function carregarManifestoAvatares(): Promise<ManifestoAvatares> {
  if (!cache) {
    cache = fetch(`${BASE_AVATARES}/manifesto.json`).then((r) => {
      if (!r.ok) throw new Error("Manifesto de avatares indisponível");
      return r.json();
    });
  }
  return cache;
}

export function buscarAvatar(manifesto: ManifestoAvatares | null, avatarId: string) {
  return manifesto?.avatares.find((a) => a.avatar_id === avatarId) ?? null;
}

/** Quadro para a direção pedida; enquanto só existe a pose frontal, usa "baixo". */
export function quadroDoAvatar(manifesto: ManifestoAvatares, avatarId: string, direcao: Direcao): string {
  const avatar = buscarAvatar(manifesto, avatarId);
  const quadros = avatar?.quadros ?? manifesto.padrao.quadros;
  return quadros[direcao] ?? quadros.baixo ?? (manifesto.padrao.quadros.baixo as string);
}

export const ESTADO_LABEL: Record<string, string> = {
  disponivel: "Disponível",
  convocado: "Convocado",
  em_andamento: "Em andamento",
  aguardando_revisao: "Aguardando revisão",
  concluido: "Concluído",
};

export const ESTADO_COR: Record<string, number> = {
  disponivel: 0x7d8ea3,
  convocado: 0xf2b84b,
  em_andamento: 0x5b9df5,
  aguardando_revisao: 0xb384f2,
  concluido: 0x46c28e,
};

export const ARTE_LABEL: Record<AvatarManifesto["arte"], string> = {
  em_revisao: "Arte proposta, aguardando revisão",
  definitiva: "Arte definitiva",
  placeholder: "Placeholder até a arte ser produzida",
};
