import Phaser from "phaser";
import { useEffect, useRef } from "react";

import {
  BASE_AVATARES,
  Direcao,
  COR_SELECAO,
  ESTADO_COR,
  ManifestoAvatares,
  quadroDoAvatar,
} from "./avatares";
import { BASE_MAPAS, TemplateMapa } from "./mapas";

export type AvatarSala = {
  agente_id: number;
  avatar_id: string;
  nome: string;
  homenagem: string;
  especialidade: string;
  direcao_arte?: string;
  referencia_visual?: string;
  estado: string;
};

type Props = {
  template: TemplateMapa;
  manifesto: ManifestoAvatares;
  avatares: AvatarSala[];
  selecionadoId: number | null;
  onSelecionarAvatar: (avatar: AvatarSala) => void;
};

type Ponto = { x: number; y: number; direcao: Direcao };

const ESTADOS_EM_REUNIAO = new Set(["convocado", "em_andamento", "aguardando_revisao"]);

function lerPonto(obj: Phaser.Types.Tilemaps.TiledObject): Ponto {
  const props = (obj.properties ?? []) as { name: string; value: unknown }[];
  const direcao = (props.find((p) => p.name === "direcao")?.value as Direcao) ?? "baixo";
  return { x: obj.x ?? 0, y: obj.y ?? 0, direcao };
}

/**
 * Posiciona os avatares a partir dos pontos genéricos do mapa: Neto na mesa de
 * reunião; agentes com turno ativo nos assentos; os demais nos postos de trabalho.
 * Só os dados do mapa definem coordenadas — a lógica não conhece o layout.
 */
function distribuir(avatares: AvatarSala[], objetos: Phaser.Types.Tilemaps.TiledObject[]) {
  const porTipo = (tipo: string) =>
    objetos
      .filter((o) => o.type === tipo)
      .sort((a, b) => (a.name ?? "").localeCompare(b.name ?? "", undefined, { numeric: true }))
      .map(lerPonto);
  const mesa = porTipo("mesa_reuniao")[0];
  const assentos = porTipo("assento_reuniao");
  const trabalho = porTipo("trabalho");
  const entrada = porTipo("entrada")[0] ?? { x: 32, y: 32, direcao: "baixo" as Direcao };

  let excedentes = 0;
  return avatares.map((avatar) => {
    let ponto: Ponto | undefined;
    if (avatar.avatar_id === "neto" && mesa) ponto = mesa;
    else if (ESTADOS_EM_REUNIAO.has(avatar.estado)) ponto = assentos.shift() ?? trabalho.shift();
    else ponto = trabalho.shift() ?? assentos.shift();
    if (!ponto) {
      ponto = { x: entrada.x + 24 * (excedentes + 1), y: entrada.y - 6, direcao: "baixo" };
      excedentes += 1;
    }
    return { avatar, ponto };
  });
}

class CenaSala extends Phaser.Scene {
  private mapa!: Phaser.Tilemaps.Tilemap;
  private aneisSelecao = new Map<number, Phaser.GameObjects.Ellipse>();

  constructor(
    private readonly props: Props,
    private readonly container: HTMLElement
  ) {
    super("sala");
  }

  preload() {
    const { template, manifesto } = this.props;
    this.load.tilemapTiledJSON(`mapa:${template.id}`, `${BASE_MAPAS}/${template.arquivo_mapa}`);
    this.load.image(`tiles:${template.id}`, `${BASE_MAPAS}/${template.tileset}`);
    this.load.atlas(
      "avatares",
      `${BASE_AVATARES}/${manifesto.atlas.imagem}`,
      `${BASE_AVATARES}/${manifesto.atlas.dados}`
    );
  }

