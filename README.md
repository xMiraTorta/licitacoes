# Licitações de Café · Café Bizinotto

Painel com as licitações públicas (pregões e dispensas) que estão comprando café no Brasil, para a Café Bizinotto (Fazenda Mumbuca, Sacramento-MG).

**Acesse:** https://xmiratorta.github.io/licitacoes-cafe/

- Fonte: PNCP – Portal Nacional de Contratações Públicas (dados públicos).
- Atualização: o coletor deste repositório (`coletor/`) roda pelo GitHub Actions nos dias úteis, por volta das 9h (horário de Brasília), e avisa no Telegram as licitações novas. A automação só funciona depois de ativada na branch `main`; veja `HANDOFF.md` para o estado atual.
- Favoritos, status, preços e notas ficam salvos só no seu navegador, nunca neste repositório. Use "Meus dados → Exportar" para fazer backup.

## Para desenvolver

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                       # testes (sem internet)
.venv/bin/python -m coletor coletar --novas novas.json   # coleta real no PNCP (~20 min na 1ª vez)
```

Instruções para agentes e detalhes de arquitetura: `CLAUDE.md`. Estado do trabalho: `HANDOFF.md`.
