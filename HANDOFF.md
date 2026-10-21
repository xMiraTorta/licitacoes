# HANDOFF · licitacoes

- **Atualizado em:** 2026-10-21, depois do PR #23 (revisão de UI/UX). `CLAUDE.md` tem a arquitetura, os contratos e as regras; aqui ficam o **estado**, as **pendências**, o que já foi **verificado** e o **histórico**.
- **Repositório:** `xMiraTorta/licitacoes` (público) · site https://xmiratorta.github.io/licitacoes/ · `main` = site no ar (commit `0c7e2bd`) · branch de trabalho `claude/confident-galileo-equwuz`, recriada a partir da `main` depois de cada PR mesclado.
- **Como trabalhar:** branch → `pytest -q` → PR → merge automático (autorizado pelo dono em 17/10/2026) → conferir o site no ar → contar ao dono em português simples. Alterações sem commit ao fim da última sessão: nenhuma.

## 1. Estado atual (21/10/2026)

### O que roda sozinho
| O quê | Quando (Brasília) | Onde | Resultado |
|---|---|---|---|
| Coleta no PNCP + aviso no Telegram | dias úteis 8h07 (45 a 60 min, limite 90) | `atualizar.yml` | commit do `data.json` na `main`, pedido ao `pages.yml`, mensagem no bot @LicitacoesGovernoBot (novas ou "nenhuma nova") |
| Café verde (CEPEA + Carvalhaes) | dias úteis 7h13 e 18h47 | `precos.yml` | `coletor/mercado.json` (fila própria, nunca o `data.json`); só a das 18h47 publica o site, a das 7h13 deixa para a coleta das 8h07 |
| Varejo das marcas (11 lojas) | segunda 7h13 | `precos.yml` | `coletor/marcas_cafe.json` |
| Publicação do site | a cada push na `main` que mude `site/`, `data.json` ou os JSONs de preço/custo (1 a 2 min) | `pages.yml` | monta o site, embute preços, marcas e custos no `data.json`, publica no Pages |
| Testes | em todo PR, menos os só de documentação | `testes.yml` | vitest + build + pytest |
| Reserva | dias úteis ~10h40 | tarefa agendada do Claude Code na nuvem (`trig_01VMXTo6cUpqkoMReBFSrWFd`) | se a coleta do dia falhou ou foi cancelada, coleta na nuvem, push na `main` com `avisos/pendentes.json`, `avisar.yml` manda o Telegram |

Falha em `atualizar.yml`, `precos.yml` ou `pages.yml` avisa no Telegram. Segredos do bot cadastrados pelo dono (confirmado por envio real).

### Dados publicados (`data.json` da `main`)
- Coleta de 20/10/2026 12:38, publicado 21:49 (preços embutidos): 244 compras (13 duplicatas ocultas), 231 abertas, 229 com edital lido. Coleta: 20.079 compras lidas no PNCP, 4.063 candidatas, 750 itens baixados, 1.296 chamadas, 3 falhas, 45 min.
- Café verde: cotação Carvalhaes de 20/10, histórico com 3 cotações (gráfico do Mercado cresce a cada atualização). Varejo: 32 marcas, pesquisa de 19/10. Custos padrão: `coletor/custos.json`. Checklist do guia: 27 itens (ordem fixa, marcado pela posição).

### Última verificação (21/10/2026, PR #23)
- `pytest -q` → 349 passed (82 de página no Chromium, 267 do coletor e dos dados) · `npm test` 14 · `tsc --noEmit` ok · `testes.yml` verde no PR · `pages.yml` execução 12 com sucesso.
- Site no ar aberto no Chromium a 1440 px e 390 px: todas as abas sem erro de JavaScript; lista sem corte no celular; paleta opaca; gráfico do café verde e marcas citadas conferidos com os dados do dia.

## 2. Pendências

### Do dono (só ele pode fazer)
- Colar a chave de acesso do GitHub em cada aparelho (Ajustes › Sincronização, passo a passo na tela). Sem isso as anotações ficam só no aparelho.
- Orçar o laudo de qualidade (sensorial + microscopia) e informar em Ajustes › Meus custos (hoje R$ 0).
- Pedir 2 a 3 cotações de frete com o CNPJ para recalibrar a fórmula (R$ 180 + R$ 2,10/kg + R$ 0,23/kg a cada 100 km + 0,8% do valor; erro médio 17% nas 42 cotações Jadlog de 18/10).
- Confirmar com o contador: Simples Nacional Anexo II, 1ª faixa (4,5%); CNAE de comércio para revender em nome próprio (4611-7/00 e 7490-1/04 são intermediação).
- Decisão aberta: "premium" e "1ª qualidade" não contam como Superior (termo comercial, sem padrão oficial). Mudar só se ele pedir.

