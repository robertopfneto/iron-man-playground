import { FormEvent, useEffect, useRef, useState } from "react";

import { api } from "./api";
import { ESTADO_LABEL } from "./room/avatares";

type AgenteProjeto = { agente_id: number; nome: string };

type Evidencia = {
  repositorio: string;
  caminho: string;
  secao: string;
  linhas: string;
  commit: string;
  link: string;
  origem: string;
};

type RespostaMensagem =
  | { tipo: "duvida_simples"; resposta: string }
  | { tipo: "resposta_direta"; resposta: string }
  | { tipo: "resposta_documentada"; resposta: string; evidencias: Evidencia[]; avisos: string[] }
  | { tipo: "sem_evidencia"; resposta: string; avisos: string[] }
  | {
      tipo: "proposta_convocacao";
      convocacao_id: number;
      prompt_copiavel: string;
      agentes_sugeridos: number[];
    }
  | { tipo: "limite_atingido" };

type Turno = { id: number; agente_id: number; agente: string; situacao: string; resultado: string; autoria: string };
type Convocacao = { id: number; situacao: string; tarefa: string; turnos: Turno[] };

type Item =
  | { tipo: "usuario"; texto: string }
  | { tipo: "neto"; texto: string }
  | { tipo: "prompt"; texto: string }
  | { tipo: "evidencias"; lista: Evidencia[]; avisos: string[] };

type Props = {
  conversaId: number;
  agentesDoProjeto: AgenteProjeto[];
  aoAtualizarSala: () => void;
};

