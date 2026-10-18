# HANDOFF · licitacoes

- **Atualizado em:** 2026-10-18 (Dashboard, nível de exigência, Telegram novo; automação ativa na main)
- **Branch de trabalho:** `claude/confident-galileo-equwuz` · repositório `xMiraTorta/licitacoes` (renomeado pelo dono em 17/10/2026; site https://xmiratorta.github.io/licitacoes/). Merge automático autorizado (ver CLAUDE.md).
- **Commit de partida:** `bd38a7f` (main). Último commit relevante: ver `git log` da branch.

## Contexto (vindo do dono)
O projeto foi feito pelo agente "Grok Bot", que tinha: uma planilha, uma busca diária às 9h com aviso no bot do Telegram **@ComprasGovXBot**, e publicava o site com um login do GitHub (fluxo de dispositivo) na conta `xMiraTorta`. A cota do Grok acabou: **o gerador, a busca diária e o envio ao Telegram dele não estão disponíveis**. O primeiro aviso dele estava previsto para 19/10 e não deve chegar. Ele também tinha começado a ampliar o painel para outros CNAEs do dono, sem concluir.

CNAEs do dono: 1081-3/02 (torrefação e moagem de café, principal), 4611-7/00 (representante de matérias-primas agrícolas), 7490-1/04 (intermediação de negócios).

## Escopo aprovado
O dono autorizou implementar "o que for válido" e, em 17/10/2026, **fazer merge automaticamente** dos PRs (PR #1 mergeado nesta data). Ele revogou o acesso OAuth do Grok no GitHub (restam só GitHub CLI e VS Code) e **apagou o bot antigo; o novo bot é @LicitacoesGovernoBot**. Segredos do Telegram cadastrados pelo dono (confirmado pelo envio do aviso de falha do run #1). Não autorizado: ampliar para outros CNAEs.

## Sessão 18/10/2026 (2): Dashboard, preço × exigência, Telegram (pedido do dono)
Decisões do dono: referência = mediana do nível + "meu piso" por nível; Dashboard substitui a aba Painel e abre primeiro.
- **Fusos (pendência antiga) resolvida, sem mudança**: 22 editais de AM/MT/MS/RO/AC/RR lidos; 16 declaram horário de Brasília e o horário do PNCP bate (ex.: Jaru-RO 09h10); nenhum usa horário local para prazo; 6 sem trecho legível.
- **Compras grandes**: maior compra de café tem 561 itens (Itapirapuã Paulista-SP, mediana 49); `itens()` baixa os 561; o PNCP aceita página de 5.000. Risco descartado.
- **Nível de exigência** (`cafe.nivel`, `cafe.nota_qg`): categoria, selo ABIC/PQC, nota mínima (0-10; 0-100 vira /10; faixa usa o mínimo) e bebida (IN MAPA 8/2003). Refinado com pesquisa de fontes oficiais (relatório no fim desta seção): "mole a dura"/"tipo 6 bebida dura" não sobem nível; "grupo especial", "Melitta especial", "cor SCA 55" não são especial; "estritamente mole" = Gourmet. Novas exigências: "Sem PVA (grãos selecionados)", "Aceita conilon/blend". Distribuição em 18/10: Tradicional 199 itens, Sem exigência 90, Superior 60, Gourmet 22.
- **Referência** (`coletor/referencia.py` + `refPrecos` no site): mediana do R$/kg por tipo e nível (mín. 5 itens). Medianas de 18/10: Sem exigência R$ 66,75; Tradicional R$ 63,29; Superior R$ 68,44; Gourmet R$ 107,44. Réguas de mercado no site: varejo ABIC ago/2026 (Tradicional 49,50; Superior 66,94; Gourmet 102,38) e grão cru arábica CEPEA 16/10/2026 (R$ 1.601,25/saca ≈ R$ 32,55/kg torrado com 18% de quebra).
- **Site**: aba Dashboard (indicadores, preço × nível com faixas, melhores oportunidades, meu piso, prazos, mosaico do Brasil, exigências mais pedidas, tipos, plataformas, distância, funil); lista com "O que pedem" (tipo, nível, selos) e preço com ▲▼≈ vs mediana e "cobre meu piso"; filtros novos (nível, preço vs mediana, só as que cobrem o piso); detalhe abre com "Vale a pena?" e "O que pedem" com pontos de atenção da Lei 14.133 (arts. 41/42) e TCU (selo ABIC só com alternativa). Piso fica em `monitorLicitacoes.pisos.v1` e entra no backup.
- **Telegram**: cabeçalho com data, resumo (novas, valor, kg, abertas, fecham em 3 dias), grupos "Perto de você" e "Demais estados", cartão com nível, nota, R$/kg ▲▼ vs mediana do nível, prazo com dia da semana e link direto `#c=` para a licitação no monitor.
- Comando novo `python -m coletor reclassificar`: reaplica regras de texto ao data.json publicado sem chamar o PNCP (usado nesta sessão; data.json/index.html já publicados com nível).
- Fontes da pesquisa (não versionado; principais URLs na aba Sobre): Portaria SDA/MAPA 570/2022 (DOU), FAQ MAPA café torrado, ABIC certificações e cartilha 2026, Resoluções SAA-SP 28/30/31-2007 (via especificação da Prefeitura de SP), IN MAPA 8/2003, CEPEA, ITAL (embalagem), Lei 14.133/2021. Não confirmado: inteiro teor dos acórdãos do TCU (portal bloqueou), custo vácuo × almofada.

## Pendências futuras (pedido do dono, para depois desta etapa)
- **Módulo de análise de custo** por tipo/qualidade pedido: custo de compra do grão (mercado), torra/embalagem, frete até o órgão, impostos sobre o lucro etc., comparando com o preço estimado da licitação. Ao lado, comparativo com os **custos próprios do dono** (comprar o café, torrar e embalar; dados fornecidos por ele, da realidade local). Ponto de partida: réguas `MERCADO` do `index.html`, distâncias por estrada já calculadas, "meu piso" por nível. Antes de implementar: levar ao dono as fontes de preço (CEPEA é público; frete e impostos precisam de premissas dele) e custos de manutenção.

## Sessão 18/10/2026: revisão completa de bugs (pedido do dono)
Três revisões independentes (site, coletor, automação), cada achado reproduzido antes de corrigir e coberto por teste que falha no código antigo.
- **Segurança**: texto do PNCP com `</script>` quebrava a página e rodava código (reproduzido no Chromium). `publicar.embutir_no_html` escapa `</` e `<!--`.
- **Coletor**: valor que arredondava para 0 derrubava a publicação do dia; compra conhecida que some da listagem (paginação do PNCP por posição) agora é conferida pela chave em `/api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{seq}` (revogada/suspensa/404 sai; erro mantém a anterior); classificador perdia "Aquisição de café", "Pacote de café", "Produto: café" etc.; "1.000g" lido como 1 g; cache `sem_cafe.json` agora `{versao, itens}` com `VERSAO_REGRAS` (2); compra sem itens não entra no cache; `nova` recalculada para mantidas; duplicata visível ontem continua visível; página vazia no meio da listagem é erro; `ValidationError` sai com código 2.
- **Automação**: link do Telegram no agendamento saía `https://xMiraTorta.github.io//` (`github.event.repository` vazio em schedule); `git pull --rebase` antes do push; alerta de falha também em timeout/cancelamento e com texto neutro; `avisar.yml` com grupo de concorrência próprio. Reserva: confere de novo o `run_date` logo antes do push e nunca resolve conflito a favor da própria coleta.
- **Site**: atualização automática quebrava o painel aberto de compra encerrada e parava de salvar sem aviso; redesenho apagava o que estava sendo digitado; Esc logo após digitar perdia a nota; ★ na Agenda não mudava e o 2º clique desfazia; link direto + × saía do site; duplicata exigia fechar 2 vezes e apagava os filtros; propostas sumiam de "Minhas propostas" quando a compra encerrava (agora ficam como "Fora dos dados", editáveis, via campo `ref`); importar o data.json por engano marcava todo o checklist; CSV deixava texto virar fórmula; preço 0 ignorado sem aviso.
- **Coleta real de validação** (18/10, neste ambiente, numa cópia: dados publicados intactos para o Telegram de segunda avisar as novas do fim de semana): 20.911 listadas, 4.144 candidatas (cache zerado pela versão nova), 4.623 chamadas, 0 falhas, 35 min, 334 compras = as mesmas 334 publicadas. Só o cache novo (`versao` 2, 3.810 itens) foi para o repositório, para a coleta de segunda no GitHub não reverificar tudo.
- Fuso e compras grandes: verificados na sessão seguinte (ver acima).

## Sessão 17/10/2026 noite: decisões do dono e entregas
Decisões (perguntadas e respondidas): repositório **continua público** (Pages grátis; dados já são públicos); nome **"Monitor de Licitações"**; escopo **só café por enquanto**; **reserva no Claude Code** aprovada. Dono quer renomear o repositório para `licitacoes`: o agente não tem ferramenta para isso; o dono faz em Settings. O código não depende do nome (link do Telegram vem do workflow).
Entregue e testado (112 testes, coleta real com 0 falhas, 39 min neste ambiente):
- Distância por estrada desde Uberaba (OSRM, `coletor/distancias_uberaba.csv`), campo novo `dist_min`.
- Redesenho total do site: lista + painel lateral, Minhas propostas (quadro por status), Agenda, Painel, Guia com progresso, tema escuro, celular sem rolagem lateral. Chaves do navegador preservadas.
- Workflows `testes.yml` (PRs) e `avisar.yml` (avisos da reserva); coletor recupera velocidade após 429.
- Chaves do navegador com prefixo `monitorLicitacoes.*`; backup exportado `app:'monitor-licitacoes'`. O dono confirmou que não tinha dados salvos, então não há migração de formato antigo.
- Respostas ao dono: CNAEs 4611-7/00 e 7490-1/04 são intermediação, não permitem revenda em nome próprio (precisa CNAE de comércio, confirmar com contador). Varredura incremental: só ~1/3 mais rápida e com risco de perder compras, não implementada. Coleta no Claude Code: 12 a 39 min contra 59 min no GitHub; varia com o limite do PNCP, então o GitHub segue como principal.

## Feito e validado nesta sessão
1. **Testes** (`tests/`, pytest + Chromium headless, sem internet): página, dados, classificador, coletor. 106 testes passando.
2. **Proteção das anotações no navegador**: dado ilegível é copiado antes (nunca apagado em silêncio) + faixa de alerta; "Desfazer última importação".
3. **R$/kg por tipo de café**: card, mediana, ordenação e gráfico deixam de misturar solúvel (~R$150-300/kg) com torrado e moído (~R$65/kg); volume com "≥" quando falta peso. Duplicata com favorito/status nunca é ocultada.
4. **Coletor novo em Python** (`coletor/`), substituindo o gerador perdido. Validação contra a coleta real de 17/10/2026:
   - listagem completa: 20.866 compras abertas (pregão eletrônico + dispensa), 458 chamadas;
   - 4.054 candidatas, itens baixados sem nenhuma falha (4.057 chamadas, ~16 min);
   - **encontrou as 327 compras do painel original + 7 compras de café reais que ele não tinha** (ex.: SP R$ 347 mil);
   - tipo igual ao original em 463/464 itens, peso em 462/464, descrição em 463/464 (divergências conferidas: erros do original ou regra deliberada, ver "Decisões");
   - distância: 327/327 iguais (mesma base de municípios).
5. **Automação** `.github/workflows/atualizar.yml` (dias úteis 9h07 BRT). Inerte até estar na `main`.

## Decisões e motivos
- **Unidade oficial vence a descrição** no peso: item em "KG" com texto "pacote 500 g" é R$/kg pelo quilo (o original dava R$ 121/kg; o certo é R$ 60,60/kg).
- **Caixa/fardo**: peso só quando o texto diz quantos pacotes (10x500g; "com 20 unidades") ou quando o preço mostra que a caixa é um pacote (R$/kg resultante entre 25 e 400). Senão, em branco.
- **Item só é café se a descrição começa pelo produto café** (elimina muda de café, caqui café, cafeteira, moedor, "Ribeirão Café").
- **Campos do edital** (ed_tags, ed_pz, trecho, plataforma citada no edital, categoria com *) não são refeitos: o coletor não lê PDFs ainda; preserva os valores do original para compras conhecidas. Compras novas ficam com "edital não baixado".
- **Candidatas** = objeto da compra com palavra de alimento/copa/expediente + busca textual "café" + já conhecidas. Busca textual do PNCP sozinha é instável (cobriu só 202/327).
- **Cache** `coletor/cache/sem_cafe.json`: candidatas sem café não são baixadas de novo se não mudaram no PNCP (poupa ~3.700 chamadas/dia).
- **Travas**: aborta se a listagem falhar, se >5% dos itens falharem, ou se as abertas caírem >40% vs coleta anterior. `--forcar` ignora (botão manual do workflow).
- **Telegram**: manda resumo das novas (MG primeiro), ou uma linha "nenhuma nova hoje" (confirma que está vivo). Falha da coleta também avisa.
- Mantida a cópia dos dados dentro do `index.html` (abre offline, como o Grok prometeu). Custo: ~1,8 MB por visita.

## Execuções no GitHub Actions
- Run #1 (17/10/2026 15:53 BRT, manual, após merge do PR #1): **falhou de propósito pela trava**. O PNCP limitou o servidor do GitHub muito mais que o ambiente de testes (a listagem de pregões levou ~22 min e a página 15 de dispensas deu 429 cinco vezes). Nada foi publicado; o aviso de falha chegou ao Telegram (HTTP 200), o que confirma que os segredos do bot novo estão configurados.
- Run #2 (após a correção): **sucesso**. 59 min, 813 chamadas, 37 novas tentativas, 0 falhas, 334 compras; commit `9fd2701` na main, build do Pages pedido (HTTP 201), site no ar conferido com os dados novos; Telegram: 1 mensagem enviada ("nenhuma nova hoje", pois a 1ª carga foi no mesmo dia).
- Ajustes após o run #2: limite do job 180 min; agendamento às 8h07 BRT para o aviso chegar ~9h.
- Correção: intervalo entre chamadas dobra a cada 429 (0,3 s até 4 s), 7 tentativas com espera até 120 s, listagem com 2 threads; actions atualizadas (checkout@v5, setup-python@v6) por causa do aviso de Node 20.

## Problemas conhecidos / não verificado
- **Não verificado**: se o GitHub Pages está ativo e de qual branch; se commits do GITHUB_TOKEN disparam o build (o workflow pede o build pela API por garantia); Telegram real (sem token aqui).
- Acessos do Grok: revogados pelo dono em 17/10/2026 (OAuth do GitHub e bot antigo apagado).
- PNCP responde 429 em rajadas; o cliente espera e tenta de novo (40 recuperações na 1ª listagem com 4 threads; 0 com 3 threads + intervalo).
- Fuso: horários do PNCP são de Brasília (-03:00), conferido em 22 editais de AM/MT/MS/RO/AC/RR em 18/10/2026.
- `checklist` é marcado pela posição: não reordenar.
- `coffee_break` existe no JSON mas a página não mostra.
- Tentativas que falharam: busca textual do PNCP como fonte principal (paginação inconsistente); 4 threads na listagem (muitos 429).

## Testes executados (último resultado)
`.venv/bin/python -m pytest -q` → 106 passed (17/10/2026). Coleta real: ver seção abaixo.

## Coleta real pela linha de comando (17/10/2026)
| Rodada | Cache | Chamadas PNCP | Tempo | Resultado |
|---|---|---|---|---|
| 1ª | vazio | 4.467 | 22 min | 334 compras, 0 falhas |
| 2ª | 3.666 sem café | 967 | 13 min | 335 (1 falso positivo: kit cozinha infantil, corrigido) |
| 3ª (publicada na branch) | 3.808 sem café | 840 | 12 min | 334 compras = 327 originais + 7 novas, 0 falhas |

Observado: 429 em rajadas na listagem (todas recuperadas); busca textual do PNCP caiu por alguns minutos (páginas puladas, coleta seguiu). A listagem leva ~8 min com o intervalo atual.
Duplicatas: 321/327 iguais ao original; 5 pares sem valor com itens diferentes deixaram de ser agrupados (de propósito); 1 compra antes visível virou duplicata (protegida pela regra da página se tiver favorito/status).

## Alterações sem commit
Nenhuma ao final da sessão (conferir `git status`).

## Próximo passo concreto
**Atualização em 17/10:** PRs #1 e #2 mergeados, automação ativa e conferida. Próximo: acompanhar a execução agendada de segunda 19/10 (8h07) e o selo "Nova".

Texto original:
O dono decide sobre: (1) autorizar merge do PR na `main`; (2) revogar acessos do Grok; (3) token novo do Telegram como segredo `TELEGRAM_BOT_TOKEN` e o chat como `TELEGRAM_CHAT_ID`; (4) se vale ampliar para outros CNAEs. Depois do merge: rodar o workflow manualmente ("Run workflow") e conferir o site e o Telegram.

## Adoção pelo Claude Code local
```bash
git fetch origin claude/confident-galileo-equwuz && git checkout claude/confident-galileo-equwuz
python -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/playwright install chromium
.venv/bin/python -m pytest -q
```
Ler `CLAUDE.md`. Se o PR já tiver sido mergeado, partir da `main`.
