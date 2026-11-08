import { KeyboardEvent, useState } from "react";

import { BASE_AVATARES, buscarAvatar, ESTADO_LABEL, ManifestoAvatares } from "./room/avatares";
import { AvatarSala } from "./room/SalaPhaser";

/* ------------------------------------------------------------ estados */

export function IconeEstado({ estado }: { estado: string }) {
  const comum = { width: 14, height: 14, viewBox: "0 0 14 14", "aria-hidden": true } as const;
  switch (estado) {
    case "convocado":
      return (
        <svg {...comum} fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round">
          <path d="M7 2.2a3.2 3.2 0 0 0-3.2 3.2v2.3L2.7 9.6h8.6L10.2 7.7V5.4A3.2 3.2 0 0 0 7 2.2Z" />
          <path d="M5.8 11.2a1.3 1.3 0 0 0 2.4 0" strokeLinecap="round" />
        </svg>
      );
    case "em_andamento":
      return (
        <svg {...comum} fill="currentColor">
          <path d="M4.5 3v8l6.5-4z" />
        </svg>
      );
    case "aguardando_revisao":
      return (
        <svg {...comum} fill="none" stroke="currentColor" strokeWidth="1.4">
          <path d="M1.3 7S3.4 3.4 7 3.4 12.7 7 12.7 7 10.6 10.6 7 10.6 1.3 7 1.3 7Z" />
          <circle cx="7" cy="7" r="1.7" />
        </svg>
      );
    case "concluido":
      return (
        <svg
          {...comum}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M2.8 7.4 5.6 10l5.6-6" />
        </svg>
      );
    default:
      return (
        <svg {...comum} fill="none" stroke="currentColor" strokeWidth="1.4">
          <circle cx="7" cy="7" r="4.2" />
        </svg>
      );
  }
}

export function Estado({ estado }: { estado: string }) {
  return (
    <span className={`estado st-${estado}`}>
      <IconeEstado estado={estado} />
      {ESTADO_LABEL[estado] ?? estado}
    </span>
  );
}

/* ------------------------------------------------------------ equipe */

type EquipeProps = {
  avatares: AvatarSala[];
  manifesto: ManifestoAvatares | null;
  selecionadoId: number | null;
  onSelecionar: (agenteId: number) => void;
};

