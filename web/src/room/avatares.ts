/**
 * Placeholders visuais da Entrega 4A. Sem ferramenta de geração de imagem
 * disponível nesta etapa, cada avatar usa uma forma simples (círculo colorido
 * + símbolo = primeira letra do nome) até a arte definitiva (retrato/sprite
 * pixel art) ser produzida em outra ferramenta e substituir este placeholder.
 * Nome, homenagem e especialidade continuam vindo do backend (core.models.Agente).
 */

export function corParaAvatar(avatarId: string): number {
  let hash = 0;
  for (let i = 0; i < avatarId.length; i++) {
    hash = (hash * 31 + avatarId.charCodeAt(i)) & 0xffffff;
  }
  // Garante saturação/luminosidade decentes convertendo para uma paleta fixa.
  const paleta = [0x2a6f97, 0x7a2e8f, 0x1b7a4a, 0x8f5a2e, 0x2e4a8f, 0x8f2e4a, 0x4a8f2e];
  return paleta[hash % paleta.length];
}

export function simboloParaAvatar(nome: string): string {
  return nome.trim().charAt(0).toUpperCase();
}

export const ESTADO_LABEL: Record<string, string> = {
  disponivel: "Disponível",
  convocado: "Convocado",
  em_andamento: "Em andamento",
  aguardando_revisao: "Aguardando revisão",
  concluido: "Concluído",
};
