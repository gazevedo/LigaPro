# Script 21 — Precificação e Salário de Jogadores Inspirados no Brasfoot

Objetivo: criar valor de mercado e salário coerentes com evidências técnicas do Brasfoot e com a economia do nosso jogo.

## 1. Evidências confirmadas

Engenharia reversa do Brasfoot 22/23 confirma:

- salário e valor de mercado são campos separados;
- salário possui rotina de recálculo;
- o recálculo de salário usa:
  - força geral
  - idade
  - posição
  - estrelas
- existe rotina separada para recalcular o valor de mercado/passe;
- jogadores reais no save apresentam salário e valor de mercado em escalas bem diferentes.

A fórmula completa original do valor de mercado não está publicamente documentada.

Portanto, não afirmar que este script reproduz exatamente a fórmula original.

## 2. Separação obrigatória

Criar:

SalaryService
MarketValueService

Campos:

salary
market_value
asking_price

São conceitos diferentes.

## 3. Valor-base por força

Usar curva não linear adaptada à nossa economia:

strength 20  → R$ 500
strength 30  → R$ 1.000
strength 40  → R$ 2.500
strength 50  → R$ 6.000
strength 60  → R$ 12.000
strength 70  → R$ 22.000
strength 80  → R$ 40.000
strength 90  → R$ 70.000
strength 100 → R$ 100.000

Interpolar continuamente.

## 4. Fator de idade

A comunidade do Brasfoot historicamente observa que jogadores mais jovens tendem a valer mais.

Usar:

17-20 → 1.20
21-24 → 1.15
25-28 → 1.05
29-31 → 0.95
32-34 → 0.80
35-37 → 0.65
38+ → 0.50

## 5. Fator de estrelas

Fama/estrelas elevam valor.

Usar:

0 → 1.00
1 → 1.05
2 → 1.10
3 → 1.18
4 → 1.28
5 → 1.40

## 6. Fator de posição

A posição deve ter peso pequeno.

GK  = 0.95
FB  = 0.98
CB  = 1.00
MID = 1.05
ATT = 1.10

## 7. Desempenho

Usar apenas ajuste moderado:

performance_factor entre 0.90 e 1.15

Baseado em:

- nota média
- titularidade
- minutos
- gols quando aplicável
- desempenho recente

## 8. Contrato

24+ meses → 1.10
13-24 meses → 1.05
7-12 meses → 1.00
4-6 meses → 0.90
1-3 meses → 0.75
sem contrato → taxa de transferência = 0

## 9. Divisão

A = 1.00
B = 0.92
C = 0.84
D = 0.76
E+ = 0.68

## 10. Reputação

Aplicar ajuste pequeno:

0.95 a 1.10

## 11. Fórmula de valor de mercado

market_value =
base_value_by_strength
× age_factor
× stars_factor
× position_factor
× performance_factor
× contract_factor
× division_factor
× reputation_factor

Limites:

MIN_PLAYER_VALUE = 500
MAX_PLAYER_VALUE = 120000

Arredondar para R$ 100.

## 12. Salário

A lógica relativa deve seguir os fatores tecnicamente confirmados no Brasfoot:

salary_reference =
salary_by_strength
× age_salary_factor
× position_salary_factor
× stars_salary_factor

Depois normalizar a folha completa do clube.

## 13. Curva salarial inicial

strength 20 → R$ 150
strength 30 → R$ 220
strength 40 → R$ 320
strength 50 → R$ 450
strength 60 → R$ 650
strength 70 → R$ 900
strength 80 → R$ 1.250
strength 90 → R$ 1.700
strength 100 → R$ 2.300

Depois aplicar idade, posição e estrelas.

## 14. Normalização da folha

Após gerar os 25 salários:

raw_payroll = soma dos salary_reference

target_payroll = R$ 13.500

normalization_factor =
target_payroll / raw_payroll

salary_final =
salary_reference × normalization_factor

Arredondar adequadamente.

A folha final deve respeitar tolerância de ±3%.

## 15. Asking price

listed:
0.90 a 1.10 × market_value

available:
1.00 a 1.30 × market_value

not_for_sale:
1.50 a 2.00 × market_value

## 16. Jogador livre

Sem contrato:

transfer_fee = 0

Pode compensar com salário maior.

## 17. Atualização

Recalcular market_value:

- mudança de força
- mudança de idade
- alteração de estrelas
- renovação
- mudança de divisão
- fim de temporada
- desempenho relevante

Recalcular salary:

- criação
- renovação
- grande evolução de força
- mudança relevante de estrelas

## 18. Distribuição-alvo

Gerar 10.000 jogadores.

Meta inicial:

mediana:
R$ 6.000 a R$ 12.000

P90:
R$ 25.000 a R$ 40.000

P99:
R$ 70.000 a R$ 110.000

## 19. Compatibilidade com a economia

Com R$ 100.000 de caixa inicial:

- vários medianos devem ser acessíveis;
- 2 ou 3 bons jogadores devem consumir parcela importante do caixa;
- um craque deve representar decisão financeira relevante;
- montar elenco inteiro de elite deve ser inviável.

## 20. Regra de fidelidade

Não usar:

- potential profissional
- atributos inventados
- fórmula apresentada como "fórmula oficial do Brasfoot"

Usar apenas fatores confirmados ou observados e calibrar à economia própria.
