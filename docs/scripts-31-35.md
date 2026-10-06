# Scripts 31–35

- Crédito em três prazos, juros totais positivos, limite por receita/caixa/reputação/dívida, parcelas mensais e bloqueio por atraso. Investimentos e crédito não podem coexistir. Bots financiam somente necessidades imediatas da folha.
- Notícias derivadas de transferências, lesões, suspensões, títulos, movimentações financeiras, estádio, patrocínio, base e aposentadoria, com deduplicação por evento.
- Histórico imutável de temporadas, classificações, campeões, acessos, rebaixamentos, clubes, carreiras e recordes.
- Pós-jogo reúne eventos persistidos, estatísticas, notas dos participantes, bilheteria e consequências; navegação para jogador, classificação e próximo evento.
- `backend/scripts/simulation_season_runner.py` executa ligas completas de duas divisões com o motor de produção e gera JSON, Markdown e gráficos SVG.

As escalas contam temporadas **somadas entre seeds**: 10, 100 e 1.000 temporadas, com quatro universos independentes (250 temporadas consecutivas por seed no maior cenário), totalizando 760.000 partidas no cenário maior.

O modelo de estresse usa regras de carreira, salários, preços, patrocínio, bilheteria e movimentação esportiva. O relatório declara simplificações de negociação, fluxo de caixa, desgaste, torcida e infraestrutura; não substitui testes transacionais do backend. Nenhum parâmetro de balanceamento foi alterado a partir de percepção subjetiva.

Executar: `PYTHONPATH=backend python backend/scripts/simulation_season_runner.py`.

Validação: testes de crédito/histórico/pós-jogo, regressões de finanças e estatísticas, testes mobile, TypeScript e linters. Resultados de simulação em `reports/global-balance/`.