export function Equipe({ avatares, manifesto, selecionadoId, onSelecionar }: EquipeProps) {
  function navegar(e: KeyboardEvent<HTMLUListElement>) {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    const botoes = Array.from(e.currentTarget.querySelectorAll<HTMLButtonElement>("button.membro"));
    const atual = botoes.indexOf(document.activeElement as HTMLButtonElement);
    const proximo = e.key === "ArrowDown" ? Math.min(atual + 1, botoes.length - 1) : Math.max(atual - 1, 0);
    botoes[proximo]?.focus();
    e.preventDefault();
  }

  return (
    <section className="card" aria-labelledby="titulo-equipe">
      <div className="card-titulo">
        <h2 id="titulo-equipe">Equipe</h2>
        <span className="meta">{avatares.length} no projeto</span>
      </div>
      <ul className="equipe" onKeyDown={navegar} id="lista-equipe">
        {avatares.map((a) => {
          const arte = buscarAvatar(manifesto, a.avatar_id);
          return (
            <li key={a.agente_id}>
              <button
                className="membro"
                aria-pressed={a.agente_id === selecionadoId}
                onClick={() => onSelecionar(a.agente_id)}
              >
                {arte ? <img className="pixel" src={`${BASE_AVATARES}/${arte.simbolo}`} alt="" /> : <span />}
                <span className="nome">{a.nome}</span>
                <Estado estado={a.estado} />
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/* ------------------------------------------------------------ atividades */

export type TurnoAberto = { id: number; agente_id: number; agente: string; situacao: string; resultado: string };
export type ConvocacaoAberta = { id: number; tarefa: string; turnos: TurnoAberto[] };
export type Decisao = { id: number; texto: string; situacao: string };

type AtividadesProps = {
  convocacoes: ConvocacaoAberta[];
  decisoes: Decisao[];
  onFecharTurno: (turnoId: number, resultado: string) => Promise<void>;
  onAprovar: (decisaoId: number) => Promise<void>;
  onConversar: () => void;
};

export function Atividades({ convocacoes, decisoes, onFecharTurno, onAprovar, onConversar }: AtividadesProps) {
  const [rascunhos, setRascunhos] = useState<Record<number, string>>({});
  const turnosPendentes = convocacoes.flatMap((c) =>
    c.turnos.filter((t) => t.situacao !== "concluido").map((t) => ({ ...t, tarefa: c.tarefa }))
  );
  const propostas = decisoes.filter((d) => d.situacao === "proposta");
  const pendentes = turnosPendentes.length + propostas.length;
  const concluidas = decisoes
    .filter((d) => d.situacao === "aprovada")
    .slice(-3)
    .reverse();

  let passo: { texto: string; acao: { rotulo: string; fazer: () => void } };
  if (turnosPendentes.length > 0) {
    const t = turnosPendentes[0];
    passo = {
      texto: `Cole o resultado de ${t.agente} para fechar o turno.`,
      acao: { rotulo: "Ir para o cartão", fazer: () => document.getElementById(`resultado-${t.id}`)?.focus() },
    };
  } else if (propostas.length > 0) {
    passo = {
      texto: "Revise a decisão proposta e aprove se estiver de acordo.",
      acao: { rotulo: "Ver decisão", fazer: () => document.getElementById(`decisao-${propostas[0].id}`)?.focus() },
    };
  } else {
    passo = {
      texto: "Nada pendente. Converse com Neto para pedir algo à equipe.",
      acao: { rotulo: "Conversar com Neto", fazer: onConversar },
    };
  }

  return (
    <section className="card" aria-labelledby="titulo-atividades">
      <div className="card-titulo">
        <h2 id="titulo-atividades">Atividades</h2>
        <span className="meta">
          {pendentes === 0 ? "nada pendente" : `${pendentes} ${pendentes === 1 ? "pendente" : "pendentes"}`}
        </span>
      </div>

      <div className="proximo-passo" role="status">
        <span className="rotulo-passo">Próximo passo</span>
        <p>{passo.texto}</p>
        <div>
          <button className="btn btn-sm" onClick={passo.acao.fazer}>
            {passo.acao.rotulo}
          </button>
        </div>
      </div>

      <ul className="pendencias">
        {turnosPendentes.map((t) => (
          <li key={`t${t.id}`} className="pendencia">
            <div className="pendencia-topo">
              <span>Turno de {t.agente}</span>
              <Estado estado={t.situacao} />
            </div>
            <p>{t.tarefa}</p>
            <textarea
              id={`resultado-${t.id}`}
              className="field"
              aria-label={`Resultado de ${t.agente}`}
              placeholder="Cole aqui a entrega deste especialista..."
              value={rascunhos[t.id] || ""}
              onChange={(e) => setRascunhos((r) => ({ ...r, [t.id]: e.target.value }))}
            />
            <div className="acoes">
              <button
                className="btn btn-sm"
                disabled={!(rascunhos[t.id] || "").trim()}
                onClick={async () => {
                  await onFecharTurno(t.id, rascunhos[t.id]);
                  setRascunhos((r) => ({ ...r, [t.id]: "" }));
                }}
              >
                Fechar turno
              </button>
            </div>
          </li>
        ))}

        {propostas.map((d) => (
          <li key={`d${d.id}`} className="pendencia" id={`decisao-${d.id}`} tabIndex={-1}>
            <div className="pendencia-topo">
              <span>Decisão proposta</span>
              <span className="estado st-proposta">
                <IconeEstado estado="aguardando_revisao" />
                Aguardando aprovação
              </span>
            </div>
            <p>{d.texto}</p>
            <div className="acoes">
              <button className="btn btn-sm" onClick={() => onAprovar(d.id)}>
                Aprovar decisão
              </button>
            </div>
          </li>
        ))}

        {concluidas.map((d) => (
          <li key={`c${d.id}`} className="pendencia">
            <div className="pendencia-topo">
              <span>Decisão aprovada</span>
              <Estado estado="concluido" />
            </div>
            <p>{d.texto}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
