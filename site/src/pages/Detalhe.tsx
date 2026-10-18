/* Painel de uma licitação: Vale a pena?, custo e margem, o que pedem, minha proposta, itens, edital e dados. */
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { BRL, BRL0, countdown, fmtDate, fmtMin, KG, n0, n1, n3, nrm, parseNum, PCT, PP, tcase } from "../lib/format";
import { follows, temAnotacao } from "../lib/filtros";
import { edStatus, grupoTipo, marcasVarejo, MERCADO_VAREJO, mgCls, nivelPorque, platShort, pncpLink, pontosDeAtencao, rkLbl, rkOutrosTxt, rkV, urg, varejoTxt, type PCompra } from "../lib/modelo";
import { abrirDetalhe, fecharDetalhe, navegar } from "../router";
import { setW, store, toast, useStore } from "../store";
import { Contador } from "../ui/Contador";
import { GlideSelect, HoldButton, StatusMark } from "../ui/Controles";
import { useDebounce, useRelogio } from "../ui/hooks";
import { IBack, ICopy, IExt, IStar, IX } from "../ui/icons";
import { MeBadge, Nivel, PrecoCmp, Prazo } from "../ui/Pecas";
import { Dica, Termo } from "../ui/Tooltip";

export function Detalhe({ chave, celular }: { chave: string; celular?: boolean }) {
  const c = useStore((s) => s.prep?.byk[chave]) || null;
  const w = useStore((s) => s.wf[chave]) || {};
  const data = useStore((s) => s.data)!;
  const fav = () => { const on = !w.fav; setW(chave, { fav: on }); toast(on ? "★ Adicionada aos favoritos" : "Removida dos favoritos"); };
  const corpo = c ? <Corpo c={c} /> : <Sumida chave={chave} />;
  const r = w.ref || {};
  return (
    <motion.aside className={"detalhe" + (celular ? " drawer" : "")} aria-label="Detalhes da licitação" data-ch={chave} initial={celular ? { x: 40, opacity: 0 } : { opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.2 }}>
      <div className="d-head">
        <div className="d-top">
          {celular && <button type="button" className="btn icon ghost" onClick={fecharDetalhe} aria-label="Voltar"><IBack /></button>}
          <div className="d-title"><h2>{c ? `${c.mun} · ${c.uf}` : r.mun ? `${r.mun} · ${r.uf}` : chave}</h2><div className="small muted">{c ? c._orgao : r.orgao || ""}</div></div>
          <button type="button" className={"star" + (w.fav ? " on" : "")} data-act="fav" aria-label="Favorito" onClick={fav}><IStar size={18} filled={!!w.fav} /></button>
          {!celular && <button type="button" className="btn icon ghost" data-act="close" aria-label="Fechar" onClick={fecharDetalhe}><IX /></button>}
        </div>
        <div className="d-meta">
          {c ? <><Prazo c={c} />{c._ms && <Contagem ms={c._ms} />}<span className="small muted">· {fmtDate(c.fim)}</span>{c._new && <span className="badge b-new">Nova</span>}<MeBadge c={c} /></> : <><span className="pill closed"><span className="dot" />Fora dos dados</span><span className="small muted">· prazo {fmtDate(r.fim)}</span></>}
        </div>
        <div className="d-actions">
          <a className="btn primary sm" href={c ? c.link_pncp : r.link || pncpLink(chave)} target="_blank" rel="noopener">Abrir no PNCP <IExt size={13} /></a>
          {c && (c.link_plat ? <a className="btn sm" href={c.link_plat} target="_blank" rel="noopener" title={c.plat}>Abrir na plataforma <IExt size={13} /></a> : <Dica texto="O PNCP não informa o link da plataforma; veja o edital"><span className="btn sm" aria-disabled="true">Plataforma: ver edital</span></Dica>)}
        </div>
      </div>
      <div className="d-body">{corpo}</div>
      {!data && null}
    </motion.aside>
  );
}

function Contagem({ ms }: { ms: number }) {
  const t = useRelogio();
  return <span className="small muted cd">{countdown(ms, t)}</span>;
}

function Corpo({ c }: { c: PCompra }) {
  return (
    <>
      <Veredito c={c} />
      <CustoMargem c={c} />
      <OQuePedem c={c} />
      <Resumo c={c} />
      <MinhaProposta chave={c.chave} c={c} />
      <Itens c={c} />
      <Edital c={c} />
      <DadosCompra c={c} />
    </>
  );
}

