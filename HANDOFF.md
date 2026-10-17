# HANDOFF · licitacoes-cafe

- **Atualizado em:** 2026-10-17
- **Branch de trabalho:** `claude/confident-galileo-equwuz` (criada pela plataforma a partir da `main`)
- **Commit de partida / último de implementação:** `bd38a7f` (main, "Atualiza licitações de café – 17/10/2026 11:39"). Nenhuma mudança funcional feita desde então.

## Objetivo atual e escopo aprovado
Etapa 0 (diagnóstico + documentação de continuidade). **Aprovado:** só criar `CLAUDE.md` e `HANDOFF.md`. **Não aprovado ainda:** qualquer mudança funcional. Aguardando o dono aprovar o plano abaixo.

## Origem do projeto
Criado por outro agente ("Grok Bot"), 3 commits em 17/10/2026 entre 11:32 e 11:39, autor `xMiraTorta`. O repositório só tem o site já gerado: `README.md`, `.nojekyll`, `index.html`, `data.json`. Não há `.github/workflows`, script de coleta, planilha ou configuração. **O gerador não está disponível.**

## O que existe e foi validado (teste no Chromium headless, 17/10/2026)
Legenda: [T] testado, [L] lido no código, [H] hipótese não verificada.

- [T] Página carrega sem erros de JS; 327 compras, 464 itens, 302 abertas sem duplicatas.
- [T] KPIs, chips rápidos (MG etc.), busca textual, visão cartões/tabela, abas Painel/Checklist/Sobre, layout celular (390 px).
- [T] Favorito, status, preço R$/kg, notas: salvos em `cafeBizinotto.meusDados.v1` e preservados após recarregar.
- [T] Checklist salvo em `cafeBizinotto.checklist.v1`. CSV gera 302 linhas com BOM e `;`. Importação JSON funciona.
- [T] `DATA0` embutido no HTML é idêntico a `data.json`.
- [L] Filtros: UF, tipo, categoria, embalagem, ME/EPP, modalidade, plataforma, distância, faixa de valor, favoritos, status, novas, urgentes, com R$/kg, ocultar duplicatas/encerradas. Contagens por faceta.
- [L] Urgência por dias de calendário (≤3 vermelho, ≤7 amarelo). Horários tratados como fixos em -03:00.
- [L] "Nova": usa `c.nova` do JSON; hoje todas são `false` (primeira carga, `run_date == seed_date`). Não testável até haver uma segunda coleta.
- [L] Duplicata: o gerador marca `dup_of`; a página oculta por padrão. Critério declarado: mesmo município, valor e data.
- [L] Importação mescla por `upd` (mais recente vence); checklist importado é somado.
- [H] Distância: linha reta de Sacramento até a sede do município; fonte das coordenadas desconhecida.
- [H] Categoria com `*`, plataforma "citada no edital" e leitura dos 200 editais vêm de heurísticas por palavra-chave do gerador; não auditadas.
- [H] README diz "atualizado automaticamente nos dias úteis ~9h". **Nada neste repositório comprova isso.** Os 3 commits foram num sábado, com minutos de diferença, o que parece execução manual. Provavelmente não haverá atualização.
- [H] `wf0` (vazio em todas) e os nomes "Interesse", "Status da proposta", "Meu preço R$/kg" sugerem que o gerador lia uma planilha do dono.

## Problemas comprovados
1. **Dados salvos corrompidos são apagados em silêncio** [T]. Se o JSON do `localStorage` estiver inválido, a página começa vazia e o primeiro clique sobrescreve tudo, sem aviso. (`lget` em `index.html` linha 443.)
2. **R$/kg da compra mistura tipos de café** [T]. Ex.: `77402196000175-1-000046/2026` mostra R$ 300/kg porque só o item solúvel tem peso; o item torrado e moído (o relevante) não tem. A mediana, a ordenação e o gráfico de R$/kg misturam solúvel (~150 a 300) com torrado e moído (~60).
3. **Volume sem "≥" quando há item sem peso** [T]. 3 compras (`75458836000133-1-000147`, `03165607000110-1-000137/138`) com cápsulas sem peso aparecem com volume "completo".
4. **Checklist marcado pela posição** [L]. Se a lista mudar de ordem numa atualização, as marcações caem nos itens errados.
5. **Dados duplicados** [T]. Os 860 KB de dados estão no HTML e no JSON; quem abre baixa ~1,8 MB. Cada atualização precisa reescrever os dois.
6. **Falha ao buscar `data.json` é silenciosa** [L] (`checkUpdate`, catch vazio). Aceitável offline, mas também esconde JSON quebrado.
7. Preço "1.000" sem vírgula vira 1,00 [L]. Detalhe menor.
8. `coffee_break` (19 registros) existe no JSON mas a página não usa [L].
9. 3 itens marcados `conferir` (R$/kg 9 a 22, provável erro de unidade no edital) [T]. A página já avisa.

## O que falta para reproduzir coleta/atualização
- Código do gerador (não existe aqui). Precisa ser reconstruído do zero se o dono aprovar.
- Regras exatas do agente anterior: palavras-chave de busca, filtro de "café", cálculo de kg, detecção de duplicata, coordenadas dos municípios, leitura de editais.
- Acesso à API pública do PNCP a partir deste ambiente: **não testado** ainda.
- Onde rodar a automação (GitHub Actions é o candidato óbvio e gratuito) e permissão do dono para publicar na `main`.
- Confirmar no GitHub se o Pages está ativo e de qual branch (não verificado).

## Plano proposto (aguardando aprovação)
1. **Testes de proteção** (sem mudar o site): script Playwright + checagens Python dos cálculos e da persistência, com dados locais. Teste: rodar e ver tudo verde.
2. **Proteger os dados do dono**: não apagar dados corrompidos (guardar cópia e avisar), backup automático antes de importar. Teste: o cenário de corrupção acima.
3. **Correções de cálculo na página**: R$/kg e mediana por tipo (ou só torrado e moído), "≥" quando faltar peso. Teste: casos citados.
4. **Gerador próprio em Python** (só após aprovação): coleta do PNCP com limites, logs e validação; recusa publicar se a coleta vier menor que o esperado; mantém as mesmas `chave`s e campos.
5. **Automação** (GitHub Actions) e decisão sobre tirar a cópia dos dados do HTML. Exige autorização para publicar.

## Decisões tomadas
- Usar a branch da plataforma `claude/confident-galileo-equwuz`, sem criar outra.
- Etapa 0 só com documentação; script de teste ficou fora do repo até aprovação (fica para a etapa 1).

## Testes executados
- Smoke test Playwright (carregar, filtrar, buscar, favoritar, editar, recarregar, CSV, importar, abas, celular): passou, 0 erros de console.
- Validação Python de somas (`vcafe`, `kg`, `kgt`, `rkg`): diferenças explicadas por cestas separadas (`vcesta`) e arredondamento, exceto os itens 2 e 3 acima.
- Teste de corrupção do `localStorage`: confirmou perda de dados (problema 1).

## Alterações sem commit
Nenhuma (após o commit desta documentação).

## Próximo passo concreto
Dono aprovar (ou ajustar) o plano. Se aprovado, começar pela etapa 1 (testes).

## Adoção pelo Claude Code local
```bash
git fetch origin claude/confident-galileo-equwuz
git checkout claude/confident-galileo-equwuz
```
Ler `CLAUDE.md` e este arquivo. Não é preciso instalar nada para abrir o site; para testes, Node + Playwright (ou `pip install playwright` numa `.venv`).