### Técnicas (para depois; nada bloqueia o uso)
- Arrastar cartões no celular: decidido em 21/10 que fica o menu de status.
- Pacote do site com ~230 KB gzip, sem divisão em partes.
- Fila `atualizar-licitacoes`: um "Run workflow" manual durante a coleta pode cancelar a execução pendente em silêncio; a reserva cobre.
- Edital: PDF escaneado sem OCR (revisão manual fica em `edital_status`); RAR antigo "sólido" (RAR3/4) não abre na libarchive, fica "sem texto legível" com aviso no log; a coleta lê até 40 editais por dia.
- CEPEA bloqueia os servidores do GitHub (403 do Cloudflare): o robusta usa o último valor gravado com a data dele; Carvalhaes atualiza o resto.
- `coffee_break` existe no JSON e a página não mostra.
- Não autorizado: ampliar para outros CNAEs ou produtos.

## 3. Limites e fatos já verificados (não refazer)
- Fuso: os horários do PNCP são de Brasília; 22 editais de AM/MT/MS/RO/AC/RR conferidos, nenhum usa hora local.
- Maior compra de café: 561 itens; o PNCP aceita página de 5.000. Sem risco.
- PNCP limita rajadas (429), muito mais nos IPs do GitHub: coleta leva 45 a 60 min lá e 12 a 39 min no Claude Code; 3 chamadas simultâneas e desaceleração automática (`coletor/pncp.py`). Busca textual do PNCP sozinha é instável (cobriu 202 de 327); varredura incremental não vale (um terço mais rápida, risco de perder compras); 4 threads na listagem dão muitos 429.
- Sincronização sem chave: o GitHub limita 60 consultas por hora por endereço (403/429 em rede de celular ou escritório); não é erro de chave e o site não acusa.
- Reserva de 20/10 não rodou por limite de uso do plano Claude (a coleta do GitHub tinha dado certo).
- Varejo automático: as 11 lojas usam VTEX com busca pública em JSON (Mambo, Giassi, Covabra, Savegnago, Bistek, Super Muffato, Zona Sul, GBarbosa, Prezunic, Coop, Mercantil Rodrigues; Tenda 404). Distância por estrada: OSRM (Google Maps e Waze descartados: pago ou sem API).
- Origem do projeto: agente "Grok Bot" (planilha, busca diária, bot @ComprasGovXBot), cota esgotada; acessos revogados pelo dono em 17/10 e bot antigo apagado. CNAEs do dono: 1081-3/02 (principal), 4611-7/00, 7490-1/04.

## 4. Regras técnicas do coletor (decisões com motivo)
- **Peso**: unidade oficial vence a descrição (item em "KG" com texto "pacote 500 g" é R$/kg pelo quilo). Caixa/fardo só tem peso quando o texto diz quantos pacotes ou quando o preço mostra que a caixa é um pacote (R$/kg entre 25 e 400); senão fica em branco. "1.000g" é 1 kg. Varejo: "10x500g", "c/ 2 unidades", "Leve 3 Pague 2" multiplicam.
- **O que é café**: a descrição começa pelo produto café (elimina muda de café, caqui café, cafeteira, "Ribeirão Café"); prefixos de licitação ("ITEM EXCLUSIVO PARA ME/EPP", "COTA PRINCIPAL 75%", "GÊNEROS ALIMENTÍCIOS NÃO PERECÍVEIS") são ignorados; "isento de grãos pretos" e "pronto para consumo" não fazem o café virar cru ou bebida. Só itens "Em andamento" no PNCP. Mudou a regra: suba `VERSAO_REGRAS` (hoje 3).
- **Candidatas**: objeto com palavra de alimento, copa ou expediente + busca textual "café" + compras já conhecidas. Cache `sem_cafe.json` poupa ~3.700 chamadas por dia. Compra conhecida que some da listagem é conferida pela chave (revogada, suspensa ou 404 sai; erro mantém a anterior; lista de itens vazia é tratada como falha).
- **Travas** (`publicar.py`): aborta se a listagem falhar, se mais de 5% dos itens falharem ou se as abertas caírem mais de 40%; `--forcar` ignora (botão manual). Infinity e NaN são recusados. Gravação atômica dos três JSONs.
- **Nível de exigência** (`cafe.nivel`, `cafe.nota_qg`): categoria citada, selo ABIC/PQC, nota mínima (0 a 10; 0 a 100 vira /10; faixa usa o mínimo; "Nota Técnica 5/2023" não é nota) e bebida (IN MAPA 8/2003: "mole" e "apenas mole" = Superior, "estritamente mole" = Gourmet; "mole a dura" e "tipo 6 bebida dura" não sobem nível). "Premium", "grupo especial", "Melitta especial", "não será aceito extraforte" não contam. Categoria e nota do edital prevalecem sobre a descrição do item (marcadas com `*`).
- **Referência de preço**: preço típico (mediana) por tipo e nível com mínimo 5 itens (`REF_MIN`), 2 casas; mesma regra em `coletor/referencia.py` e `refPrecos` (site). Margem: mesma regra em `coletor/custos.py` e `Calculadora.margem` (site); frete pelo mais barato entre fracionado (fórmula Jadlog) e caminhão.
- **Edital**: TR primeiro; PDF (inclusive AES), DOCX, ODT, RTF, .doc, ZIP, RAR; releitura que falha não apaga leitura boa (vai para `edital_tentativa`); leitura parcial (download com falha) não grava `edital_ver`, então relê no dia seguinte; "cesta" citada de passagem (pesquisa de preços, nome de fornecedor) não tira a compra.
- **Telegram**: resumo das novas (MG primeiro) ou "nenhuma nova hoje"; 1,1 s entre mensagens e `retry_after` respeitado; 429 com HTML (Cloudflare) espera 5 s; links `#c=<chave>` abrem a licitação no site.
- **Duplicatas**: mesmo município, valor e dia de prazo; fica a versão mais completa, exceto se o dono acompanha a outra. Pares sem valor com itens diferentes não são agrupados.

