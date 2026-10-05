# Script 25 — Mercado Avançado

Objetivo: evoluir compra, venda e empréstimo para um sistema de negociação completo.

## 1. Status de mercado

player_transfer_status:

available
listed
not_for_sale
loan_listed

## 2. Ofertas

transfer_offers:

buyer_club_id
seller_club_id
player_id
offer_type
transfer_value
salary_offer
contract_months
loan_months
status
created_at
expires_at

## 3. Fluxo de compra

1. comprador envia proposta
2. vendedor aceita/rejeita/contrapropõe
3. jogador avalia contrato
4. comprador confirma
5. transação financeira
6. transferência do jogador

## 4. Contraproposta

Permitir:

counter_offer

O clube vendedor pode alterar:

- preço
- condições

## 5. Aceitação do jogador

PlayerContractDecisionService deve considerar:

- salário
- divisão
- reputação
- titularidade esperada
- duração

## 6. Jogador livre

Sem contrato:

transfer_fee = 0

Negociar apenas:

- salário
- duração

## 7. Empréstimo

Permitir:

- duração
- taxa
- divisão de salário
- retorno automático

Sem opção de compra nesta primeira versão.

## 8. Interesse

Bots e jogadores devem evitar transferências absurdas.

Exemplo:

jogador muito forte pode rejeitar clube muito abaixo em divisão/reputação.

## 9. Janelas

Negociação pode ser visualizada sempre.

Finalização só dentro das janelas definidas.

## 10. Histórico

transfer_history deve registrar:

- origem
- destino
- valor
- tipo
- data

## 11. Testes

Validar:

- proposta
- contraproposta
- rejeição
- aceite
- free agent
- empréstimo
- janela fechada
- falta de caixa
