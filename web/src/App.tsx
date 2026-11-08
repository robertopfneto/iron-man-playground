import { useCallback, useEffect, useState } from "react";

import { api } from "./api";
import { ChatNeto } from "./ChatNeto";
import { Login } from "./Login";
import {
  ARTE_LABEL,
  BASE_AVATARES,
  buscarAvatar,
  carregarManifestoAvatares,
  ESTADO_LABEL,
  ManifestoAvatares,
} from "./room/avatares";
import { resolverTemplate, TemplateMapa } from "./room/mapas";
import { AvatarSala, SalaPhaser } from "./room/SalaPhaser";

type Projeto = { id: number; nome: string; cenario: string };
type Sala = { projeto_id: number; template_id: string; avatares: AvatarSala[] };
type Decisao = { id: number; texto: string; situacao: string };
type Sessao = { autenticado: boolean; usuario: string | null; precisa_cadastro?: boolean };

const SITUACAO_DECISAO: Record<string, string> = {
  proposta: "Proposta",
  aprovada: "Aprovada",
  rejeitada: "Rejeitada",
};

function App() {
  const [sessao, setSessao] = useState<Sessao | null>(null);
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [projetoId, setProjetoId] = useState<number | null>(null);
  const [sala, setSala] = useState<Sala | null>(null);
  const [template, setTemplate] = useState<TemplateMapa | null>(null);
  const [manifesto, setManifesto] = useState<ManifestoAvatares | null>(null);
  const [conversaId, setConversaId] = useState<number | null>(null);
  const [avatarSelecionadoId, setAvatarSelecionadoId] = useState<number | null>(null);
  const [decisoes, setDecisoes] = useState<Decisao[]>([]);

  const avatarSelecionado = sala?.avatares.find((a) => a.agente_id === avatarSelecionadoId) ?? null;
  const arteSelecionada = avatarSelecionado ? buscarAvatar(manifesto, avatarSelecionado.avatar_id) : null;

  useEffect(() => {
    api<Sessao>("/auth/sessao")
      .then(setSessao)
      .catch(() => setSessao({ autenticado: false, usuario: null }));
    carregarManifestoAvatares().then(setManifesto);
  }, []);

  useEffect(() => {
    if (!sessao?.autenticado) return;
    api<Projeto[]>("/projetos").then((lista) => {
      setProjetos(lista);
      if (lista.length > 0) setProjetoId(lista[0].id);
    });
  }, [sessao?.autenticado]);

  const carregarSala = useCallback(async (id: number) => {
    const [dadosSala, dadosDecisoes] = await Promise.all([
      api<Sala>(`/projetos/${id}/sala`),
      api<Decisao[]>(`/projetos/${id}/decisoes`),
    ]);
    setTemplate(await resolverTemplate(dadosSala.template_id));
    setSala(dadosSala);
    setDecisoes(dadosDecisoes);
  }, []);

  useEffect(() => {
    if (projetoId === null) return;
    setAvatarSelecionadoId(null);
    setConversaId(null);
    carregarSala(projetoId);
    api<{ id: number }>("/conversas", {
      method: "POST",
      body: JSON.stringify({ projeto_id: projetoId }),
    }).then((c) => setConversaId(c.id));
  }, [projetoId, carregarSala]);

  async function aprovarDecisao(id: number) {
    await api(`/decisoes/${id}/aprovar`, { method: "POST" });
    if (projetoId !== null) carregarSala(projetoId);
  }

  async function sair() {
    await api("/auth/logout", { method: "POST" });
    setSessao({ autenticado: false, usuario: null });
    setProjetos([]);
    setProjetoId(null);
    setSala(null);
  }

  if (sessao === null) return null;

  if (!sessao.autenticado) {
    return (
      <Login
        precisaCadastro={Boolean(sessao.precisa_cadastro)}
        aoEntrar={(usuario) => setSessao({ autenticado: true, usuario })}
      />
    );
  }

  const projetoAtual = projetos.find((p) => p.id === projetoId);

  return (
    <>
      <header className="topbar">
        <div className="marca">
          <span className="marca-icone" aria-hidden="true" />
          Escritório 2D
        </div>
        <div className="seletor">
          <label className="rotulo" htmlFor="projeto" style={{ margin: 0 }}>
            Projeto
          </label>
          <select
            id="projeto"
            className="field"
            value={projetoId ?? ""}
            onChange={(e) => setProjetoId(Number(e.target.value))}
          >
            {projetos.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome}
              </option>
            ))}
          </select>
        </div>
        <div className="usuario">
          <span>{sessao.usuario}</span>
          <button className="btn btn-ghost btn-sm" onClick={sair}>
            Sair
          </button>
        </div>
      </header>

      <div className="layout">
        <div className="coluna">
          <section className="card">
            <div className="card-titulo">
              <h2>{template ? template.nome : "Sala"}</h2>
              <span className="meta">
                {projetoAtual?.cenario}
                {template ? ` · mapa ${template.id} v${template.versao}` : ""}
              </span>
            </div>
            {sala && template && manifesto ? (
              <SalaPhaser
                key={`${template.id}-${sala.avatares.map((a) => `${a.agente_id}:${a.estado}`).join(",")}`}
                template={template}
                manifesto={manifesto}
                avatares={sala.avatares}
                selecionadoId={avatarSelecionadoId}
                onSelecionarAvatar={(avatar) => setAvatarSelecionadoId(avatar.agente_id)}
              />
            ) : (
              <div className="sala-canvas sala-carregando">Carregando a sala…</div>
            )}

            {sala && (
              <ul className="equipe" aria-label="Equipe do projeto">
                {sala.avatares.map((a) => {
                  const arte = buscarAvatar(manifesto, a.avatar_id);
                  return (
                    <li key={a.agente_id}>
                      <button
                        className="membro"
                        aria-pressed={a.agente_id === avatarSelecionadoId}
                        onClick={() => setAvatarSelecionadoId(a.agente_id)}
                      >
                        {arte && <img className="pixel" src={`${BASE_AVATARES}/${arte.simbolo}`} alt="" />}
                        <span>{a.nome}</span>
                        <span className={`ponto st-${a.estado}`} aria-hidden="true" />
                        <span className="sr-only">{ESTADO_LABEL[a.estado]}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <div className="linha-2">
            <section className="card">
              <div className="card-titulo">
                <h2>Ficha</h2>
                {arteSelecionada && <span className="meta">{ARTE_LABEL[arteSelecionada.arte]}</span>}
              </div>
              {avatarSelecionado ? (
                <div className="ficha">
                  {arteSelecionada ? (
                    <img
                      className="pixel ficha-retrato"
                      src={`${BASE_AVATARES}/${arteSelecionada.retrato}`}
                      alt={`Retrato de ${avatarSelecionado.nome}`}
                      width={96}
                      height={96}
                    />
                  ) : (
                    <div className="ficha-retrato" />
                  )}
                  <dl>
                    <dt>Agente</dt>
                    <dd className="ficha-nome">{avatarSelecionado.nome}</dd>
                    {avatarSelecionado.homenagem && (
                      <>
                        <dt>Homenagem</dt>
                        <dd>{avatarSelecionado.homenagem}</dd>
                      </>
                    )}
                    <dt>Papel</dt>
                    <dd>{avatarSelecionado.especialidade}</dd>
                    <dt>Estado</dt>
                    <dd>
                      <span className={`badge st-${avatarSelecionado.estado}`}>
                        {ESTADO_LABEL[avatarSelecionado.estado] ?? avatarSelecionado.estado}
                      </span>
                    </dd>
                  </dl>
                  {avatarSelecionado.direcao_arte && (
                    <details className="ficha-arte">
                      <summary>Direção de arte e referência</summary>
                      <p>{avatarSelecionado.direcao_arte}</p>
                      <p className="vazio">{avatarSelecionado.referencia_visual}</p>
                    </details>
                  )}
                </div>
              ) : (
                <p className="vazio">Clique em um avatar na sala ou na equipe para ver a ficha.</p>
              )}
            </section>

            <section className="card">
              <div className="card-titulo">
                <h2>Decisões</h2>
                <span className="meta">{decisoes.length}</span>
              </div>
              {decisoes.length === 0 ? (
                <p className="vazio">Nenhuma decisão registrada neste projeto.</p>
              ) : (
                <div className="decisoes">
                  {decisoes.map((d) => (
                    <div key={d.id} className="decisao">
                      <p>{d.texto}</p>
                      <div className="acoes">
                        <span className={`badge st-${d.situacao}`}>
                          {SITUACAO_DECISAO[d.situacao] ?? d.situacao}
                        </span>
                        {d.situacao === "proposta" && (
                          <button className="btn btn-sm" onClick={() => aprovarDecisao(d.id)}>
                            Aprovar
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>

        {projetoId !== null && conversaId !== null && sala ? (
          <ChatNeto
            key={conversaId}
            conversaId={conversaId}
            agentesDoProjeto={sala.avatares.map((a) => ({ agente_id: a.agente_id, nome: a.nome }))}
            aoAtualizarSala={() => carregarSala(projetoId)}
          />
        ) : (
          <section className="card chat" />
        )}
      </div>
    </>
  );
}

export default App;
