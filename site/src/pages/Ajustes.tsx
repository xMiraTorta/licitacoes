/* Ajustes: meus custos, café verde por nível, pisos, sincronização com o GitHub, tema e atalhos. */
import { useEffect, useState } from "react";
import { abertas } from "../lib/dash";
import { BRL, BRL0, fmtDate, n0, n2, parseNum, PP } from "../lib/format";
import { CAMPOS_CUSTO, custoPadrao, grupoTipo, median, NIVEIS, TM } from "../lib/modelo";
import { alternarTema, custosPadrao, setCusto, setPiso, setUI, temaAtual, toast, useStore } from "../store";
import { conectar, desconectar, REPO, SYNC_BRANCH, SYNC_PATH, syncAgora } from "../sync/github";
import { HoldButton } from "../ui/Controles";
import { IRefresh } from "../ui/icons";
import { Nivel } from "../ui/Pecas";
import { Segmentado } from "../ui/Segmentado";
import { Dica } from "../ui/Tooltip";

export function Ajustes() {
  return (
    <div className="page ajustes">
      <div className="page-h"><h1>Ajustes</h1><span className="small muted">Suas premissas de custo, seus pisos de preço e a gravação das anotações. Tudo isso é gravado junto com as suas anotações.</span></div>
      <div className="aj-grid">
        <MeusCustos />
        <Pisos />
        <Sincronizacao />
        <Aparencia />
        <Atalhos />
        <Versao />
      </div>
    </div>
  );
}

/* Campo numérico com valor padrão em cinza; vazio volta ao padrão. */
function Campo({ id, rotulo, unidade, valor, padrao, ajuda, onSave, permiteZero = true, testid }: { id: string; rotulo: string; unidade: string; valor: number | undefined; padrao: number | undefined; ajuda?: string; onSave: (v: number | null) => void; permiteZero?: boolean; testid?: string }) {
  const fmt = (v: number | undefined) => (v == null ? "" : n2(v).replace(/,00$/, ""));
  const [txt, setTxt] = useState(fmt(valor));
  useEffect(() => setTxt(fmt(valor)), [valor]);
  const salvar = () => {
    const v = parseNum(txt);
    if (Number.isNaN(v) || (v != null && (v < 0 || (!permiteZero && v === 0)))) { toast("Não salvo: digite um número válido (ex.: 5,00).", "erro"); setTxt(fmt(valor)); return; }
    if (v === valor || (v == null && valor == null)) return;
    onSave(v);
  };
  return (
    <div className="campo">
      <label className="lab" htmlFor={id}>{rotulo} <span className="muted">({unidade})</span>{ajuda && <Dica texto={ajuda}><span className="tt-term" style={{ marginLeft: 4 }}>?</span></Dica>}</label>
      <input className="inp num" id={id} inputMode="decimal" placeholder={fmt(padrao)} value={txt} onChange={(e) => setTxt(e.target.value)} onBlur={salvar} onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }} data-testid={testid} />
    </div>
  );
}

function MeusCustos() {
  const data = useStore((s) => s.data)!, prep = useStore((s) => s.prep)!, meus = useStore((s) => s.custos), now = useStore((s) => s.now);
  const O = abertas(prep, now);
  const M = O.filter((c) => c._mg), pos = M.filter((c) => c._mg!.m >= 0).length;
  const cot = (data.mercado?.carvalhaes?.data || data.mercado?.atualizado_em || "").split("-").reverse().join("/");
  return (
    <section className="card pad aj-custos" id="meus-custos" aria-label="Meus custos">
      <div className="card-h" style={{ padding: 0 }}><div><h2>Meus custos</h2><div className="sub">Premissas da margem estimada de cada licitação. Vazio = padrão da pesquisa (em cinza). Torra, embalagem e perda vêm do que você informou; o resto, das fontes em Guia › Sobre os dados.</div></div>{Object.keys(meus).length > 0 && <button type="button" className="btn sm" onClick={() => { custosPadrao(); toast("Custos de volta ao padrão"); }} data-act="custos-padrao">Voltar ao padrão</button>}</div>
      <div className="custos">
        {CAMPOS_CUSTO.map(([k, t, u, , f, ajuda]) => {
          const pd = custoPadrao(data.custos, k);
          return <Campo key={k} id={"cu-" + k} rotulo={t} unidade={u} valor={meus[k] == null ? undefined : meus[k] * f} padrao={pd == null ? undefined : pd * f} ajuda={ajuda} onSave={(v) => { setCusto(k, v == null ? null : v / f); toast(v == null ? "Voltou ao padrão" : "Custo salvo"); }} testid={"custo-" + k} />;
        })}
        {NIVEIS.map((n) => {
          const m = data.mercado?.niveis?.[n];
          return <Campo key={n} id={"cu-g" + NIVEIS.indexOf(n)} rotulo={`Café verde ${n}`} unidade="R$/saca" valor={meus["grao|" + n]} padrao={m?.kg_medio ? Math.round(m.kg_medio * 60) : undefined} ajuda={m ? `Mercado: ${BRL0(m.saca60_min)} a ${BRL0(m.saca60_max)} a saca (cotação de ${cot}); vazio usa o meio da faixa. Café da fazenda: o preço que você receberia vendendo.` : undefined} onSave={(v) => { setCusto("grao|" + n, v); toast(v == null ? "Voltou ao mercado" : "Preço do café verde salvo"); }} permiteZero={false} testid={"custo-grao-" + NIVEIS.indexOf(n)} />;
        })}
      </div>
      <p className="small ink2" style={{ marginTop: 12 }}>{M.length ? <><b>{pos}</b> de {M.length} licitações com estimativa dão lucro aos preços do órgão; margem típica <b>{PP(median(M.map((c) => c._mg!.mp)) || 0)}</b>.</> : "Sem licitações com volume e distância para estimar."}</p>
    </section>
  );
}