/* ---------------- Vale a pena? */
function Veredito({ c }: { c: PCompra }) {
  const x = c._cmp, refs = useStore((s) => s.prep!.refs), mr = useStore((s) => s.data!.marcas_ref);
  if (!x) {
    const why = c.itens.every((i) => !i.nivel) ? `${c.tipos.join(", ")}: tipo sem comparação por nível de qualidade.` : "O item de café torrado não tem R$/kg calculável (falta peso ou valor, ou o valor parece erro de unidade).";
    return <section className="card verdict"><h3>Vale a pena?</h3><p className="small ink2">{why} Compare pelo valor unitário dos itens.</p></section>;
  }
  const r = refs[grupoTipo(x.i.tipo) + "|" + x.i.nivel];
  const mv = marcasVarejo(mr, c);
  const vj = MERCADO_VAREJO.valores[x.i.nivel || ""];
  return (
    <section className="card verdict">
      <h3>Vale a pena?</h3>
      <div className="big">{BRL(x.i.rkg)}/kg para café {x.i.tipo.toLowerCase()} nível {x.i.nivel} <PrecoCmp c={c} longo /></div>
      {r && <Strip r={r} v={x.i.rkg!} piso={x.piso} nivel={x.i.nivel || ""} vj={vj} />}
      <p className="small ink2">
        {x.dif == null ? "Poucas licitações abertas desse nível para calcular um preço típico." : <>Preço típico do nível: <b>{BRL(x.ref)}/kg</b> ({r!.n} itens abertos; a maioria fica entre {BRL(r!.p25)} e {BRL(r!.p75)}).</>}
        {x.piso ? (x.ok ? <b className="good"> Cobre o seu piso de {BRL(x.piso)}/kg.</b> : <b className="crit"> Abaixo do seu piso de {BRL(x.piso)}/kg.</b>) : <> <button type="button" className="linkbtn" data-act="pisos" onClick={() => irAjustes(`[data-piso="${x.i.nivel}"]`)}>Definir meu preço mínimo para {x.i.nivel}</button></>}
        {mv && <><br />Marcas de referência citadas no edital (linha mais básica) custam {BRL(mv.min)} a {BRL(mv.max)}/kg no varejo.</>}
        {vj && <><br />Varejo {x.i.nivel} em supermercados (ABIC, {MERCADO_VAREJO.data}): {BRL(vj)}/kg.</>}
        <br /><span className="muted">Por que nível {x.i.nivel}: {nivelPorque(x.i)}. O preço típico compara licitações entre si; não é custo.</span>
      </p>
    </section>
  );
}

function Strip({ r, v, piso, nivel, vj }: { r: { med: number; p25: number; p75: number; pts: { chave: string; v: number }[] }; v: number; piso: number | null; nivel: string; vj?: number }) {
  const lo = 30, hi = 160, W = 600, H = 40, y0 = 3, y1 = 25;
  const x = (val: number) => 6 + ((Math.min(Math.max(val, lo), hi) - lo) / (hi - lo)) * (W - 12);
  const ticks: number[] = [];
  for (let t = 40; t <= hi; t += 20) ticks.push(t);
  return (
    <svg className="strip" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={`R$/kg estimado das licitações nível ${nivel}`}>
      {ticks.map((t) => <g key={t}><line className="grid" x1={x(t)} x2={x(t)} y1={y0} y2={y1} /><text className="axl" x={x(t)} y={H - 2} textAnchor="middle">R$ {t}</text></g>)}
      <rect className="band" x={x(r.p25)} y={y0 + 3} width={Math.max(2, x(r.p75) - x(r.p25))} height={y1 - y0 - 6} rx="3"><title>Faixa comum (metade das licitações): {BRL(r.p25)} a {BRL(r.p75)}/kg</title></rect>
      {r.pts.map((p) => <rect key={p.chave} className="dotp" x={x(p.v) - 1.5} y={y0 + 5} width="3" height={y1 - y0 - 10} rx="1.5" onClick={() => abrirDetalhe(p.chave)} />)}
      <rect className="medr" x={x(r.med) - 1.5} y={y0} width="3" height={y1 - y0} rx="1.5"><title>Preço típico {nivel}: {BRL(r.med)}/kg</title></rect>
      <rect className="eu" x={x(v) - 2.5} y={y0 - 2} width="5" height={y1 - y0 + 4} rx="2"><title>Esta licitação: {BRL(v)}/kg</title></rect>
      {vj && <path className="vj" d={`M${x(vj)} ${y0 - 1}l5 6-5 6-5-6z`} transform={`translate(0 ${(y1 - y0) / 2 - 5})`}><title>Varejo {nivel} (ABIC): {BRL(vj)}/kg</title></path>}
      {piso && <line className="piso" x1={x(piso)} x2={x(piso)} y1={y0 - 2} y2={y1 + 2}><title>Meu piso {nivel}: {BRL(piso)}/kg</title></line>}
    </svg>
  );
}

