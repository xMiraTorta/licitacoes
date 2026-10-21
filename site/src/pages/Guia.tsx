/* Guia da proposta: passo a passo com checklist (marcado pela POSIÇÃO do item: não reordenar) e "Sobre os dados". */
import { motion } from "motion/react";
import { useMemo, useState } from "react";
import { BRL, fmtDate, n0 } from "../lib/format";
import { MERCADO_VAREJO, REF_MIN, rkV } from "../lib/modelo";
import { setChecklist, useStore } from "../store";
import { SYNC_BRANCH } from "../sync/github";
import { HoldButton, SpringCheck } from "../ui/Controles";
import { Segmentado } from "../ui/Segmentado";
import { Termo } from "../ui/Tooltip";

export function Guia() {
  const [aba, setAba] = useState<"passos" | "sobre">("passos");
  return (
    <div className="page guia">
      <div className="page-h"><h1>Guia da proposta</h1><Segmentado rotulo="Seção" valor={aba} onChange={setAba} opcoes={[["passos", "Passo a passo"], ["sobre", "Sobre os dados"]]} /></div>
      {aba === "passos" ? <Checklist /> : <Sobre />}
    </div>
  );
}

function Checklist() {
  const data = useStore((s) => s.data)!;
  const done = useStore((s) => s.checklist);
  const stages = useMemo(() => {
    const st: { etapa: string; itens: [typeof data.checklist[number], number][] }[] = [];
    data.checklist.forEach((x, i) => { let s = st[st.length - 1]; if (!s || s.etapa !== x.etapa) st.push((s = { etapa: x.etapa, itens: [] })); s.itens.push([x, i]); });
    return st;
  }, [data]);
  const tot = data.checklist.length, ok = data.checklist.filter((_, i) => done[i]).length;
  const marcar = (i: number, v: boolean) => { const d = { ...done }; if (v) d[i] = 1; else delete d[i]; setChecklist(d); };
  const [atual, setAtual] = useState(0);
  return (
    <div className="guide">
      <aside className="g-side card pad" id="gside">
        <h3>Passo a passo</h3>
        <p className="small muted">Orientação geral tirada dos editais de café lidos. <b>Confira sempre o edital específico.</b> As marcações ficam salvas com as suas anotações.</p>
        <div className="prog" aria-hidden="true"><motion.div className="prog-fill" animate={{ width: (tot ? (ok / tot) * 100 : 0) + "%" }} transition={{ type: "spring", stiffness: 120, damping: 20 }} /></div>
        <div className="small num">{ok} de {tot} itens prontos</div>
        <ol className="g-steps">
          {stages.map((s, n) => { const d = s.itens.filter(([, i]) => done[i]).length; return (
            <li key={s.etapa} className={(d === s.itens.length ? "done" : "") + (n === atual ? " atual" : "")}>
              <button type="button" onClick={() => { setAtual(n); document.getElementById("etapa-" + n)?.scrollIntoView({ block: "start", behavior: "smooth" }); }}><span className="g-num">{d === s.itens.length ? "✓" : n + 1}</span><span>{s.etapa.replace(/^\d+\.\s*/, "")}</span><span className="num muted">{d}/{s.itens.length}</span></button>
            </li>
          ); })}
        </ol>
        <HoldButton className="btn sm" onConfirm={() => setChecklist({})} testid="clReset">Desmarcar tudo (segure)</HoldButton>
      </aside>
      <div className="g-main">
        {stages.map((s, n) => (
          <section key={s.etapa} className="stage card" id={"etapa-" + n}>
            <h3>{s.etapa} <span className="mono muted">{s.itens.filter(([, i]) => done[i]).length}/{s.itens.length}</span></h3>
            {s.itens.map(([x, i]) => {
              const p = x.freq != null ? Math.round(x.freq * 100) : null;
              return <SpringCheck key={i} marcado={!!done[i]} onChange={(v) => marcar(i, v)} rotulo={x.item} dica={x.dica} testid={"cl-" + i} extra={p != null ? <span className="pct"><b>{p}%</b> dos editais<span className="bar"><span style={{ width: p + "%" }} /></span></span> : undefined} />;
            })}
          </section>
        ))}
      </div>
    </div>
  );
}