export function ChatNeto({ conversaId, agentesDoProjeto, aoAtualizarSala }: Props) {
  const [pedido, setPedido] = useState("");
  const [historico, setHistorico] = useState<Item[]>([]);
  const [convocacao, setConvocacao] = useState<Convocacao | null>(null);
  const [agentesEscolhidos, setAgentesEscolhidos] = useState<Set<number>>(new Set());
  const [rascunhoResultado, setRascunhoResultado] = useState<Record<number, string>>({});
  const [enviando, setEnviando] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const fimRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [historico]);

  async function enviarMensagem(e: FormEvent) {
    e.preventDefault();
    if (!pedido.trim() || enviando) return;
    const texto = pedido;
    setPedido("");
    setEnviando(true);
    setHistorico((h) => [...h, { tipo: "usuario", texto }]);

    try {
      const resp = await api<RespostaMensagem>(`/conversas/${conversaId}/mensagens`, {
        method: "POST",
        body: JSON.stringify({ conteudo: texto }),
      });

      if (resp.tipo === "duvida_simples" || resp.tipo === "resposta_direta") {
        setHistorico((h) => [...h, { tipo: "neto", texto: resp.resposta }]);
        return;
      }
      if (resp.tipo === "resposta_documentada") {
        const corpo = resp.resposta.split("\nFontes:")[0].trim();
        setHistorico((h) => [
          ...h,
          { tipo: "neto", texto: corpo },
          { tipo: "evidencias", lista: resp.evidencias, avisos: resp.avisos },
        ]);
        return;
      }
      if (resp.tipo === "sem_evidencia") {
        setHistorico((h) => [...h, { tipo: "neto", texto: resp.resposta }]);
        return;
      }
      if (resp.tipo === "limite_atingido") {
        setHistorico((h) => [
          ...h,
          { tipo: "neto", texto: "Há convocações demais abertas neste projeto. Conclua alguma antes de abrir outra." },
        ]);
        return;
      }

      setHistorico((h) => [
        ...h,
        { tipo: "neto", texto: "Isso pede especialistas. Preparei a triagem abaixo — confirme quem convocar." },
        { tipo: "prompt", texto: resp.prompt_copiavel },
      ]);
      setAgentesEscolhidos(new Set(resp.agentes_sugeridos));
      setConvocacao(await api<Convocacao>(`/convocacoes/${resp.convocacao_id}`));
    } catch (falha) {
      setHistorico((h) => [...h, { tipo: "neto", texto: `Não consegui processar: ${(falha as Error).message}` }]);
    } finally {
      setEnviando(false);
    }
  }

  function alternarAgente(id: number) {
    setAgentesEscolhidos((atual) => {
      const novo = new Set(atual);
      if (novo.has(id)) novo.delete(id);
      else novo.add(id);
      return novo;
    });
  }

  async function copiar(texto: string) {
    await navigator.clipboard.writeText(texto);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1500);
  }

  async function confirmarConvocacao() {
    if (!convocacao || agentesEscolhidos.size === 0) return;
    const resp = await api<{ id: number }>(`/convocacoes/${convocacao.id}/confirmar`, {
      method: "POST",
      body: JSON.stringify({ agentes_ids: Array.from(agentesEscolhidos) }),
    });
    setConvocacao(await api<Convocacao>(`/convocacoes/${resp.id}`));
    aoAtualizarSala();
  }

  async function registrarResultado(turnoId: number) {
    const resultado = rascunhoResultado[turnoId] || "";
    if (!resultado.trim() || !convocacao) return;
    await api(`/turnos/${turnoId}/resultado`, {
      method: "POST",
      body: JSON.stringify({ resultado, autoria: "usuario" }),
    });
    const detalhe = await api<Convocacao>(`/convocacoes/${convocacao.id}`);
    setConvocacao(detalhe);
    if (detalhe.situacao === "concluida") {
      setHistorico((h) => [
        ...h,
        { tipo: "neto", texto: "Todos os turnos foram fechados. A decisão está proposta na lateral para sua aprovação." },
      ]);
    }
    aoAtualizarSala();
  }

  return (
    <section className="card chat" aria-label="Chat com Neto">
      <div className="card-titulo">
        <h2>Neto · coordenação</h2>
        <span className="meta">modo manual</span>
      </div>

      <div className="chat-mensagens">
        {historico.length === 0 && (
          <p className="vazio">
            Fale com Neto sobre este projeto. Perguntas simples são respondidas direto; pedidos de mudança viram uma
            convocação de especialistas.
          </p>
        )}
        {historico.map((item, i) =>
          item.tipo === "evidencias" ? (
            <div key={i} className="evidencias" aria-label="Fontes consultadas">
              <span className="bolha-autor">Fontes consultadas</span>
              <ul>
                {item.lista.map((e, j) => (
                  <li key={j}>
                    {e.link.startsWith("https://") ? (
                      <a href={e.link} target="_blank" rel="noreferrer">
                        {e.secao}
                      </a>
                    ) : (
                      <span>{e.secao}</span>
                    )}
                    <code>
                      {e.repositorio}/{e.caminho} {e.linhas} @ {e.commit.slice(0, 12)}
                    </code>
                    {e.origem === "relacao" && <span className="badge st-concluido">relacionado</span>}
                  </li>
                ))}
              </ul>
              {item.avisos.map((a, j) => (
                <p key={j} className="aviso">
                  {a}
                </p>
              ))}
            </div>
          ) : item.tipo === "prompt" ? (
            <div key={i} className="prompt-copiavel">
              <div className="topo">
                <span>Prompt para triagem manual</span>
                <button className="btn btn-ghost btn-sm" type="button" onClick={() => copiar(item.texto)}>
                  {copiado ? "Copiado" : "Copiar"}
                </button>
              </div>
              {item.texto}
            </div>
          ) : (
            <div key={i} className={`bolha ${item.tipo === "usuario" ? "bolha-usuario" : "bolha-neto"}`}>
              {item.tipo === "neto" && <span className="bolha-autor">Neto</span>}
              {item.texto}
            </div>
          )
        )}
        <div ref={fimRef} />
      </div>

      {convocacao && convocacao.situacao === "proposta" && (
        <div className="painel">
          <h3>Convocar especialistas</h3>
          <div className="chips">
            {agentesDoProjeto
              .filter((a) => a.nome !== "Neto")
              .map((a) => (
                <button
                  key={a.agente_id}
                  type="button"
                  className="chip"
                  aria-pressed={agentesEscolhidos.has(a.agente_id)}
                  onClick={() => alternarAgente(a.agente_id)}
                >
                  {a.nome}
                </button>
              ))}
          </div>
          <button className="btn" onClick={confirmarConvocacao} disabled={agentesEscolhidos.size === 0}>
            Confirmar convocação
          </button>
        </div>
      )}

      {convocacao && convocacao.situacao !== "proposta" && (
        <div className="painel">
          <h3>Convocação #{convocacao.id}</h3>
          {convocacao.turnos.map((t) => (
            <div key={t.id} className="turno">
              <div className="turno-topo">
                {t.agente}
                <span className={`badge st-${t.situacao}`}>{ESTADO_LABEL[t.situacao] ?? t.situacao}</span>
              </div>
              {t.situacao !== "concluido" ? (
                <>
                  <textarea
                    className="field"
                    aria-label={`Resultado de ${t.agente}`}
                    placeholder="Cole aqui a entrega deste especialista..."
                    value={rascunhoResultado[t.id] || ""}
                    onChange={(e) => setRascunhoResultado((r) => ({ ...r, [t.id]: e.target.value }))}
                  />
                  <button
                    className="btn btn-sm"
                    onClick={() => registrarResultado(t.id)}
                    disabled={!(rascunhoResultado[t.id] || "").trim()}
                  >
                    Fechar turno
                  </button>
                </>
              ) : (
                <p>{t.resultado}</p>
              )}
            </div>
          ))}
        </div>
      )}

      <form className="chat-entrada" onSubmit={enviarMensagem}>
        <input
          className="field"
          aria-label="Mensagem para Neto"
          value={pedido}
          onChange={(e) => setPedido(e.target.value)}
          placeholder="Escreva para Neto..."
        />
        <button className="btn" type="submit" disabled={enviando || !pedido.trim()}>
          Enviar
        </button>
      </form>
    </section>
  );
}
