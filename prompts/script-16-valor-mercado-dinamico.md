# Script 16 — Valor de Mercado Dinâmico

Objetivo: calcular valor de mercado com base em fatores esportivos e econômicos.

## Fatores

market_value deve considerar:

- strength
- potential
- age
- posição
- desempenho recente
- divisão
- contrato restante
- reputação do clube

## Fórmula

Não espalhar regra.

Criar:

MarketValueService

A fórmula deve ser configurável.

## Idade

Valor tende a:

- subir em jogadores jovens com potencial
- atingir pico
- cair em veteranos

## Desempenho

Boa temporada aumenta valor.

Má temporada reduz levemente.

## Contrato

Contrato curto reduz valor.

## Atualização

Recalcular:

- após rodada
- após treinamento relevante
- após promoção da base
- após transferência
- após envelhecimento

## Histórico

Criar:

player_market_value_history

## Testes

- jovem promissor vale mais
- veterano tende a perder valor
- bom desempenho valoriza
- contrato curto desvaloriza
