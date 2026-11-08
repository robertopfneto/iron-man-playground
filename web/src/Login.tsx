import { FormEvent, useState } from "react";

import { api } from "./api";

type Props = { precisaCadastro: boolean; aoEntrar: (usuario: string) => void };

export function Login({ precisaCadastro, aoEntrar }: Props) {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function entrar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    if (precisaCadastro && senha !== confirmacao) {
      setErro("As senhas não conferem.");
      return;
    }
    setEnviando(true);
    try {
      const resp = await api<{ usuario: string }>(precisaCadastro ? "/auth/primeiro-acesso" : "/auth/login", {
        method: "POST",
        body: JSON.stringify({ usuario, senha }),
      });
      aoEntrar(resp.usuario);
    } catch (falha) {
      setErro(
        precisaCadastro
          ? (falha as Error).message || "Não foi possível criar a conta."
          : "Usuário ou senha inválidos."
      );
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="login">
      <div className="login-card">
        <div className="marca">
          <span className="marca-icone" aria-hidden="true" />
          Escritório 2D
        </div>
        <p className="sub">
          {precisaCadastro
            ? "Primeiro acesso: crie a conta administradora deste escritório. Depois disso o cadastro é fechado."
            : "Entre para conversar com Neto e acompanhar a equipe."}
        </p>
        <form onSubmit={entrar}>
          <div>
            <label className="rotulo" htmlFor="usuario">
              Usuário
            </label>
            <input
              id="usuario"
              name="usuario"
              className="field"
              autoComplete="username"
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="rotulo" htmlFor="senha">
              Senha
            </label>
            <input
              id="senha"
              name="senha"
              type="password"
              className="field"
              autoComplete={precisaCadastro ? "new-password" : "current-password"}
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              required
            />
          </div>
          {precisaCadastro && (
            <div>
              <label className="rotulo" htmlFor="confirmacao">
                Confirmar senha
              </label>
              <input
                id="confirmacao"
                name="confirmacao"
                type="password"
                className="field"
                autoComplete="new-password"
                value={confirmacao}
                onChange={(e) => setConfirmacao(e.target.value)}
                required
              />
            </div>
          )}
          {erro && (
            <p className="erro" role="alert">
              {erro}
            </p>
          )}
          <button className="btn" type="submit" disabled={enviando}>
            {enviando ? "Aguarde..." : precisaCadastro ? "Criar conta e entrar" : "Entrar"}
          </button>
        </form>
      </div>
    </main>
  );
}
