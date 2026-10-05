# Script 29 — Estádio e Bilheteria

Objetivo: tornar estádio e público parte real da economia.

## 1. Estádio

Campos:

capacity
stands_level
pitch_level
lights_level
changing_rooms_level
medical_level
training_level
parking_level
shops_level
boxes_level

## 2. Público

AttendanceService deve considerar:

- torcida
- satisfação
- capacidade
- preço do ingresso
- divisão
- posição na tabela
- importância da partida
- reputação
- adversário

## 3. Limite

attendance <= capacity

## 4. Preço do ingresso

ticket_price configurável.

Preço alto:

- aumenta receita por ingresso
- reduz demanda

Preço baixo:

- aumenta público
- reduz receita unitária

## 5. Receita

ticketing_income =
attendance × ticket_price

## 6. Expansão

Aumentar capacidade custa dinheiro.

## 7. Estrutura

medical_level:
ajuda recuperação

training_level:
ajuda treino

shops/boxes:
podem gerar receita futura

## 8. Bots

Bots investem apenas se:

- caixa suficiente
- ocupação alta
- retorno justificável

## 9. Testes

Validar:

- lotação
- elasticidade de preço
- receita
- capacidade
- expansão
