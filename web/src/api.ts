function lerCookie(nome: string): string {
  const match = document.cookie.match(new RegExp(`(?:^|; )${nome}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

export async function api<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  const metodo = (opcoes.method || "GET").toUpperCase();
  const cabecalhos: Record<string, string> = {
    "Content-Type": "application/json",
    ...((opcoes.headers as Record<string, string>) || {}),
  };
  if (metodo !== "GET") {
    cabecalhos["X-CSRFToken"] = lerCookie("csrftoken");
  }
  const resposta = await fetch(`/api${caminho}`, {
    ...opcoes,
    method: metodo,
    headers: cabecalhos,
    credentials: "same-origin",
  });
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null);
    const detalhe = corpo && typeof corpo.detail === "string" ? corpo.detail : "";
    throw new Error(detalhe || `Falha na API (${resposta.status}) em ${caminho}`);
  }
  return resposta.json() as Promise<T>;
}
