import { useCallback, useEffect, useState } from "react";

import { api } from "./api";
import { ChatNeto, ID_CAMPO_NETO } from "./ChatNeto";
import { Atividades, ConvocacaoAberta, Decisao, Equipe, Estado, IconeEstado } from "./EquipeAtividades";
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
type Sessao = { autenticado: boolean; usuario: string | null; precisa_cadastro?: boolean };
type Aba = "chat" | "ficha";

function App() {
  const [sessao, setSessao] = useState<Sessao | null>(null);
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [projetoId, setProjetoId] = useState<number | null>(null);
  const [sala, setSala] = useState<Sala | null>(null);
  const [template, setTemplate] = useState<TemplateMapa | null>(null);
  const [manifesto, setManifesto] = useState<ManifestoAvatares | null>(null);
  const [conversaId, setConversaId] = useState<number | null>(null);
  const [selecionadoId, setSelecionadoId] = useState<number | null>(null);
  const [decisoes, setDecisoes] = useState<Decisao[]>([]);
  const [convocacoes, setConvocacoes] = useState<ConvocacaoAberta[]>([]);
  const [aba, setAba] = useState<Aba>("chat");

  const selecionado = sala?.avatares.find((a) => a.agente_id === selecionadoId) ?? null;
  const arteSelecionada = selecionado ? buscarAvatar(manifesto, selecionado.avatar_id) : null;

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

  const carregar = useCallback(async (id: number) => {
    const [dadosSala, dadosDecisoes, dadosConvocacoes] = await Promise.all([
      api<Sala>(`/projetos/${id}/sala`),
      api<Decisao[]>(`/projetos/${id}/decisoes`),
      api<ConvocacaoAberta[]>(`/projetos/${id}/convocacoes-abertas`),
    ]);
    setTemplate(await resolverTemplate(dadosSala.template_id));
    setSala(dadosSala);
    setDecisoes(dadosDecisoes);
    setConvocacoes(dadosConvocacoes);
  }, []);

  useEffect(() => {
    if (projetoId === null) return;
    setSelecionadoId(null);
    setConversaId(null);
    setAba("chat");
    carregar(projetoId);
    api<{ id: number }>("/conversas", {
      method: "POST",
      body: JSON.stringify({ projeto_id: projetoId }),
    }).then((c) => setConversaId(c.id));
  }, [projetoId, carregar]);

  function selecionar(agenteId: number) {
    setSelecionadoId(agenteId);
    setAba("ficha");
  }

  function conversarComNeto() {
    setAba("chat");
    requestAnimationFrame(() => {
      const campo = document.getElementById(ID_CAMPO_NETO);
      campo?.scrollIntoView({ block: "nearest", behavior: "smooth" });
      campo?.focus();
    });
  }

  function irParaEquipe() {
    document.querySelector<HTMLButtonElement>("#lista-equipe button")?.focus();
  }

  async function fecharTurno(turnoId: number, resultado: string) {
    await api(`/turnos/${turnoId}/resultado`, {
      method: "POST",
      body: JSON.stringify({ resultado, autoria: sessao?.usuario ?? "usuario" }),
    });
    if (projetoId !== null) await carregar(projetoId);
  }

  async function aprovarDecisao(id: number) {
    await api(`/decisoes/${id}/aprovar`, { method: "POST" });
    if (projetoId !== null) await carregar(projetoId);
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
        <div className="contexto">
          <label className="sr-only" htmlFor="projeto">
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
          {template && (
            <span className="area" title={template.nome}>
              {template.nome}
            </span>
          )}
        </div>
        <div className="acoes">
          <button className="btn btn-ghost btn-equipe" onClick={irParaEquipe}>
            Equipe
          </button>
          <button className="btn" onClick={conversarComNeto}>
            Conversar com Neto
          </button>
          <div className="usuario">
            <span>{sessao.usuario}</span>
            <button className="btn btn-ghost btn-sm" onClick={sair}>
              Sair
            </button>
          </div>
        </div>
      </header>

      <div className="layout">
        <main className="palco">
          <section className="card sala" aria-label={`Sala do projeto ${projetoAtual?.nome ?? ""}`}>
            {sala && template && manifesto ? (
              <SalaPhaser
                key={`${template.id}-${sala.avatares.map((a) => `${a.agente_id}:${a.estado}`).join(",")}`}
                template={template}
                manifesto={manifesto}
                avatares={sala.avatares}
                selecionadoId={selecionadoId}
                onSelecionarAvatar={(avatar) => selecionar(avatar.agente_id)}
              />
            ) : (
              <div className="sala-canvas sala-carregando">Carregando a sala…</div>
            )}
            <div className="legenda" aria-label="Legenda de estados">
              {Object.entries(ESTADO_LABEL).map(([chave, rotulo]) => (
                <span key={chave} className={`st-${chave}`}>
                  <IconeEstado estado={chave} />
                  <span style={{ color: "var(--text-muted)" }}>{rotulo}</span>
                </span>
              ))}
            </div>
          </section>

          {sala && (
            <div className="faixa">
              <Equipe
                avatares={sala.avatares}
                manifesto={manifesto}
                selecionadoId={selecionadoId}
                onSelecionar={selecionar}
              />
              <Atividades
                convocacoes={convocacoes}
                decisoes={decisoes}
                onFecharTurno={fecharTurno}
                onAprovar={aprovarDecisao}
                onConversar={conversarComNeto}
              />
            </div>
          )}
        </main>

        <aside className="card painel-contexto" aria-label="Painel de contexto">
          <div className="abas" role="tablist">
            <button
              role="tab"
              id="aba-chat"
              className="aba"
              aria-selected={aba === "chat"}
              aria-controls="painel-chat"
              onClick={() => setAba("chat")}
            >
              Conversa com Neto
            </button>
            <button
              role="tab"
              id="aba-ficha"
              className="aba"
              aria-selected={aba === "ficha"}
              aria-controls="painel-ficha"
              onClick={() => setAba("ficha")}
            >
              {selecionado ? `Ficha · ${selecionado.nome}` : "Ficha"}
            </button>
          </div>

          <div
            role="tabpanel"
            id="painel-chat"
            aria-labelledby="aba-chat"
            className="aba-conteudo"
            hidden={aba !== "chat"}
          >
            {projetoId !== null && conversaId !== null && sala ? (
              <ChatNeto
                key={conversaId}
                conversaId={conversaId}
                agentesDoProjeto={sala.avatares.map((a) => ({ agente_id: a.agente_id, nome: a.nome }))}
                aoAtualizarSala={() => carregar(projetoId)}
              />
            ) : null}
          </div>

          <div
            role="tabpanel"
            id="painel-ficha"
            aria-labelledby="aba-ficha"
            className="aba-conteudo"
            hidden={aba !== "ficha"}
          >
            {selecionado ? (
              <div className="ficha">
                <div className="ficha-cabecalho">
                  {arteSelecionada ? (
                    <img
                      className="pixel ficha-retrato"
                      src={`${BASE_AVATARES}/${arteSelecionada.retrato}`}
                      alt={`Retrato de ${selecionado.nome}`}
                      width={96}
                      height={96}
                    />
                  ) : (
                    <div className="ficha-retrato" />
                  )}
                  <dl>
                    <dt>Agente</dt>
                    <dd className="ficha-nome">{selecionado.nome}</dd>
                    {selecionado.homenagem && (
                      <>
                        <dt>Homenagem</dt>
                        <dd>{selecionado.homenagem}</dd>
                      </>
                    )}
                    <dt>Papel</dt>
                    <dd>{selecionado.especialidade}</dd>
                    <dt>Estado</dt>
                    <dd>
                      <Estado estado={selecionado.estado} />
                    </dd>
                  </dl>
                </div>
                {arteSelecionada && <p className="vazio">{ARTE_LABEL[arteSelecionada.arte]}</p>}
                {selecionado.direcao_arte && (
                  <details className="ficha-arte">
                    <summary>Direção de arte e referência</summary>
                    <p>{selecionado.direcao_arte}</p>
                    <p className="vazio">{selecionado.referencia_visual}</p>
                  </details>
                )}
                <div>
                  <button className="btn btn-ghost btn-sm" onClick={conversarComNeto}>
                    Voltar à conversa
                  </button>
                </div>
              </div>
            ) : (
              <div className="ficha-vazia">
                <p className="vazio">Selecione um agente na sala ou na lista da equipe para ver a ficha.</p>
              </div>
            )}
          </div>
        </aside>
      </div>
    </>
  );
}

export default App;
