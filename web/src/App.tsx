import { useEffect, useState } from "react";

type SaudeResposta = { status: string };

function App() {
  const [status, setStatus] = useState<string>("verificando...");

  useEffect(() => {
    fetch("/api/health")
      .then((resp) => resp.json())
      .then((data: SaudeResposta) => setStatus(data.status))
      .catch(() => setStatus("indisponível"));
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>Escritório 2D</h1>
      <p>Status da API: {status}</p>
    </main>
  );
}

export default App;
