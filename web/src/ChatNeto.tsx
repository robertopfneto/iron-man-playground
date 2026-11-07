import { useState } from "react";

import { api } from "./api";

type AgenteProjeto = { agente_id: number; nome: string };

type RespostaMensagem =
  | { tipo: "duvida_simples"; resposta: string }
  | { tipo: "resposta_direta"; resposta: string }
  | {
      tipo: "proposta_convocacao";
      convocacao_id: number;
      prompt_copiavel: string;
      agentes_sugeridos: number[];
    }
  | { tipo: "limite_atingido" };

type Turno = { id: number; agente_id: number; agente: string; situacao: string; resultado: string; autoria: string };
type Convocacao = { id: number; situacao: string; tarefa: string; turnos: Turno[] };

type Props = {
  projetoId: number;
  conversaId: number;
  agentesDoProjeto: AgenteProjeto[];
  aoAtualizarSala: () => void;
};

export function ChatNeto({ projetoId, conversaId, agentesDoProjeto, aoAtualizarSala }: Props) {
  const [pedido, setPedido] = useState("");
  const [historico, setHistorico] = useState<string[]>([]);
  const [convocacao, setConvocacao] = useState<Convocacao | null>(null);
  const [agentesEscolhidos, setAgentesEscolhidos] = useState<Set<number>>(new Set());
  const [rascunhoResultado, setRascunhoResultado] = useState<Record<number, string>>({});

  async function enviarMensagem() {
    if (!pedido.trim()) return;
    const texto = pedido;
    setPedido("");
    setHistorico((h) => [...h, `Você: ${texto}`]);

    const resp = await api<RespostaMensagem>(`/conversas/${conversaId}/mensagens`, {
      method: "POST",
      body: JSON.stringify({ conteudo: texto }),
    });

    if (resp.tipo === "duvida_simples" || resp.tipo === "resposta_direta") {
      setHistorico((h) => [...h, `Neto: ${resp.resposta}`]);
      return;
    }
    if (resp.tipo === "limite_atingido") {
      setHistorico((h) => [...h, "Neto: limite de convocações abertas atingido neste projeto."]);
      return;
    }

    setHistorico((h) => [...h, `Neto (prompt para triagem manual):\n${resp.prompt_copiavel}`]);
    setAgentesEscolhidos(new Set(resp.agentes_sugeridos));
    const detalhe = await api<Convocacao>(`/convocacoes/${resp.convocacao_id}`);
    setConvocacao(detalhe);
  }

  function alternarAgente(id: number) {
    setAgentesEscolhidos((atual) => {
      const novo = new Set(atual);
      if (novo.has(id)) novo.delete(id);
      else novo.add(id);
      return novo;
    });
  }

  async function confirmarConvocacao() {
    if (!convocacao) return;
    const resp = await api<{ id: number; situacao: string; turnos: number[] }>(
      `/convocacoes/${convocacao.id}/confirmar`,
      { method: "POST", body: JSON.stringify({ agentes_ids: Array.from(agentesEscolhidos) }) }
    );
    const detalhe = await api<Convocacao>(`/convocacoes/${resp.id}`);
    setConvocacao(detalhe);
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
    aoAtualizarSala();
  }

  return (
    <section style={{ border: "1px solid #3c5375", borderRadius: 8, padding: "1rem", marginTop: "1rem" }}>
      <h2 style={{ marginTop: 0 }}>Chat com Neto</h2>
      <div style={{ whiteSpace: "pre-wrap", maxHeight: 200, overflowY: "auto", marginBottom: "0.5rem" }}>
        {historico.map((linha, i) => (
          <p key={i} style={{ margin: "0.25rem 0" }}>
            {linha}
          </p>
        ))}
      </div>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <input
          value={pedido}
          onChange={(e) => setPedido(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && enviarMensagem()}
          placeholder="Fale com Neto sobre este projeto..."
          style={{ flex: 1 }}
        />
        <button onClick={enviarMensagem}>Enviar</button>
      </div>

      {convocacao && convocacao.situacao === "proposta" && (
        <div style={{ marginTop: "1rem" }}>
          <h3>Confirmar convocação</h3>
          {agentesDoProjeto.map((a) => (
            <label key={a.agente_id} style={{ display: "block" }}>
              <input
                type="checkbox"
                checked={agentesEscolhidos.has(a.agente_id)}
                onChange={() => alternarAgente(a.agente_id)}
              />{" "}
              {a.nome}
            </label>
          ))}
          <button onClick={confirmarConvocacao}>Confirmar convocação</button>
        </div>
      )}

      {convocacao && convocacao.situacao !== "proposta" && (
        <div style={{ marginTop: "1rem" }}>
          <h3>Cartões da convocação #{convocacao.id}</h3>
          {convocacao.turnos.map((t) => (
            <div key={t.id} style={{ border: "1px solid #3c5375", borderRadius: 6, padding: "0.5rem", marginBottom: "0.5rem" }}>
              <strong>{t.agente}</strong> — {t.situacao}
              {t.situacao !== "concluido" ? (
                <div style={{ marginTop: "0.25rem" }}>
                  <textarea
                    placeholder="Cole aqui o resultado deste especialista..."
                    value={rascunhoResultado[t.id] || ""}
                    onChange={(e) => setRascunhoResultado((r) => ({ ...r, [t.id]: e.target.value }))}
                    style={{ width: "100%" }}
                  />
                  <button onClick={() => registrarResultado(t.id)}>Fechar turno</button>
                </div>
              ) : (
                <p style={{ whiteSpace: "pre-wrap" }}>{t.resultado}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