## 5. Decisões do dono (registro)
- **17/10**: repositório continua público; nome "Monitor de Licitações"; só café por enquanto; merge automático dos PRs; reserva no Claude Code; repositório renomeado para `licitacoes` por ele (pasta, sessão e repositório com o mesmo nome).
- **18/10**: cestas básicas e kits fora, mesmo com café em item próprio; compras encerradas nunca aparecem; só café torrado (solúvel, cápsula, pronto e cru fora); o edital é a fonte principal; anotações gravadas no GitHub (branch `dados`, públicas) e fim do CSV e do exportar/importar; "Sem exigência" virou "Sem categoria"; site em React com visual próprio, escuro por padrão (mockup aprovado em 3 rodadas); Pages publicado por Actions (ele trocou a fonte do Pages); Telegram curto e profissional, sem exclamação, no máximo 1 emoji; café verde atualizado todo dia útil (o preço muda todo dia); referência = preço típico do nível + "meu piso" por nível; Dashboard (hoje "Hoje") abre primeiro.
- **21/10**: minutos do Actions (o repositório é público, logo não contam na cota; mesmo assim: coleta com limite de 90 min, testes não rodam em PR só de docs, rodada das 7h13 não publica o site); marcas de removido ficam para sempre; preços de mercado fora do `data.json` (fila própria); filtro "além de N km"; os 3 lotes da revisão de UI/UX ("Implemente tudo"), sem arrastar no celular.

