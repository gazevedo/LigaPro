# Script 20 — Sistema Monetário e Economia dos Clubes

Objetivo: criar um sistema econômico inspirado no Brasfoot, mas adaptado à escala monetária do nosso jogo.

## 1. Caixa inicial

Todo clube novo, humano ou bot, inicia com:

STARTING_CASH = 100000

Valor:
R$ 100.000,00

## 2. Receita fixa mensal do nosso jogo

Por decisão de design:

MONTHLY_SPONSORSHIP = 5000
MONTHLY_TV_REVENUE = 10000

Receita fixa mensal:
R$ 15.000

Observação:
direitos de TV mensais não aparecem como fonte clássica documentada do Brasfoot. Mantemos TV como mecanismo próprio do nosso projeto.

## 3. Folha salarial inicial

A folha salarial inicial deve equivaler a aproximadamente 90% da receita fixa mensal:

R$ 15.000 × 0,90 = R$ 13.500

Configuração:

INITIAL_PAYROLL_TARGET_PERCENT = 0.90
INITIAL_PAYROLL_TARGET = 13500
PAYROLL_TOLERANCE = 0.03

A soma dos salários dos 25 jogadores deve ficar próxima desse alvo.

## 4. Fontes financeiras inspiradas no Brasfoot

Receitas:

- sponsorship
- tv_rights
- ticketing
- player_sale
- prize
- friendly_income
- other_income

Despesas:

- salary
- player_purchase
- stadium
- interest
- other_expense

O manual do Brasfoot documenta como fontes clássicas:

- venda de jogadores
- ingressos
- patrocínio
- amistosos

Prêmios também aparecem conforme avanço/classificação em competições.

## 5. Patrocínio

No Brasfoot documentado, patrocínio é definido conforme divisão e pode ser influenciado por reputação, sendo recebido no início da temporada.

No nosso jogo, para manter a economia mensal:

MONTHLY_SPONSORSHIP = 5000

Essa é uma adaptação deliberada.

## 6. Bilheteria

A bilheteria é variável:

ticketing_income = attendance × ticket_price

Regras:

- mandante recebe a renda na maioria dos jogos
- partidas de copa podem dividir renda futuramente
- capacidade do estádio limita attendance

## 7. Salários

A documentação técnica do Brasfoot 22/23 confirma que o salário é recalculado usando:

- força geral
- idade
- posição
- estrelas

No nosso jogo:

1. calcular salário relativo por jogador;
2. somar salários do elenco;
3. normalizar a folha para o alvo aproximado de R$ 13.500.

Não usar `potential` profissional.

## 8. Premiação por posição — Série A

1º  — R$ 80.000
2º  — R$ 40.000
3º  — R$ 20.000
4º  — R$ 18.000
5º  — R$ 17.000
6º  — R$ 16.000
7º  — R$ 15.000
8º  — R$ 14.000
9º  — R$ 13.000
10º — R$ 12.000
11º — R$ 11.000
12º — R$ 10.000
13º — R$ 9.000
14º — R$ 8.000
15º — R$ 7.000
16º — R$ 6.000
17º — R$ 5.000
18º — R$ 5.000
19º — R$ 5.000
20º — R$ 5.000

Regra do topo:

1º = 2 × 2º
2º = 2 × 3º

## 9. Multiplicador por divisão

Série A = 1.00
Série B = 0.75
Série C = 0.55
Série D = 0.40
Série E ou inferior = 0.30

## 10. Fechamento mensal

Criar:

MonthlyFinanceService

Fluxo:

1. creditar patrocínio
2. creditar TV
3. somar bilheteria
4. somar outras receitas
5. descontar salários
6. descontar demais despesas
7. calcular resultado
8. atualizar caixa
9. registrar transações

## 11. Transações financeiras

Toda movimentação deve gerar registro.

Receitas:

- sponsorship
- tv_rights
- ticketing
- prize
- player_sale
- friendly_income
- other_income

Despesas:

- salary
- player_purchase
- stadium
- interest
- other_expense

## 12. Collection club_finances

Campos:

club_id
cash_balance
monthly_fixed_revenue
monthly_payroll
monthly_income
monthly_expenses
monthly_result
updated_at

## 13. Compra e venda de jogadores

Compra:

buyer.cash_balance -= transfer_value

Venda:

seller.cash_balance += transfer_value

Registrar as duas transações.

## 14. Bots

Bots seguem as mesmas regras.

Sem:

- dinheiro infinito
- folha ignorada
- compras sem caixa

## 15. Saúde da folha

payroll / fixed_monthly_revenue

até 80%:
saudável

81%-100%:
atenção

101%-120%:
alto risco

acima de 120%:
crítico

## 16. Dashboard financeiro

Mostrar:

- caixa atual
- faturamento mensal
- patrocínio
- TV
- bilheteria
- folha salarial
- outras despesas
- resultado mensal
- premiação acumulada

## 17. Exemplo-base

Caixa inicial:
R$ 100.000

Receita fixa:
R$ 15.000

Folha:
R$ 13.500

Resultado operacional fixo:
R$ 1.500

Antes de bilheteria, premiação e mercado.

## 18. Configuração central

Criar:

EconomyConfig

Campos:

STARTING_CASH
MONTHLY_SPONSORSHIP
MONTHLY_TV_REVENUE
INITIAL_PAYROLL_TARGET_PERCENT
PAYROLL_TOLERANCE
POSITION_PRIZES
DIVISION_PRIZE_MULTIPLIERS
ALLOW_NEGATIVE_CASH

## 19. Regra de fidelidade

O sistema não deve ser descrito como reprodução exata do Brasfoot.

Ele deve ser documentado como:

"economia inspirada no Brasfoot com escala e periodicidade adaptadas ao nosso jogo".

A estrutura clássica vem do Brasfoot; os valores de R$ 100 mil, R$ 5 mil de patrocínio e R$ 10 mil de TV são regras próprias do nosso balanceamento.

## 20. Testes

Validar:

- caixa inicial
- faturamento
- folha
- patrocínio
- TV
- bilheteria
- prêmio
- compra
- venda
- salário
- bots
- não duplicação de receitas/despesas

Simular várias temporadas para impedir inflação ou falência generalizada.
