# Script 31 — Empréstimos Bancários e Juros

Objetivo: permitir crédito sem criar dinheiro infinito.

## 1. Produtos

short_term
medium_term
long_term

## 2. Campos

club_loans:

club_id
principal
interest_rate
installments
installment_value
remaining_balance
status
created_at

## 3. Limite de crédito

credit_limit deve considerar:

- faturamento
- caixa
- reputação
- dívida atual

## 4. Juros

Sempre positivos.

Não permitir arbitragem com investimentos.

## 5. Pagamento

Descontar parcelas no fechamento mensal.

## 6. Inadimplência

Se não houver caixa:

- bloquear novos empréstimos
- aumentar risco financeiro
- aplicar restrições

Evitar regras extremas nesta primeira versão.

## 7. Bots

Bots só tomam crédito quando necessário.

## 8. Testes

Validar:

- contratação
- juros
- parcela
- saldo
- limite
- quitação