/* ---------------- custo e margem */
function CustoMargem({ c }: { c: PCompra }) {
  const x = c._mg, prep = useStore((s) => s.prep)!, data = useStore((s) => s.data)!;
  const calc = prep.calc;
  if (!x) {
    const falta = !c._main ? "sem item de café com R$/kg" : !c.kg ? "falta o volume em kg" : c.dist == null ? "falta a distância até o município" : "sem preço do café verde para o nível";
    return <section className="card"><h3>Custo e margem (estimativa)</h3><p className="small ink2">Não dá para estimar: {falta}.</p></section>;
  }
  const cot = (data.mercado?.carvalhaes?.data || data.mercado?.atualizado_em || "").split("-").reverse().join("/");
  const L: [React.ReactNode, number][] = [
    [<>Café verde {x.nivel} {x.proprio ? "(seu preço)" : `(mercado, cotação de ${cot})`}, com {PP(calc.custo("perda_torra"))} de perda na torra</>, x.grao],
    ["Torra terceirizada", x.torra], ["Embalagem", x.emb],
    [<>Frete até {c.mun} ({n0(c.dist!)} km, {Math.max(1, Math.round(c.srp === "Sim" ? calc.custo("entregas_rp") : calc.custo("entregas")))} entrega(s), +{PP(calc.custo("folga_frete"))} de folga)</>, x.frete],
    [<>Plataforma, laudo e amostra, divididos em {KG(x.kg)}</>, x.fixos], [<>Imposto, prazo de pagamento e perdas ({PP(x.pct)} do preço)</>, x.pctV],
  ];
  return (
    <section className="card" data-testid="custo-margem">
      <h3>Custo e <Termo t="Margem">margem</Termo> (estimativa)</h3>
      <div className="big" style={{ fontSize: 17 }}>Margem <span className={"mg " + mgCls(x.mp)}>{PCT(x.mp)}</span> ao preço do órgão: {x.m >= 0 ? "lucro" : "prejuízo"} de ~{BRL0(Math.abs(x.lucro))} em {c._parcial ? "≥ " : ""}{KG(x.kg)}</div>
      <table className="cost-t"><tbody>
        {L.map(([t, v], i) => <tr key={i}><td>{t}</td><td className="mono">{BRL(v)}/kg</td></tr>)}
        <tr className="tot"><td>Custo total</td><td className="mono">{BRL(x.custo)}/kg</td></tr>
        <tr className="tot"><td>Preço do órgão</td><td className="mono">{BRL(x.preco)}/kg</td></tr>
      </tbody></table>
      <p className="small ink2" style={{ marginTop: 8 }}><Termo t="Preço para empatar">Preço para empatar</Termo> (lucro zero): <b>{BRL(x.empate)}/kg</b>. Estimativa com premissas de mercado e pesquisa (fontes em Guia › Sobre os dados); frete por fórmula (erro médio de 17%), confirme com cotação nas licitações boas. <button type="button" className="linkbtn" data-act="custos" onClick={() => irAjustes("#meus-custos")}>Ajustar meus custos</button></p>
    </section>
  );
}

