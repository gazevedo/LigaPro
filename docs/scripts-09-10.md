Scripts 9 e 10

Disciplina: a disputa individual precede a falta; marcação, resultado da disputa e gravidade determinam a disciplina. Os modificadores iniciais são 0,75/1,00/1,35. Eventos distinguem amarelo, segundo amarelo e vermelho direto; os expulsos deixam a equipe ativa. Pênaltis usam serviço separado.

Calibração: `calibration-script-09.json` registra 10.000 jogos para cada marcação, com seis critérios aprovados. `calibration-script-09-regression.json` registra outros 460.000 jogos de base, estilos e matriz tática: sem combinação dominante. Média entre equipes iguais: 2,3707 gols e 26,59% de empates. Os relatórios dos scripts 6 e 7 pertencem às versões anteriores do motor.

Contratos: elenco inicial e profissionais legados recebem dois anos do jogo; a promoção da base cria contrato profissional. Salário inicial em centavos: máximo entre 1.000 e força × 100. A renovação aceita salário positivo e 1–5 temporadas. Uma temporada tem 12 meses; o período salarial fica salvo no contrato, preservando-o quando as regras mudam.

Salários vencidos são debitados uma única vez, inclusive após períodos offline. Renovação e transferência liquidam a parcela proporcional já trabalhada. Obrigações salariais podem deixar o saldo negativo; renovação e contratação exigem saldo para a folha mensal resultante. Empréstimos mantêm a folha no proprietário. Venda encerra o contrato anterior e cria o vínculo com o comprador, preservando salário e vencimento.

O fim do contrato libera o jogador, fecha empréstimos/anúncios/ofertas e ajusta as escalações sem inventar atletas. A aposentadoria encerra o vínculo. Contratos e histórico não são apagados. Livres aparecem no mercado e podem ser contratados durante as janelas já existentes.

APIs: `GET /api/players/{id}/contract`, `POST /api/players/{id}/contract/renew` e `POST /api/market/players/{id}/sign`; os dois POSTs recebem `{ "salary": 5000, "seasons": 2 }`. O financeiro exibe folha, custos individuais, custo restante e histórico salarial. A manutenção trata vencimentos antes das partidas na respectiva data simulada.