function Sobre() {
  const data = useStore((s) => s.data)!, prep = useStore((s) => s.prep)!;
  const C = prep.compras, n = C.length, semK = C.filter((c) => !c.kg).length, semR = C.filter((c) => rkV(c) == null).length, dup = C.filter((c) => c.dup).length, dupH = C.filter((c) => c.dup_of).length;
  const naoPlat = C.filter((c) => c.plat.startsWith("Ver edital")).length, semEd = C.filter((c) => !c.edital_lido).length, co = data.coleta;
  const Card = ({ t, children }: { t: string; children: React.ReactNode }) => <section className="card pad sobre-card"><h3>{t}</h3>{children}</section>;
  return (
    <div className="sobre">
      <Card t="De onde vêm os dados"><p>{data.fonte}. São todas as compras com itens de café que estavam recebendo propostas na data da busca (pregões eletrônicos e dispensas), de órgãos federais, estaduais e municipais. Atualizado em <b>{fmtDate(data.gerado_em.slice(0, 16))}</b> (horário de Brasília), nos dias úteis de manhã.{co ? ` Na última coleta: ${n0(co.listadas || 0)} compras abertas verificadas, ${n0(co.candidatas || 0)} candidatas, ${co.falhas ?? 0} falhas.` : ""}</p></Card>
      <Card t="Como ler"><ul>
        <li><b>Prazo</b>: vermelho até 3 dias, amarelo até 7, verde acima disso. O contador conta até o fim do prazo de propostas, no horário de Brasília.</li>
        <li><b>Distância</b>: por estrada, de {prep.origem} até a sede do município, calculada com mapas do OpenStreetMap. É uma estimativa; o Google Maps pode dar alguns km de diferença.</li>
        <li><b>R$/kg estimado</b>: só aparece quando o peso da embalagem é inequívoco, e é separado por tipo de café. Preço típico, ordenação e gráficos usam só torrado e moído. Volume com “≥” é parcial (algum item sem peso).</li>
        <li><b>Categoria com *</b> veio do trecho do edital, porque a descrição do item era curta.</li>
        <li><b>Nova</b>: apareceu pela primeira vez desde a busca do dia útil anterior.</li>
        <li><b><Termo t="Duplicata">Duplicatas</Termo></b>: mesmo município, mesmo valor e mesmo dia de prazo, provavelmente a mesma compra publicada duas vezes. Por padrão fica só a versão mais completa, exceto se você acompanha a outra.</li>
      </ul></Card>
      <Card t="Nível de exigência e referências de preço"><ul>
        <li><b>Nível</b> (Sem categoria, Tradicional, Superior, Gourmet/especial) é lido do texto do item: categoria citada, selo ABIC/PQC, nota mínima de qualidade e classificação da bebida. Vale o maior nível que o texto indicar. Quando a descrição do item no PNCP não diz, o coletor usa o trecho do edital/TR sobre aquele item (a categoria aparece com *). Confira sempre o edital.</li>
        <li><b>Só café torrado</b>: entram só itens de café torrado e moído ou em grão. Solúvel, cápsula, café pronto, cestas e café cru ficam de fora (decisão de 18/10/2026).</li>
        <li><b>Nota mínima de qualidade</b> (0 a 10): faixas usadas pelos editais, vindas das Resoluções SAA-SP 28, 30 e 31/2007: Tradicional 4,5 a 5,9; Superior 6,0 a 7,2; Gourmet 7,3 a 10. Hoje a <a href="https://www.abic.com.br/certificacoes/" target="_blank" rel="noopener">ABIC</a> trata as categorias como estilos e mantém só o piso de 4,5 (abaixo disso é “Fora de Tipo”, como na <a href="https://www.in.gov.br/web/dou/-/portaria-sda-n-570-de-9-de-maio-de-2022-398971389" target="_blank" rel="noopener">Portaria SDA/MAPA 570/2022</a>, que define o mínimo legal mas não as categorias). Pontuação de 0 a 100 (ex.: 80 pontos SCA) é dividida por 10.</li>
        <li><b>Bebida</b> (classificação oficial do café cru, IN MAPA 8/2003): “mole” ou “apenas mole” conta como Superior, “estritamente mole” como Gourmet. “Tipo 6, bebida dura” e faixas como “mole a dura” são o café comercial (padrão do indicador CEPEA) e não sobem o nível.</li>
        <li><b>Preço típico do nível</b>: o R$/kg do meio entre os itens abertos do mesmo tipo e nível (metade das licitações paga mais, metade paga menos; mínimo {REF_MIN} itens). Compara licitações entre si; não é custo. “No típico” = até 10% de diferença. A <b>faixa comum</b> mostra onde fica a metade das licitações.</li>
        <li><b>Varejo</b>: preço médio em supermercados por estilo, ABIC, {MERCADO_VAREJO.data} (Tradicional {BRL(MERCADO_VAREJO.valores.Tradicional)}, Superior {BRL(MERCADO_VAREJO.valores.Superior)}, Gourmet {BRL(MERCADO_VAREJO.valores["Gourmet/especial"])} por kg). As marcas citadas nos editais têm preço pesquisado toda semana em 11 lojas online.</li>
        <li><b>Meu piso</b>: o preço mínimo que você digita em Ajustes. É gravado junto com as suas anotações.</li>
        <li><b>Pontos de atenção</b> citam a <a href="https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm" target="_blank" rel="noopener">Lei 14.133/2021</a> (arts. 41 e 42). Não são orientação jurídica.</li>
      </ul></Card>
      <Card t="Custo e margem (como é estimado)"><ul>
        <li><b>Margem</b> = (preço do órgão − custo) ÷ preço do órgão, no item principal, para o volume total da licitação. É estimativa para triagem; antes de dar lance, confira frete e grão com cotação real.</li>
        <li><b>Café verde</b> do nível pedido (meio da faixa), atualizado todo dia útil (7h13 e 18h47) com o fechamento do mercado físico: indicadores <a href="https://www.cepea.org.br/br/indicador/cafe.aspx" target="_blank" rel="noopener">CEPEA/ESALQ</a> (arábica e robusta, CC BY-NC 4.0) e classes de bebida do <a href="https://www.carvalhaes.com.br/cotacoes/cotacoes.asp" target="_blank" rel="noopener">Escritório Carvalhaes</a>, com a receita de blend das Resoluções SAA-SP 28, 30 e 31/2007 (Tradicional: até 40% de conilon com arábica rio; Superior: até 15% de conilon com arábica duro; Gourmet: arábica fino a cereja descascado). Café da sua fazenda entra pelo preço que você receberia vendendo. Você pode fixar o seu R$/saca em Ajustes.</li>
        <li><b>Torra e embalagem</b> terceirizadas (R$ 5/kg cada, informadas por você) e <b>perda de 18%</b> na torra (literatura: 13% a 20%).</li>
        <li><b>Frete</b> por entrega, o mais barato entre carga fracionada (fórmula ajustada em 42 cotações Jadlog saindo de Uberaba, 18/10/2026: R$ 180 + kg × (R$ 2,10 + R$ 0,23 a cada 100 km) + 0,8% do valor; erro médio 17%) e caminhão de 2 eixos (piso da ANTT, Res. 6.084/2026), mais 20% de folga. Registro de preços: 3 entregas.</li>
        <li><b>Imposto</b>: Simples Nacional, Anexo II, 1ª faixa, 4,5% (empresa que manda torrar o próprio café é indústria por encomenda; até R$ 180 mil de venda em 12 meses). Sem DIFAL para órgão de outro estado e sem substituição tributária do café torrado em MG. Confirme com o contador.</li>
        <li><b>Outros</b>: custo de esperar o pagamento 2,6% (1,5 mês × juro de capital de giro, Banco Central), perdas 1%, plataforma R$ 129 por licitação (Portal de Compras Públicas; Compras.gov.br é grátis), amostra de 2 kg e laudo (orçar: sem preço público).</li>
      </ul></Card>
      <Card t="Lacunas conhecidas"><ul>
        <li>{semK} de {n} sem volume em kg (pacote sem peso informado) e {semR} sem R$/kg.</li>
        <li>{naoPlat} sem plataforma identificada automaticamente (aparece “ver edital”).</li>
        <li>{semEd} sem edital lido (ainda não publicado no PNCP, documento escaneado ou falha ao baixar): só a descrição do item está disponível.</li>
        <li>{dup} marcadas como possível duplicata ({dupH} ficam ocultas por padrão).</li>
      </ul></Card>
      <Card t="Seus dados"><p>Favoritos, status, preços, responsável, notas, checklist, pisos e meus custos ficam guardados <b>sozinhos no seu GitHub</b>, numa área separada do site chamada “{SYNC_BRANCH}” (qualquer pessoa pode ver), e sincronizam entre celular e computador. Cada gravação fica no histórico do GitHub, de onde dá para recuperar versões antigas. Para gravar, cada aparelho precisa da sua chave de acesso uma vez: em Ajustes › Sincronização.</p></Card>
    </div>
  );
}