  create() {
    const { template, manifesto, avatares } = this.props;
    this.mapa = this.make.tilemap({ key: `mapa:${template.id}` });
    const tileset = this.mapa.addTilesetImage(template.nome_tileset, `tiles:${template.id}`);
    if (!tileset) throw new Error(`Tileset ${template.nome_tileset} ausente no mapa ${template.id}`);
    this.mapa.createLayer("piso", tileset, 0, 0)?.setDepth(0);
    this.mapa.createLayer("obstaculos", tileset, 0, 0)?.setDepth(1);

    const zoom = this.ajustarTamanho();
    const resolucao = Math.max(zoom, 1) * (window.devicePixelRatio || 1);
    // Tamanho em unidades do mapa que vira pelo menos ~10–11 px na tela, em qualquer zoom.
    const tamanho = (minimo: number, telaPx: number) => `${Math.max(minimo, telaPx / zoom)}px`;
    const objetos = this.mapa.getObjectLayer("objetos")?.objects ?? [];

    for (const area of objetos.filter((o) => o.type === "area")) {
      const rotulo = this.add
        .text((area.x ?? 0) + (area.width ?? 0) / 2, (area.y ?? 0) + 3, (area.name ?? "").toUpperCase(), {
          fontFamily: "system-ui, sans-serif",
          fontSize: tamanho(5.5, 10),
          fontStyle: "600",
          color: "#c9d3e0",
          resolution: resolucao,
          padding: { top: 2, bottom: 1 },
        })
        .setOrigin(0.5, 0)
        .setDepth(2000);
      const fundo = this.add
        .rectangle(rotulo.x, rotulo.y - 1, rotulo.width + 8, rotulo.height + 2, 0x0e1218, 0.55)
        .setOrigin(0.5, 0)
        .setDepth(1999);
      fundo.setStrokeStyle(0.5, 0x3a4660, 0.8);
    }

    const { apoio, largura, altura } = manifesto.quadro;
    for (const { avatar, ponto } of distribuir(avatares, objetos)) {
      const corEstado = ESTADO_COR[avatar.estado] ?? ESTADO_COR.disponivel;
      const anel = this.add
        .ellipse(ponto.x, ponto.y, 24, 8)
        .setFillStyle(corEstado, 0.22)
        .setStrokeStyle(1, corEstado, 0.95)
        .setDepth(5 + ponto.y);
      if (avatar.estado === "em_andamento") {
        this.tweens.add({ targets: anel, alpha: 0.35, duration: 700, yoyo: true, repeat: -1 });
      }
      const selecao = this.add
        .ellipse(ponto.x, ponto.y, 31, 12)
        .setStrokeStyle(1.6, COR_SELECAO, 1)
        .setDepth(5 + ponto.y)
        .setVisible(avatar.agente_id === this.props.selecionadoId);
      this.aneisSelecao.set(avatar.agente_id, selecao);

      const sprite = this.add
        .sprite(ponto.x, ponto.y, "avatares", quadroDoAvatar(manifesto, avatar.avatar_id, ponto.direcao))
        .setOrigin(apoio.x / largura, apoio.y / altura)
        .setDepth(10 + ponto.y)
        .setInteractive({ useHandCursor: true });
      sprite.on("pointerover", () => sprite.setTint(0xe4ecff));
      sprite.on("pointerout", () => sprite.clearTint());
      sprite.on("pointerdown", () => this.props.onSelecionarAvatar(avatar));

      const topo = ponto.y - apoio.y - 3;
      const nome = this.add
        .text(ponto.x + 3, topo, avatar.nome, {
          fontFamily: "system-ui, sans-serif",
          fontSize: tamanho(6.5, 11),
          fontStyle: "600",
          color: "#f3f6fa",
          resolution: resolucao,
          padding: { top: 2, bottom: 1 },
        })
        .setOrigin(0.5, 1)
        .setDepth(3000);
      const placa = this.add
        .rectangle(ponto.x, topo + 1, nome.width + 13, nome.height + 2, 0x0e1218, 0.78)
        .setOrigin(0.5, 1)
        .setDepth(2999);
      placa.setStrokeStyle(0.6, corEstado, 0.9);
      this.add
        .circle(ponto.x - nome.width / 2 - 1.5, topo - nome.height / 2 + 0.5, 1.8, corEstado)
        .setDepth(3001);
    }

    // Recalcula quando o card muda de largura (layout tardio, painel abrindo, janela redimensionada).
    const observador = new ResizeObserver(() => this.ajustarTamanho());
    observador.observe(this.container);
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => observador.disconnect());
  }

  marcarSelecionado(id: number | null) {
    this.aneisSelecao.forEach((anel, agenteId) => anel.setVisible(agenteId === id));
  }

  private ajustarTamanho(): number {
    const mapaW = this.mapa.widthInPixels;
    const mapaH = this.mapa.heightInPixels;
    const disponivel = Math.max(1, this.container.clientWidth);
    // Sempre escala inteira (pixels nítidos). Em tela estreita fica em 1x e o card rola na horizontal.
    const zoom = Math.max(1, Math.floor(disponivel / mapaW));
    this.container.classList.toggle("estreita", disponivel < mapaW);
    if (this.scale.width === mapaW * zoom && this.cameras.main.zoom === zoom) return zoom;
    this.scale.resize(mapaW * zoom, mapaH * zoom);
    this.cameras.main.setZoom(zoom).centerOn(mapaW / 2, mapaH / 2);
    return zoom;
  }
}

/**
 * Sala Phaser incorporada ao React (Entrega 4). O componente é remontado pelo
 * pai quando o template ou os estados mudam; a seleção é atualizada sem remontar.
 */
export function SalaPhaser(props: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cenaRef = useRef<CenaSala | null>(null);
  const propsRef = useRef(props);
  propsRef.current = props;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const cena = new CenaSala(
      {
        ...propsRef.current,
        onSelecionarAvatar: (avatar) => propsRef.current.onSelecionarAvatar(avatar),
      },
      container
    );
    cenaRef.current = cena;
    const jogo = new Phaser.Game({
      type: Phaser.AUTO,
      parent: container,
      width: container.clientWidth || 448,
      height: Math.round(((container.clientWidth || 448) * 272) / 448),
      backgroundColor: "#121821",
      pixelArt: true,
      roundPixels: true,
      scene: cena,
    });
    return () => {
      cenaRef.current = null;
      jogo.destroy(true);
    };
  }, []);

  useEffect(() => {
    cenaRef.current?.marcarSelecionado(props.selecionadoId);
  }, [props.selecionadoId]);

  return <div ref={containerRef} className="sala-canvas" aria-label="Sala 2D do projeto" />;
}