/* ---------------- o que pedem */
function OQuePedem({ c }: { c: PCompra }) {
  const i = c._main || c.itens[0];
  const t = i.tags || [], val = t.find((x) => x.startsWith("Validade")), sim = (x: string) => (t.includes(x) ? "Sim" : "Não citado");
  const kv: [string, string][] = [["Tipo", i.tipo], ["Nível de exigência", i.nivel || "não se aplica"], ["Nota mínima de qualidade", i.qg ? n1(i.qg) + " (0 a 10)" : "Não citada"],
    ["Categoria citada", i.cat || "Não citada"], ["Selo ABIC", sim("ABIC/pureza")], ["100% arábica", sim("100% arábica")], ["Embalagem", i.emb || c.embs || "Não informada"],
    ["Validade mínima", val ? val.replace("Validade ", "") : "Não citada"], ["Laudo de qualidade", sim("Laudo")], ["Amostra", sim("Amostra")], ["Marca de referência", sim("Marca ref.")],
    ["Grãos sem defeitos (PVA)", sim("Sem PVA (grãos selecionados)")], ["Grãos selecionados", sim("Grãos selecionados")], ["“Premium” ou “1ª qualidade”", t.includes("Premium/1ª qualidade (termo comercial)") ? "Sim (termo comercial, sem padrão oficial)" : "Não citado"], ["Aceita conilon ou blend", t.includes("Aceita conilon/blend") ? "Sim (matéria-prima mais barata)" : "Não citado"]];
  const at = pontosDeAtencao(i);
  return (
    <section className="card">
      <h3>O que pedem{c._main && c.itens.length > 1 ? " (item principal)" : ""}</h3>
      <div className="spec-grid">{kv.map(([k, v]) => <div key={k}><small>{k}</small>{v}</div>)}</div>
      {at.length > 0 && <div style={{ marginTop: 12 }}><b className="small">Pontos de atenção</b> <span className="small muted">(para avaliar impugnação ou esclarecimento; não é orientação jurídica)</span><ul className="warn-list">{at.map((x) => <li key={x}>{x}</li>)}</ul></div>}
      {c.edital_lido && c.ed_tags.length > 0 && <p className="small muted" style={{ marginTop: 10 }}>O edital também menciona: {c.ed_tags.join(", ")}</p>}
    </section>
  );
}

/* ---------------- resumo */
function Resumo({ c }: { c: PCompra }) {
  const prep = useStore((s) => s.prep)!;
  const r = rkV(c);
  return (
    <section className="card">
      <h3>Resumo</h3>
      <div className="facts num">
        <div><small>Valor estimado (café)</small><b>{c.vcafe == null ? (c.sig !== "Não" ? <Termo t="Sigiloso" /> : "—") : BRL0(c.vcafe)}</b></div>
        <div><small>Volume</small><b>{c.kg == null ? "—" : (c._parcial ? "≥ " : "") + KG(c.kg)}</b>{c._parcial && <div className="sub">algum item sem peso</div>}</div>
        <div><small>R$/kg estimado</small><b>{r == null ? "—" : BRL(r)}</b><div className="sub">{rkLbl(c) || (r == null ? "" : "torrado e moído")}{rkOutrosTxt(c) ? " · + " + rkOutrosTxt(c) : ""}</div></div>
        <div><small>Distância de {prep.origem}</small><b>{c.dist == null ? "—" : n0(c.dist) + " km"}</b><div className="sub">{c.dist_min != null ? "cerca de " + fmtMin(c.dist_min) + " de carro" : ""}</div></div>
        <div><small>Onde enviar</small><b style={{ fontSize: 14 }}>{platShort(c)}</b><div className="sub">{c.plat_src}</div></div>
        <div><small>Modalidade</small><b style={{ fontSize: 14 }}><Termo t={c.mod}>{c.mod}</Termo> {c.num}</b><div className="sub">{c.srp === "Sim" ? <Termo t="Registro de preços">registro de preços</Termo> : ""}</div></div>
      </div>
    </section>
  );
}