## 6. Histórico por sessão (mais novo primeiro)
- **21/10 (12), PR #25**: minutos do Actions em outubro (17 a 21/10): coleta 174 min em 4 execuções (43 a 59 min cada), testes 51 min em 29 PRs, publicação 16 min, preços 7 min; o GitHub arredonda cada job para o minuto cheio. Em repositório público os minutos não contam na cota de 2.000 (documentação do GitHub). Ajustes: limite da coleta 180 → 90 min, `testes.yml` ignora PR só de documentação, rodada das 7h13 do `precos.yml` não publica o site. Coleta no computador do dono (GitHub só de reserva) ficou como opção; runner próprio descartado (repositório público).
- **21/10 (11), PR #23**: revisão de UI/UX a partir de fotos de todas as telas (computador e celular, escuro e claro). Lote 1, erros: celular cortava números (`minmax(0,1fr)`), "Melhores" sem lucro no celular, paleta transparente (`contentClassName` do cmdk), rótulos de eixo cortados, avisos repetidos viram ×N (máximo 2), `tiposTexto`, "60 a 60", KPI de propostas por etapa. Lote 2, organização: cartões pelo topo, `Faixas` em grade única, `Hbar` com número na primeira linha, "Vale a pena?" em lista, lista sem travessões, filtros compactos no celular, rodapé do cartão fixo, Mercado junta Sem categoria com Tradicional e agrupa Carvalhaes, textos sem jargão, checklist sem traço. Lote 3, interatividade: quadro de propostas em colunas com arrastar e soltar (computador), Exigências e Embalagem clicáveis (filtro `selos`), cabeçalhos ordenáveis, dica do mapa, valores no fim das linhas do gráfico. Revisão por 4 agentes antes do merge: 17 achados corrigidos (cartão mais largo que a coluna, arrasto cancelando o "Parar de acompanhar", Exigências com conta diferente da lista, rótulos internos do filtro, dica fora da tela, status desconhecido, entre outros). 36 testes novos.
- **21/10 (10), PRs #19 a #22**: revisão geral de bugs com três leituras independentes e teste de fumaça: 19 correções no site (página em branco sem dados, link `#c=` quebrado, G G, "1.800" lido como 1,8, perda de 100%, atualização zerando a lista, `publicado_em`, hora em UTC, campos sobrescritos por outro aparelho, "fecham em 7 dias" ia para 3 dias, entre outros), 14 no coletor (ZIP corrompido derrubava a coleta, download sem nova tentativa, café cru/bebida por engano, prefixos de ME/EPP, releitura sobrescrevendo leitura boa, Carvalhaes abaixo de R$ 1.000, multipacks do varejo, Infinity/NaN, 429 do Telegram, "Nota Técnica", gravação atômica) e na automação (pedido ao `pages.yml` sem 2xx falha, push com 3 tentativas, aviso do `pages.yml`). Três decisões resolvidas com o dono (seção 5).
- **18/10 (9), PRs #16 a #18**: site novo em React + Vite + TypeScript (mesmas chaves do navegador, sincronização portada 1:1, mapa IBGE com anéis e pontos, paleta Ctrl K, atalhos), publicação do Pages por Actions, Telegram enxuto, README visual, pasta renomeada. Depois de ver no ar: 403 sem chave não acusa mais "chave recusada".
- **18/10 (8)**: café verde 2 vezes por dia útil (7h13 e 18h47); site mostra a data da cotação.
- **18/10 (7)**: custo e margem por oportunidade: 3 pesquisas (`docs/pesquisas/`: grão por nível, frete, impostos e outros custos), `mercado.py`, `varejo.py`, `precos.yml`, `custos.py` + `custos.json`, margem na lista, no detalhe, em Minha proposta e em Meus custos. Primeira execução no GitHub: varejo ok, CEPEA bloqueado (tratado).
- **18/10 (6)**: cestas fora (23 compras), encerradas sempre fora, RAR5 e PDF protegido testados no GitHub, viabilidade do varejo automático confirmada.
- **18/10 (5)**: só café torrado (331 → 282 compras), leitor de edital (`edital.py`), leitura das 282 (239 automáticas, 23 sem especificação no documento, 4 escaneadas revisadas), marcas de referência (31 marcas com varejo pesquisado).
- **18/10 (4)**: anotações gravadas no GitHub (branch `dados`), Minhas propostas redesenhado, ícone com a bandeira, rolagens laterais removidas.
- **18/10 (3)**: itens cancelados fora (`situacaoCompraItem == 1`), "Sem categoria", termos simples (preço típico, faixa comum), mapa do IBGE, 2ª revisão de bugs (coletor e site).
- **18/10 (2)**: nível de exigência e nota mínima, referência por nível, Dashboard, Telegram com cartões, comando `reclassificar`; fuso e compras grandes verificados.
- **18/10 (1)**: 1ª revisão completa de bugs (segurança: `</script>` em texto do PNCP; coletor; automação; site) e coleta real de validação (334 compras, 0 falhas).
- **17/10 noite, PRs #2 a #8**: distâncias por estrada (OSRM), redesenho do site (lista + painel, Minhas propostas, Agenda, Painel, Guia), `testes.yml` e `avisar.yml`, prefixo `monitorLicitacoes.*` nas chaves do navegador.
- **17/10, PR #1**: testes (pytest + Chromium), proteção das anotações, R$/kg por tipo, coletor novo em Python validado contra a coleta original (as 327 compras + 7 que faltavam; 463/464 itens iguais), `atualizar.yml`. Execução 1 no GitHub falhou de propósito pela trava (PNCP limitou), execução 2 com sucesso (59 min, 334 compras, Telegram entregue).

## 7. Como continuar
```bash
git fetch origin main && git checkout -B claude/confident-galileo-equwuz origin/main
python -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/playwright install chromium   # na nuvem do Claude Code o Chromium já existe
cd site && npm install && cd ..
.venv/bin/python -m pytest -q      # 349 testes, sem internet
```
Para conferir que tudo está vivo: último `atualizar.yml` verde (Actions), mensagem do dia no Telegram, `publicado_em` do `data.json` no ar, site aberto sem erro no console. Comandos e caminhos: `CLAUDE.md`.
