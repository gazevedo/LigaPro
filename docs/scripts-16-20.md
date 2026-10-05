# Scripts 16 a 20

- **16 — Valor de mercado:** fórmula central configurável com força, idade, posição, últimas cinco notas, divisão, contrato restante e reputação. Recalculada após partidas, evolução de força, promoção, transferência, renovação, vencimento e envelhecimento; mudanças ficam em `player_market_value_history`. A curva e as faixas de preço foram revisadas pelo script 21; o potencial profissional foi removido pelo script 22.
- **17 — Torcida:** crescimento e satisfação por resultados, campanhas, títulos e movimentação entre divisões. Público considera preço, satisfação, reputação, importância e capacidade. A propensão inicial de comparecimento é 10% da torcida, para manter a bilheteria na escala econômica do projeto. Há histórico em `club_fan_history` e previsão de público na tela de bilheteria.
- **18 — Ranking e reputação:** ranking responde à divisão, classificação, últimos cinco resultados e títulos recentes; o peso dos títulos diminui a cada temporada. Reputação cresce lentamente pela história esportiva e pela torcida. Os campos aparecem na tela Clube, e o ranking tem histórico próprio.
- **19 — Copa Nacional:** competição paralela de jogo único, com participantes configuráveis (até 128 clubes, das cinco primeiras divisões por padrão), sorteio determinístico e folgas quando a quantidade não é potência de dois. Empates levam a 30 minutos de prorrogação e, se necessário, pênaltis com morte súbita. Disputas de pênaltis não contam como gols de jogo nem como minutos adicionais. Avanço, prêmios, campeão e troféu são persistidos; jogos aparecem no calendário e a fase no dashboard. Humanos herdam a participação ativa do bot substituído.
- **20 — Economia:** economia inspirada no Brasfoot com escala e periodicidade adaptadas ao nosso jogo. Humanos e bots novos recebem R$ 100.000. A receita fixa mensal é R$ 5.000 de patrocínio mais R$ 10.000 de TV. Os salários relativos usam força, idade, posição e estrelas, sem potencial, e a folha inicial é normalizada para R$ 13.500. Bilheteria e prêmios são variáveis; compras exigem caixa. Os prêmios por posição e multiplicadores das divisões seguem o script.

## Persistência e compatibilidade

Valores monetários permanecem em **centavos inteiros**, como na API e no mobile existentes. `balance` e `cash_balance` são mantidos juntos por atualização atômica. A folha, receitas, despesas, resultado mensal e saúde financeira aparecem no resumo financeiro.

Um mês do jogo continua sendo 1/12 da duração da temporada. O fechamento usa marcador único por clube/período, credita as duas receitas fixas e liquida salários de forma transacional. Partidas, temporadas e obrigações financeiras são processadas offline pela ordem das datas. Resultados e prêmios não são reaplicados ao repetir o processamento.

A inicialização acrescenta os campos ausentes aos clubes existentes e inicia suas receitas mensais. **Caixa e contratos existentes são preservados**; não há reinicialização financeira nem alteração retroativa dos salários contratados.

## Validação

Validação: 33 testes unitários do backend, 44 de integração e 21 mobile; Ruff, ESLint, TypeScript e verificação de whitespace. Nos testes, o processamento automático em tempo real é isolado, e o avanço offline é acionado explicitamente para evitar que o relógio dos cenários seja alterado em paralelo.

Testes relacionados cobrem mercado, torcida, ranking, contratos, finanças, concorrência, substituição de bots, copa completa, calendário, telas e finalização de temporada com recuperação após falha.

A projeção financeira de cinco temporadas mantém elencos fixos para verificar receitas, salários e ausência de duplicação. Uma projeção adicional inclui bilheteria e premiações, com crescimento controlado de torcida; a simulação de uma temporada completa valida a integração esportiva. Essas projeções isolam o balanceamento inicial e não substituem a futura IA completa de mercado dos bots.

A comparação com o commit `42922aa` cobriu **85 cenários × 20 sementes = 1.700 partidas** de 90 minutos: os resultados completos permaneceram iguais, inclusive eventos, estatísticas e snapshots.

Os scripts 21 a 25 complementam estas regras; consulte `scripts-20-25.md`.