function Pisos() {
  const prep = useStore((s) => s.prep)!, pisos = useStore((s) => s.pisos), now = useStore((s) => s.now);
  const O = abertas(prep, now);
  const temPiso = Object.values(pisos).some((v) => v > 0);
  return (
    <section className="card pad" aria-label="Meu preço mínimo por nível">
      <h2>Meu preço mínimo por nível</h2>
      <div className="sub small muted">R$/kg abaixo do qual não vale entrar (café torrado). A sugestão em cinza é o preço típico do nível.</div>
      <div className="pisos">
        {NIVEIS.map((n) => {
          const r = prep.refs[TM + "|" + n];
          return <div key={n} className="campo"><label className="lab" htmlFor={"piso-" + NIVEIS.indexOf(n)}><Nivel n={n} /></label><PisoInput id={"piso-" + NIVEIS.indexOf(n)} nivel={n} valor={pisos[n]} sugestao={r ? r.med : 60} /></div>;
        })}
      </div>
      <p className="small ink2" style={{ marginTop: 10 }}>{temPiso ? <><b>{O.filter((c) => c._cmp && c._cmp.ok).length}</b> licitações abertas cobrem o seu piso; <b>{O.filter((c) => c._cmp && c._cmp.ok === false).length}</b> ficam abaixo.</> : "Preencha para ver quais licitações cobrem o seu custo."}</p>
    </section>
  );
}
function PisoInput({ id, nivel, valor, sugestao }: { id: string; nivel: string; valor: number | undefined; sugestao: number }) {
  const [txt, setTxt] = useState(valor ? n2(valor) : "");
  useEffect(() => setTxt(valor ? n2(valor) : ""), [valor]);
  const salvar = () => {
    const v = parseNum(txt);
    if (Number.isNaN(v) || (v != null && !(v > 0))) { toast("Piso não salvo: digite um valor maior que zero (ex.: 55,00).", "erro"); setTxt(valor ? n2(valor) : ""); return; }
    if ((v ?? null) === (valor ?? null)) return;
    setPiso(nivel, v);
    toast(v ? `Piso ${nivel}: ${BRL(v)}/kg` : `Piso ${nivel} removido`);
  };
  return <input className="inp num" id={id} data-piso={nivel} inputMode="decimal" placeholder={n2(sugestao)} value={txt} onChange={(e) => setTxt(e.target.value)} onBlur={salvar} onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }} title="Vazio: sem piso. A sugestão é o preço típico do nível." />;
}

