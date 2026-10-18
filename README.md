# Monitor de Licitações

Monitor de compras públicas para encontrar oportunidades de venda ao governo. Foco atual: **café** (torrado e moído, em grão, solúvel, cápsulas e cestas que incluem café), em pregões eletrônicos e dispensas de todo o Brasil.

**Site:** https://xmiratorta.github.io/licitacoes/

## O que ele faz

- Lista todas as compras com propostas abertas no **PNCP** (Portal Nacional de Contratações Públicas), encontra as que têm café e calcula o volume em kg, o R$/kg estimado e a distância por estrada a partir de Uberaba-MG.
- Mostra tudo num painel com filtros, agenda de prazos, quadro "Minhas propostas" (status, preço, notas) e um guia passo a passo da proposta.
- Atualiza sozinho nos dias úteis de manhã e avisa as licitações novas no Telegram.
- Favoritos, status, preços e notas ficam **só no navegador** de quem usa (nada disso vai para o repositório). Use "Meus dados → Exportar backup".

## Como funciona

```
GitHub Actions (seg-sex 8h07) ──> coletor/ (Python) ──> PNCP (APIs públicas)
        │                              │
        │                              └─> data.json + index.html (dados embutidos)
        ├─> commit na main ──> GitHub Pages (site)
        └─> Telegram (licitações novas, ou alerta de falha)

Reserva: tarefa agendada do Claude Code às ~10h40, só age se a atualização do dia falhou.
```

Travas de segurança: se a coleta vier incompleta (erro na listagem, muitas falhas, queda brusca no número de compras), nada é publicado e o site mantém os dados anteriores.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `index.html` | O site inteiro (HTML, CSS, JS) com uma cópia dos dados na linha `const DATA0 = ...` |
| `data.json` | Dados publicados (mesmo conteúdo do `DATA0`) |
| `coletor/` | Coleta no PNCP, classificação dos itens de café, montagem, publicação e aviso no Telegram |
| `coletor/distancias_uberaba.csv` | Km e tempo de viagem por estrada desde Uberaba (OpenStreetMap, calculado uma vez) |
| `coletor/cache/sem_cafe.json` | Compras já verificadas sem café (não são baixadas de novo) |
| `tests/` | Testes automáticos (sem internet), inclusive do site em navegador |
| `.github/workflows/` | Atualização diária, testes e envio de avisos |

## Para desenvolver

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium                  # navegador para os testes do site
.venv/bin/python -m pytest -q                          # todos os testes
.venv/bin/python -m coletor coletar --novas novas.json # coleta real (15 a 60 min)
python -m http.server 8765                             # ver o site em http://localhost:8765
```

Instruções para agentes de IA: `CLAUDE.md`. Estado atual do trabalho: `HANDOFF.md`.

## Fontes e limites

- Dados: PNCP (pncp.gov.br), públicos. Classificação do café, peso das embalagens e plataformas são **inferidos** do texto dos itens e podem ter erros; confira sempre o edital.
- Distâncias: OSRM sobre OpenStreetMap, estimativa por estrada (pode diferir alguns km do Google Maps).
- Municípios: base IBGE de [kelvins/municipios-brasileiros](https://github.com/kelvins/municipios-brasileiros) (MIT).
