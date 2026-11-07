import Phaser from "phaser";
import { useEffect, useRef } from "react";

import { corParaAvatar, ESTADO_LABEL, simboloParaAvatar } from "./avatares";
import { TemplateMapa } from "./mapas";

export type AvatarSala = {
  agente_id: number;
  avatar_id: string;
  nome: string;
  homenagem: string;
  especialidade: string;
  estado: string;
};

type Props = {
  template: TemplateMapa;
  avatares: AvatarSala[];
  onSelecionarAvatar: (avatar: AvatarSala) => void;
};

/**
 * Sala Phaser incorporada ao React (Entrega 4). Recebe o layout a partir do
 * template_id (mapas.ts) e os avatares reais vindos da API. Avatares usam
 * placeholders geométricos (Entrega 4A) até a arte definitiva ser produzida.
 */
export function SalaPhaser({ template, avatares, onSelecionarAvatar }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    class CenaSala extends Phaser.Scene {
      create() {
        this.cameras.main.setBackgroundColor("#1d2733");
        this.add
          .rectangle(template.largura / 2, template.altura / 2, template.largura - 20, template.altura - 20, 0x24324a)
          .setStrokeStyle(2, 0x3c5375);

        this.add
          .text(template.pontoMesaReuniao.x, template.pontoMesaReuniao.y - 40, "Mesa de reunião", {
            fontSize: "12px",
            color: "#9fb3c8",
          })
          .setOrigin(0.5);
        this.add
          .rectangle(template.pontoMesaReuniao.x, template.pontoMesaReuniao.y, 120, 50, 0x16202c)
          .setStrokeStyle(1, 0x3c5375);
        this.add
          .text(template.pontoEntrada.x, template.pontoEntrada.y - 20, "Entrada", {
            fontSize: "12px",
            color: "#9fb3c8",
          })
          .setOrigin(0.5);

        const posicoes = [template.pontoMesaReuniao, ...template.pontosTrabalho];
        avatares.forEach((avatar, indice) => {
          const ponto = posicoes[indice % posicoes.length];
          const cor = corParaAvatar(avatar.avatar_id);

          const circulo = this.add.circle(ponto.x, ponto.y, 22, cor).setStrokeStyle(2, 0xffffff);
          circulo.setInteractive({ useHandCursor: true });
          circulo.on("pointerdown", () => onSelecionarAvatar(avatar));

          this.add
            .text(ponto.x, ponto.y, simboloParaAvatar(avatar.nome), { fontSize: "18px", color: "#ffffff" })
            .setOrigin(0.5);
          this.add
            .text(ponto.x, ponto.y + 32, avatar.nome, { fontSize: "12px", color: "#e8edf2" })
            .setOrigin(0.5);
          this.add
            .text(ponto.x, ponto.y + 46, ESTADO_LABEL[avatar.estado] ?? avatar.estado, {
              fontSize: "10px",
              color: "#9fb3c8",
            })
            .setOrigin(0.5);
        });
      }
    }

    const jogo = new Phaser.Game({
      type: Phaser.AUTO,
      parent: containerRef.current,
      width: template.largura,
      height: template.altura,
      backgroundColor: "#1d2733",
      scene: CenaSala,
    });

    return () => {
      jogo.destroy(true);
    };
    // O componente é remontado via `key` no pai quando template/avatares mudam.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={containerRef} />;
}
