# HANDOFF · licitacoes-cafe

- **Atualizado em:** 2026-10-17 (fim da sessão de nuvem 1; automação ativa na main)
- **Branch de trabalho:** `claude/confident-galileo-equwuz` · PR aberto: https://github.com/xMiraTorta/licitacoes-cafe/pull/1 (não fazer merge sem o dono)
- **Commit de partida:** `bd38a7f` (main). Último commit relevante: ver `git log` da branch.

## Contexto (vindo do dono)
O projeto foi feito pelo agente "Grok Bot", que tinha: uma planilha, uma busca diária às 9h com aviso no bot do Telegram **@ComprasGovXBot**, e publicava o site com um login do GitHub (fluxo de dispositivo) na conta `xMiraTorta`. A cota do Grok acabou: **o gerador, a busca diária e o envio ao Telegram dele não estão disponíveis**. O primeiro aviso dele estava previsto para 19/10 e não deve chegar. Ele também tinha começado a ampliar o painel para outros CNAEs do dono, sem concluir.

CNAEs do dono: 1081-3/02 (torrefação e moagem de café, principal), 4611-7/00 (representante de matérias-primas agrícolas), 7490-1/04 (intermediação de negócios).

## Escopo aprovado
O dono autorizou implementar "o que for válido" e, em 17/10/2026, **fazer merge automaticamente** dos PRs (PR #1 mergeado nesta data). Ele revogou o acesso OAuth do Grok no GitHub (restam só GitHub CLI e VS Code) e **apagou o bot antigo; o novo bot é @LicitacoesGovernoBot**. Segredos do Telegram cadastrados pelo dono (confirmado pelo envio do aviso de falha do run #1). Não autorizado: ampliar para outros CNAEs.

## Sessão 17/10/2026 noite: decisões do dono e entregas
Decisões (perguntadas e respondidas): repositório **continua público** (Pages grátis; dados já são públicos); nome **"Monitor de Licitações"** (não existe "Café Bizinotto"); escopo **só café por enquanto**; **reserva no Claude Code** aprovada. Dono quer renomear o repositório para `licitacoes`: o agente não tem ferramenta para isso; o dono faz em Settings. O código não depende do nome (link do Telegram vem do workflow).
Entregue e testado (112 testes, coleta real com 0 falhas, 39 min neste ambiente):
- Distância por estrada desde Uberaba (OSRM, `coletor/distancias_uberaba.csv`), campo novo `dist_min`.
- Redesenho total do site: lista + painel lateral, Minhas propostas (quadro por status), Agenda, Painel, Guia com progresso, tema escuro, celular sem rolagem lateral. Chaves do navegador preservadas.
- Workflows `testes.yml` (PRs) e `avisar.yml` (avisos da reserva); coletor recupera velocidade após 429.
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
- Fuso: horários do PNCP tratados como -03:00. Compras de AM/MT/MS/RO/AC/RR podem estar no horário local (hipótese não verificada; `municipios.csv` tem o fuso de cada município).
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
