import { useEffect, useState } from "react";

import { api } from "./api";
import { ChatNeto } from "./ChatNeto";
import { resolverTemplate } from "./room/mapas";
import { AvatarSala, SalaPhaser } from "./room/SalaPhaser";

type Projeto = { id: number; nome: string; cenario: string };
type Sala = { projeto_id: number; template_id: string; avatares: AvatarSala[] };
type Decisao = { id: number; texto: string; situacao: string };

function App() {
  const [status, setStatus] = useState<string>("verificando...");
  const [autenticado, setAutenticado] = useState(false);
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [projetoId, setProjetoId] = useState<number | null>(null);
  const [sala, setSala] = useState<Sala | null>(null);
  const [conversaId, setConversaId] = useState<number | null>(null);
  const [avatarSelecionadoId, setAvatarSelecionadoId] = useState<number | null>(null);
  const [decisoes, setDecisoes] = useState<Decisao[]>([]);

  const avatarSelecionado =
    sala?.avatares.find((a) => a.agente_id === avatarSelecionadoId) ?? null;

  useEffect(() => {
    fetch("/api/health")
      .then((resp) => resp.json())
      .then((data: { status: string }) => setStatus(data.status))
      .catch(() => setStatus("indisponível"));
  }, []);

  useEffect(() => {
    api<Projeto[]>("/projetos")
      .then((lista) => {
        setAutenticado(true);
        setProjetos(lista);
        if (lista.length > 0) setProjetoId(lista[0].id);
      })
      .catch(() => setAutenticado(false));
  }, []);

  async function carregarSala(id: number) {
    const dados = await api<Sala>(`/projetos/${id}/sala`);
    setSala(dados);
    const d = await api<Decisao[]>(`/projetos/${id}/decisoes`);
    setDecisoes(d);
  }

  useEffect(() => {
    if (projetoId === null) return;
    setAvatarSelecionadoId(null);
    carregarSala(projetoId);
    api<{ id: number }>("/conversas", {
      method: "POST",
      body: JSON.stringify({ projeto_id: projetoId }),
    }).then((c) => setConversaId(c.id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projetoId]);

  async function aprovarDecisao(id: number) {
    await api(`/decisoes/${id}/aprovar`, { method: "POST" });
    if (projetoId !== null) carregarSala(projetoId);
  }

  if (!autenticado) {
    return (
      <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
        <h1>Escritório 2D</h1>
        <p>Status da API: {status}</p>
        <p>
          Faça login pelo <a href="/admin/login/">Django Admin</a> para acessar a sala e os projetos.
        </p>
      </main>
    );
  }

  const template = sala ? resolverTemplate(sala.template_id) : resolverTemplate(undefined);

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem", color: "#e8edf2" }}>
      <h1>Escritório 2D</h1>

      <label>
        Projeto:{" "}
        <select value={projetoId ?? ""} onChange={(e) => setProjetoId(Number(e.target.value))}>
          {projetos.map((p) => (
            <option key={p.id} value={p.id}>
              {p.nome}
            </option>
          ))}
        </select>
      </label>

      <div style={{ display: "flex", gap: "1rem", marginTop: "1rem", flexWrap: "wrap" }}>
        {sala && (
          <SalaPhaser
            key={`${template.id}-${sala.avatares.map((a) => `${a.agente_id}:${a.estado}`).join(",")}`}
            template={template}
            avatares={sala.avatares}
            onSelecionarAvatar={(avatar) => setAvatarSelecionadoId(avatar.agente_id)}
          />
        )}

        <aside style={{ minWidth: 220 }}>
          <h2>Ficha</h2>
          {avatarSelecionado ? (
            <div>
              <p>
                <strong>{avatarSelecionado.nome}</strong>
              </p>
              {avatarSelecionado.homenagem && <p>Homenagem: {avatarSelecionado.homenagem}</p>}
              <p>{avatarSelecionado.especialidade}</p>
              <p>Estado: {avatarSelecionado.estado}</p>
            </div>
          ) : (
            <p>Selecione um avatar na sala.</p>
          )}

          <h2>Decisões</h2>
          {decisoes.length === 0 && <p>Nenhuma decisão ainda.</p>}
          {decisoes.map((d) => (
            <div key={d.id} style={{ marginBottom: "0.5rem" }}>
              <p style={{ whiteSpace: "pre-wrap" }}>{d.texto}</p>
              <p>Situação: {d.situacao}</p>
              {d.situacao === "proposta" && <button onClick={() => aprovarDecisao(d.id)}>Aprovar</button>}
            </div>
          ))}
        </aside>
      </div>

      {projetoId !== null && conversaId !== null && sala && (
        <ChatNeto
          projetoId={projetoId}
          conversaId={conversaId}
          agentesDoProjeto={sala.avatares.map((a) => ({ agente_id: a.agente_id, nome: a.nome }))}
          aoAtualizarSala={() => carregarSala(projetoId)}
        />
      )}
    </main>
  );
}

export default App;
