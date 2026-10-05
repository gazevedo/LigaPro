# Scripts 11 a 15

- **11 — Potencial:** atributo interno entre a força atual e 100, com maior dispersão nos jovens. O treino respeita o teto individual; as respostas públicas exibem apenas uma indicação de desenvolvimento e a possibilidade de treinar. O potencial influencia o valor de mercado e a escolha de agentes livres por bots com orçamento disponível, limitada a uma contratação por temporada.
- **12 — Moral:** evolução após partidas, participação, resultados, gols, ausência prolongada, promoção e transferências. Valores entre 0 e 100; fatores de desempenho entre 0,94 e 1,04, configurados centralmente. A faixa normal é neutra.
- **13 — Entrosamento:** evolução pela continuidade da escalação, formação e tempo de integração. Mudanças e novas contratações reduzem o entrosamento; a integração individual limita o benefício disponível ao time. Fatores entre 0,92 e 1,04; a faixa normal é neutra.
- **14 — Estatísticas:** totais por jogador, clube e temporada, com agregado de carreira; partidas, titularidades, minutos efetivamente jogados, gols, cartões, pênaltis, defesas e jogos sem sofrer gols. Assistências têm estrutura preparada, sem atribuição fictícia. Rankings e partidas recentes estão disponíveis na tela de estatísticas.
- **15 — Notas:** notas individuais de 5 a 10 calculadas a partir das ações registradas e do resultado. O relatório apresenta os participantes que efetivamente entraram em campo. Reservas não utilizados e partidas decididas por WO não recebem estatísticas individuais fictícias.

Estatísticas, notas, moral e entrosamento são persistidos na mesma transação que conclui a partida. A proteção existente contra processamento duplicado também cobre esses registros. Jogadores antigos recebem os atributos ausentes na inicialização; partidas históricas não são recalculadas.

## Validação

- 33 testes unitários do backend.
- 29 testes de integração, incluindo concorrência, contratos, transferências, escalações e uma temporada completa de 380 partidas.
- 25 testes mobile, incluindo estatísticas, relatório, navegação, potencial e moral.
- Verificação de tipos do mobile, ESLint, Ruff e verificação de whitespace.
- Comparação contra o commit `0da0ce4`: 82 cenários, 20 sementes por cenário, total de 1.640 partidas. Com moral e entrosamento neutros, os placares e todas as estatísticas agregadas permaneceram iguais.

O commit `0da0ce4` contém os scripts 7 a 10 e foi enviado para `main`. As alterações dos scripts 11 a 15 foram preparadas depois desse commit.
