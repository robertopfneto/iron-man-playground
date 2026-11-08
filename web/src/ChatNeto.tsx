import { FormEvent, useEffect, useRef, useState } from "react";

import { api } from "./api";

export const ID_CAMPO_NETO = "mensagem-neto";

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

/** Conversa com Neto. Os turnos convocados ficam no painel de Atividades, que persiste entre recargas. */
export function ChatNeto({ conversaId, agentesDoProjeto, aoAtualizarSala }: Props) {
  const [pedido, setPedido] = useState("");
  const [historico, setHistorico] = useState<Item[]>([]);
  const [convocacaoId, setConvocacaoId] = useState<number | null>(null);
  const [agentesEscolhidos, setAgentesEscolhidos] = useState<Set<number>>(new Set());
  const [enviando, setEnviando] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const mensagensRef = useRef<HTMLDivElement>(null);
  const especialistas = agentesDoProjeto.filter((a) => a.nome !== "Neto");

  useEffect(() => {
    // Rola só a lista de mensagens; scrollIntoView rolaria a página inteira quando o chat fica abaixo da sala.
    const lista = mensagensRef.current;
    if (lista && historico.length > 0) lista.scrollTop = lista.scrollHeight;
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

      if (resp.tipo === "duvida_simples" || resp.tipo === "resposta_direta" || resp.tipo === "sem_evidencia") {
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
      setConvocacaoId(resp.convocacao_id);
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
    if (convocacaoId === null || agentesEscolhidos.size === 0) return;
    await api(`/convocacoes/${convocacaoId}/confirmar`, {
      method: "POST",
      body: JSON.stringify({ agentes_ids: Array.from(agentesEscolhidos) }),
    });
    const nomes = especialistas.filter((a) => agentesEscolhidos.has(a.agente_id)).map((a) => a.nome);
    setConvocacaoId(null);
    setHistorico((h) => [
      ...h,
      {
        tipo: "neto",
        texto: `Convoquei ${nomes.join(" e ")}. Os cartões estão em Atividades: cole ali a entrega de cada especialista.`,
      },
    ]);
    aoAtualizarSala();
  }

  return (
    <>
      <div className="chat-mensagens" aria-live="polite" ref={mensagensRef}>
        {historico.length === 0 && (
          <p className="vazio">
            Fale com Neto sobre este projeto. Perguntas sobre a documentação vêm com as fontes; pedidos de mudança viram
            uma convocação de especialistas.
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
      </div>

      {convocacaoId !== null && (
        <div className="painel">
          <h3>Convocar especialistas</h3>
          <div className="chips">
            {especialistas.map((a) => (
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

      <form className="chat-entrada" onSubmit={enviarMensagem}>
        <input
          id={ID_CAMPO_NETO}
          className="field"
          aria-label="Mensagem para Neto"
          value={pedido}
          onChange={(e) => setPedido(e.target.value)}
          placeholder="Escreva para Neto..."
          autoComplete="off"
        />
        <button className="btn" type="submit" disabled={enviando || !pedido.trim()}>
          Enviar
        </button>
      </form>
    </>
  );
}