/* ---------------- minha proposta */
export function MinhaProposta({ chave, c }: { chave: string; c: PCompra | null }) {
  const w = useStore((s) => s.wf[chave]) || {};
  const data = useStore((s) => s.data)!;
  const prep = useStore((s) => s.prep)!;
  const [preco, setPreco] = useState(w.preco != null ? w.preco.toFixed(2).replace(".", ",") : "");
  const [resp, setResp] = useState(w.resp || "");
  const [notas, setNotas] = useState(w.notas || "");
  useEffect(() => { setPreco(w.preco != null ? w.preco.toFixed(2).replace(".", ",") : ""); setResp(w.resp || ""); setNotas(w.notas || ""); }, [chave]); // eslint-disable-line react-hooks/exhaustive-deps
  const salvar = useDebounce<[string, string]>(([k, v]) => {
    if (k === "preco") {
      const n = parseNum(v);
      if (n != null && !(n > 0)) { toast("Preço não salvo: digite um valor maior que zero (ex.: 45,50).", "erro"); return; }
      setW(chave, { preco: n ?? undefined });
    } else setW(chave, { [k]: v });
  }, 350);
  const r = c ? rkV(c) : null;
  const precoN = parseNum(preco);
  const m = c && precoN && r ? (r - precoN) / r : null;
  const mm = c && precoN && precoN > 0 ? prep.calc.margem(c, c._main, precoN) : null;
  return (
    <section className="card" data-testid="minha-proposta">
      <h3>Minha proposta</h3>
      <div className="mine-grid">
        <div><label className="lab">Status</label><GlideSelect valor={w.status || ""} opcoes={data.status_opcoes} onChange={(v) => { setW(chave, { status: v }); toast(v ? `Status: ${v}` : "Status removido"); }} rotulo="Status da proposta" testid="status" /></div>
        <div><label className="lab" htmlFor={"pr-" + chave}>Meu preço (R$/kg)</label><input className="inp num" id={"pr-" + chave} data-w="preco" inputMode="decimal" placeholder={r ? "ex.: " + (Math.round(r * 90) / 100).toFixed(2).replace(".", ",") : "ex.: 45,00"} value={preco} onChange={(e) => { setPreco(e.target.value); salvar.push(["preco", e.target.value]); }} onBlur={salvar.flush} /></div>
        <div className="full"><label className="lab" htmlFor={"rs-" + chave}>Responsável</label><input className="inp" id={"rs-" + chave} data-w="resp" value={resp} placeholder="Quem cuida desta proposta" onChange={(e) => { setResp(e.target.value); salvar.push(["resp", e.target.value]); }} onBlur={salvar.flush} /></div>
        <div className="full"><label className="lab" htmlFor={"nt-" + chave}>Notas</label><textarea className="inp" id={"nt-" + chave} data-w="notas" value={notas} placeholder="Frete, amostra, contato do pregoeiro…" onChange={(e) => { setNotas(e.target.value); salvar.push(["notas", e.target.value]); }} onBlur={salvar.flush} /></div>
      </div>
      {c && (
        <div className="calc small" data-calc>
          {!precoN || precoN <= 0 ? (r ? <>Estimado pelo órgão: <b>{BRL(r)}/kg</b>{c._rk ? ` (${c._rk.main.t.toLowerCase()})` : ""}. Digite seu preço para ver a margem.</> : "Sem R$/kg calculável para esta licitação; compare pelo valor unitário dos itens.") : (
            <>
              Estimado: <b>{r ? BRL(r) + "/kg" : "—"}</b>{c._rk ? ` (${c._rk.main.t.toLowerCase()})` : ""} · Meu preço: <b>{BRL(precoN)}/kg</b>
              {m != null && <><br />Desconto sobre o estimado: <span className={"mg " + (m >= 0 ? "pos" : "neg")}>{PCT(m)}</span> {m >= 0 ? "(meu preço está abaixo do estimado ✓)" : "(meu preço está acima do estimado)"}</>}
              {mm && <><br />Minha margem estimada a esse preço: <span className={"mg " + (mm.m >= 0 ? "pos" : "neg")}>{PCT(mm.mp)}</span> ({mm.m >= 0 ? "lucro" : "prejuízo"} de ~<Contador valor={Math.abs(mm.lucro)} fmt={(x) => BRL0(x)} dur={0.5} />; custo {BRL(mm.custo)}/kg)</>}
              {c._rk && c._rk.outros.length ? <><br />Proposta aprox. (só {c._rk.main.t.toLowerCase()}): <b>{BRL0(precoN * c._rk.main.kg)}</b> para {KG(c._rk.main.kg)} (estimado {BRL0(c._rk.main.v * c._rk.main.kg)})</> : c.kg ? <><br />Proposta total aprox.: <b><Contador valor={precoN * c.kg} fmt={(x) => BRL0(x)} dur={0.5} /></b> para {c._parcial ? "≥ " : ""}{KG(c.kg)}{c.vcafe ? ` (estimado ${BRL0(c.vcafe)})` : ""}</> : null}
              {c.itens.some((i) => i.conferir && i.kgt != null) && <><br /><span className="muted">Atenção: há item com provável erro de unidade no edital (marcado "conferir"); confira o volume antes de usar este total.</span></>}
            </>
          )}
        </div>
      )}
      {follows(w) && <div style={{ marginTop: 10 }}><HoldButton className="btn sm" onConfirm={() => { setW(chave, { fav: false, status: "" }); toast("Saiu de Minhas propostas (preço e notas continuam guardados)"); }} testid="unfollow">Parar de acompanhar (segure)</HoldButton> <span className="tiny muted">tira a ★ e o status; preço e notas ficam</span></div>}
    </section>
  );
}

