import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
import "./styles/base.css";
import "./styles/app.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { iniciarAtualizacao } from "./data/carregar";
import { iniciarRota } from "./router";
import { store, temaAtual } from "./store";
import { flushSync, REPO, syncAgora } from "./sync/github";

function aplicarTema(): void {
  document.documentElement.setAttribute("data-theme", temaAtual());
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", temaAtual() === "dark" ? "#0b0d11" : "#f4f5f7");
}
aplicarTema();
store.subscribe(aplicarTema);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

iniciarRota();
iniciarAtualizacao();
if (REPO) {
  void syncAgora();
  window.setInterval(() => void syncAgora(), 15 * 60000);
  document.addEventListener("visibilitychange", () => { if (document.hidden) flushSync(); else void syncAgora(); });
}
