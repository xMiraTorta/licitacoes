/* Dicas ao passar o mouse (Radix) e termos do dia a dia das licitações explicados em uma linha
   (React Bits "Warm Tooltip": depois da primeira, as seguintes abrem na hora). */
import * as RT from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

export const GLOSSARIO: Record<string, string> = {
  "Pregão Eletrônico": "Disputa de preços pela internet: ganha quem oferece o menor preço e cumpre as exigências do edital.",
  Dispensa: "Compra direta sem disputa formal (valor pequeno ou caso previsto em lei). Costuma ser mais rápida.",
  SRP: "Registro de preços: o órgão registra o seu preço e vai comprando aos poucos, em várias entregas, por até 1 ano.",
  "Registro de preços": "O órgão registra o seu preço e vai comprando aos poucos, em várias entregas, por até 1 ano.",
  "ME/EPP": "Micro e pequena empresa. Muitas licitações são exclusivas ou dão preferência a elas; no Simples Nacional você se enquadra.",
  UASG: "Código da unidade compradora no Compras.gov.br. Serve para achar a licitação na plataforma.",
  PNCP: "Portal Nacional de Contratações Públicas: o site oficial onde todas as licitações são publicadas.",
  ABIC: "Associação dos torrefadores. O selo de pureza ABIC atesta que é só café; alguns editais exigem o selo ou um laudo equivalente.",
  PQC: "Programa de Qualidade do Café (ABIC): classifica o café por nota de bebida (Tradicional, Superior, Gourmet).",
  "Nota mínima": "Nota de qualidade da bebida, de 0 a 10 (Tradicional 4,5; Superior 6,0; Gourmet 7,3). O edital pode exigir um mínimo.",
  "Preço típico": "O R$/kg do meio entre as licitações abertas do mesmo tipo e nível: metade paga mais, metade paga menos.",
  "Faixa comum": "Onde fica a metade das licitações, tirando as mais baratas e as mais caras.",
  Margem: "O que sobra do preço depois de grão, torra, embalagem, frete, impostos e outros custos. Estimativa com os seus custos.",
  "Preço para empatar": "Preço em que o lucro é zero: abaixo dele é prejuízo.",
  "Edital": "Documento oficial com todas as regras da compra: o que, quanto, como entregar, documentos exigidos.",
  TR: "Termo de Referência: a parte do edital que descreve o produto e as exigências técnicas.",
  "Café verde": "Café cru, ainda não torrado, que você compra ou tira da fazenda. Perde cerca de 18% do peso na torra.",
  Sigiloso: "O órgão não divulgou quanto espera gastar. O valor só aparece na disputa.",
  "Vácuo": "Embalagem fechada sem ar: o café dura mais. Exigida por muitos editais.",
  Almofada: "Pacote comum com ar dentro: mais barato, validade menor.",
  Laudo: "Documento de um laboratório atestando a qualidade do café. Alguns editais exigem para habilitar.",
  Amostra: "O órgão pede uma quantidade do produto para avaliar antes de homologar o vencedor.",
  Homologado: "Resultado confirmado pelo órgão: a compra está fechada.",
  Duplicata: "A mesma compra publicada duas vezes no PNCP (mesmo município, valor e prazo). Fica só a versão mais completa.",
};

export function Provedor({ children }: { children: ReactNode }) {
  return <RT.Provider delayDuration={350} skipDelayDuration={600}>{children}</RT.Provider>;
}

export function Dica({ texto, children, lado = "top" }: { texto: ReactNode; children: ReactNode; lado?: "top" | "bottom" | "left" | "right" }) {
  if (!texto) return <>{children}</>;
  return (
    <RT.Root>
      <RT.Trigger asChild>{children}</RT.Trigger>
      <RT.Portal>
        <RT.Content className="tt" side={lado} sideOffset={6} collisionPadding={12}>{texto}</RT.Content>
      </RT.Portal>
    </RT.Root>
  );
}

/* Termo com explicação: <Termo t="SRP" /> ou <Termo t="SRP">registro de preços</Termo>. */
export function Termo({ t, children }: { t: string; children?: ReactNode }) {
  const d = GLOSSARIO[t];
  if (!d) return <>{children ?? t}</>;
  return <Dica texto={d}><span className="tt-term" tabIndex={0}>{children ?? t}</span></Dica>;
}