/* ---------------- itens */
function Itens({ c }: { c: PCompra }) {
  return (
    <section className="card">
      <h3>Itens de café ({c.itens.length})</h3>
      {c.itens.map((i, k) => <Item key={k} i={i} />)}
    </section>
  );
}
function Item({ i }: { i: PCompra["itens"][number] }) {
  const [aberto, setAberto] = useState(false);
  const long = i.espec.length > 280;
  return (
    <div className="item">
      <div className="item-h"><span className="n">Item {i.n}</span>{i.tipo}{i.cat ? ` · ${i.cat}` : ""}{i.emb ? ` · ${i.emb}` : ""}{i.nivel && <Nivel n={i.nivel} />}</div>
      <div className="kv num">
        <div><small>Quantidade</small><b>{i.qtd != null ? n0(i.qtd) : "—"} {i.un}</b></div>
        <div><small>kg por unidade</small><b>{i.kgu != null ? n3(i.kgu) + " kg" : "—"}</b>{i.kgu == null && i.kg_src && <div className="tiny muted">{i.kg_src}</div>}</div>
        <div><small>Total</small><b>{KG(i.kgt)}</b></div>
        <div><small>R$/kg est.</small><b>{BRL(i.rkg)}</b>{i.conferir && <> <Dica texto="Valor fora da faixa usual: provável erro de unidade no edital"><span className="badge b-warn">conferir</span></Dica></>}</div>
        <div><small>Valor unitário</small><b>{i.sig ? "Sigiloso" : BRL(i.vu)}</b></div>
        <div><small>Valor total</small><b>{i.sig ? "Sigiloso" : BRL(i.vt)}</b></div>
        <div><small>ME/EPP</small><b>{i.me || "—"}</b></div>
        <div><small>Situação</small><b>{i.sit || "—"}</b></div>
      </div>
      {i.tags.length > 0 && <div className="tags">{i.tags.map((t) => <span key={t} className="tag req">{t}</span>)}</div>}
      <p className={"spec" + (long && !aberto ? " clamp" : "")}>{i.espec}</p>
      {long && <button type="button" className="linkbtn" onClick={() => setAberto(!aberto)}>{aberto ? "Mostrar menos" : "Ver especificação completa"}</button>}
      {i.ed_trecho && <><div className="small muted" style={{ marginTop: 8 }}>No edital/TR, sobre este item:</div><blockquote>{i.ed_trecho}</blockquote></>}
    </div>
  );
}

/* ---------------- edital */
function Edital({ c }: { c: PCompra }) {
  const mr = useStore((s) => s.data!.marcas_ref);
  const st = edStatus(c);
  const tre = (c.trecho_edital || "").split(" || ").filter(Boolean);
  return (
    <section className="card">
      <h3><Termo t="Edital">Edital</Termo></h3>
      <p className="small ink2 row-flex" style={{ alignItems: "flex-start" }}><StatusMark estado={st.estado} /><span>{st.texto}</span></p>
      {(c.marcas || []).length > 0 && (
        <>
          <div className="small muted" style={{ margin: "10px 0 6px" }}>Marcas citadas como referência (aceitam “ou equivalente”):</div>
          <div className="tags">{c.marcas!.map((m) => <Dica key={m} texto={varejoTxt(mr, m) ? "Varejo, linha mais básica: " + varejoTxt(mr, m) : "Sem preço de varejo pesquisado"}><span className="tag">{m}{varejoTxt(mr, m) ? " · " + varejoTxt(mr, m) : ""}</span></Dica>)}</div>
          <p className="tiny muted" style={{ marginTop: 6 }}>Preços de varejo em supermercados online e categoria oficial da ABIC, pesquisa de {(mr?.pesquisa_em || "").split("-").reverse().join("/")}. A mesma linha varia até 2 vezes entre lojas.</p>
        </>
      )}
      {c.edital_lido && c.ed_tags.length > 0 && <><div className="small muted" style={{ margin: "10px 0 6px" }}>O edital menciona:</div><div className="tags">{c.ed_tags.map((t) => <span key={t} className="tag">{t}</span>)}</div></>}
      {c.ed_pz && <p className="small" style={{ marginTop: 8 }}>Prazo de entrega citado: <b>{c.ed_pz}</b></p>}
      {c.tags.length > 0 && <><div className="small muted" style={{ margin: "10px 0 6px" }}>Exigências na descrição dos itens:</div><div className="tags">{c.tags.map((t) => <span key={t} className="tag req">{t}</span>)}</div></>}
      {tre.length > 0 && !c.itens.some((i) => i.ed_trecho) && <><div className="small muted" style={{ marginTop: 10 }}>Trecho do edital/TR sobre o café:</div>{tre.map((t, i) => <blockquote key={i}>{t}</blockquote>)}</>}
    </section>
  );
}