function Sincronizacao() {
  const sync = useStore((s) => s.sync), meta = useStore((s) => s.meta);
  const [tok, setTok] = useState("");
  const st = !REPO ? "local" : sync.estado === "erro" ? "erro" : sync.estado === "salvando" || (meta.pendente && sync.token) ? "salvando" : sync.token ? "ok" : "local";
  const lbl = { ok: "Salvo no GitHub", salvando: "Salvando…", erro: "Erro ao salvar", local: "Só neste aparelho" }[st];
  const hist = REPO ? `https://github.com/${REPO}/commits/${SYNC_BRANCH}/${SYNC_PATH}` : "";
  return (
    <section className="card pad" aria-label="Sincronização" id="sync">
      <h2 className="row-flex"><span className={"sdot " + st} aria-hidden="true" />Sincronização <span className="small muted" id="syncLbl">· {lbl}{sync.quando ? " em " + fmtDate(sync.quando.slice(0, 16)) : ""}</span></h2>
      {!REPO ? <p className="small muted" style={{ marginTop: 8 }}>Gravação no GitHub disponível só no site publicado. Aqui as anotações ficam neste navegador.</p> : (
        <>
          <p className="small ink2" style={{ marginTop: 8 }}>Favoritos, status, preços, notas, checklist, pisos e meus custos são gravados sozinhos em <code>{SYNC_PATH}</code>, na branch <code>{SYNC_BRANCH}</code> do repositório (visível ao público; não apague essa branch). Cada gravação fica no <a href={hist} target="_blank" rel="noopener">histórico</a>, então dá para recuperar versões antigas.</p>
          {sync.erro && <p className="small crit" style={{ marginTop: 6 }}>{sync.erro}</p>}
          {sync.token ? (
            <div className="row-flex wrap" style={{ marginTop: 10 }}>
              <button type="button" className="btn sm" onClick={() => void syncAgora()} id="syncNow"><IRefresh size={14} /> Sincronizar agora</button>
              <HoldButton className="btn sm ghost" onConfirm={() => { desconectar(); toast("Aparelho desconectado. As anotações continuam aqui e no GitHub."); }} testid="syncOff">Desconectar este aparelho (segure)</HoldButton>
            </div>
          ) : (
            <div className="sync-form" style={{ marginTop: 10 }}>
              <label className="lab" htmlFor="syncTok">Chave de acesso do GitHub (só fica neste aparelho)</label>
              <div className="row-flex"><input className="inp" id="syncTok" type="password" autoComplete="off" placeholder="github_pat_…" value={tok} onChange={(e) => setTok(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void conectar(tok); }} /><button type="button" className="btn primary" id="syncSave" onClick={() => void conectar(tok)}>Conectar</button></div>
              <details className="sync-how"><summary>Como criar a chave (uma vez, 2 minutos)</summary><ol className="small">
                <li>No GitHub: foto do perfil → <b>Settings</b> → <b>Developer settings</b> → <b>Personal access tokens</b> → <b>Fine-grained tokens</b> → <b>Generate new token</b>.</li>
                <li>Nome: “Monitor de Licitações”. Validade: 1 ano.</li>
                <li><b>Repository access</b>: <i>Only select repositories</i> → <b>{REPO}</b>.</li>
                <li><b>Permissions</b> → <b>Contents</b>: <i>Read and write</i>. Nada mais.</li>
                <li>Gere, copie e cole aqui. Repita só o passo 5 nos outros aparelhos (ou crie uma chave para cada um).</li>
              </ol></details>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Aparencia() {
  const theme = useStore((s) => s.ui.theme);
  const dens = useStore((s) => s.ui.densidade || "normal");
  return (
    <section className="card pad" aria-label="Aparência">
      <h2>Aparência</h2>
      <div className="row-flex wrap" style={{ marginTop: 10, gap: 18 }}>
        <div><div className="lab" style={{ marginBottom: 6 }}>Tema</div><Segmentado rotulo="Tema" valor={theme || temaAtual()} onChange={(v) => { if (v !== temaAtual()) alternarTema(); }} opcoes={[["dark", "Escuro"], ["light", "Claro"]]} /></div>
        <div><div className="lab" style={{ marginBottom: 6 }}>Lista</div><Segmentado rotulo="Densidade da lista" valor={dens} onChange={(v) => setUI({ densidade: v })} opcoes={[["normal", "Normal"], ["compacta", "Compacta"]]} /></div>
      </div>
    </section>
  );
}

function Atalhos() {
  const L: [string, string][] = [["/ ou Ctrl K", "Buscar ou fazer algo"], ["G H · G O · G P · G M · G G · G C", "Ir para Hoje, Oportunidades, Propostas, Mercado, Guia, Ajustes"], ["J / K", "Andar na lista"], ["Enter", "Abrir a licitação marcada"], ["F", "Favoritar a licitação marcada"], ["Esc", "Fechar o detalhe ou os filtros"], ["T", "Trocar o tema"], ["?", "Esta tela"]];
  return (
    <section className="card pad" aria-label="Atalhos do teclado">
      <h2>Atalhos do teclado</h2>
      <table className="tbl" style={{ marginTop: 8 }}><tbody>{L.map(([k, t]) => <tr key={k}><td><kbd>{k}</kbd></td><td className="small ink2">{t}</td></tr>)}</tbody></table>
    </section>
  );
}

function Versao() {
  const data = useStore((s) => s.data)!;
  const co = data.coleta;
  return (
    <section className="card pad" aria-label="Sobre esta versão">
      <h2>Dados e versão</h2>
      <dl className="dl small" style={{ marginTop: 8 }}>
        <dt>Dados de</dt><dd>{fmtDate(data.gerado_em.slice(0, 16))} (Brasília)</dd>
        <dt>Licitações</dt><dd>{n0(data.compras.length)} · {data.editais_lidos} com edital lido</dd>
        {co && <><dt>Última coleta</dt><dd>{n0(co.listadas || 0)} compras lidas no PNCP, {n0(co.candidatas || 0)} candidatas, {co.falhas ?? 0} falhas, {Math.round((co.segundos || 0) / 60)} min</dd></>}
        <dt>Site</dt><dd>versão 2 (React) · {grupoTipo(TM)} como tipo de referência</dd>
      </dl>
    </section>
  );
}