/* ---------------- dados da compra */
function DadosCompra({ c }: { c: PCompra }) {
  const copiar = async (t: string) => { try { await navigator.clipboard.writeText(t); toast("Copiado"); } catch { toast("Não consegui copiar", "erro"); } };
  return (
    <section className="card">
      <h3>Dados da compra</h3>
      <dl className="dl">
        <dt>Objeto</dt><dd>{c.objeto}</dd>
        <dt>Órgão</dt><dd>{c._orgao}{c.unidade && nrm(c.unidade) !== nrm(c.orgao) ? <><br /><span className="small muted">{tcase(c.unidade)}</span></> : null}</dd>
        <dt>Esfera</dt><dd>{c.esfera}</dd>
        <dt>Prazo final</dt><dd><b>{fmtDate(c.fim)}</b></dd>
        <dt>Abertura</dt><dd>{fmtDate(c.abre)}</dd>
        <dt>Publicado</dt><dd>{fmtDate(c.publicado)}</dd>
        <dt>Onde enviar</dt><dd>{c.plat}</dd>
        {c.uasg && <><dt><Termo t="UASG" /></dt><dd>{c.uasg} <button type="button" className="linkbtn" onClick={() => copiar(c.uasg)}><ICopy size={12} /> copiar</button></dd></>}
        <dt><Termo t="Registro de preços" /></dt><dd>{c.srp}</dd>
        <dt>Orçamento sigiloso</dt><dd>{c.sig}</dd>
        <dt><Termo t="ME/EPP" /></dt><dd>{c.me}</dd>
        <dt>Chave PNCP</dt><dd>{c.chave} <button type="button" className="linkbtn" onClick={() => copiar(c.chave)}><ICopy size={12} /> copiar</button></dd>
        {(c.dup_group || []).length > 0 && <><dt><Termo t="Duplicata">Duplicata?</Termo></dt><dd>Possível duplicata de {c.dup_group.map((k, i) => <span key={k}>{i > 0 && ", "}<button type="button" className="linkbtn" data-goto={k} onClick={() => abrirDetalhe(k)}>{k}</button></span>)}{c.dup_of ? " (esta fica oculta por padrão)" : ""}</dd></>}
      </dl>
    </section>
  );
}

/* ---------------- licitação acompanhada que saiu dos dados */
function Sumida({ chave }: { chave: string }) {
  const w = useStore((s) => s.wf[chave]) || {};
  const r = w.ref || {};
  if (!temAnotacao(w)) { fecharDetalhe(); return null; }
  return (
    <>
      <div className="note">Esta licitação saiu do monitor (prazo encerrado, revogada ou suspensa). Suas anotações continuam aqui: atualize o status quando souber o resultado.</div>
      <MinhaProposta chave={chave} c={null} />
      <section className="card"><h3>Dados</h3><dl className="dl"><dt>Chave PNCP</dt><dd>{chave}</dd>{r.vcafe != null && <><dt>Valor estimado (café)</dt><dd>{BRL0(r.vcafe)}</dd></>}</dl></section>
    </>
  );
}

/* Vai para Ajustes e leva o foco ao campo pedido (piso do nível, meus custos). */
function irAjustes(seletor: string): void {
  navegar("ajustes"); // com o detalhe aberto, troca a entrada do histórico e fecha o painel
  window.setTimeout(() => {
    const el = document.querySelector<HTMLElement>(seletor);
    if (!el) return;
    el.scrollIntoView({ block: "center" });
    if (el.matches("input")) el.focus();
  }, 60);
}

export const urgDe = urg;
export const lerStore = () => store.get();
