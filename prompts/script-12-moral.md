# Script 12 — Moral dos Jogadores

Objetivo: implementar moral individual com impacto leve no desempenho.

## Escala

Utilizar:

0 a 100

Faixas:

0-20 muito baixa
21-40 baixa
41-60 normal
61-80 alta
81-100 muito alta

## Influências

A moral muda por:

- vitória
- derrota
- sequência de vitórias
- sequência de derrotas
- titularidade
- ficar muito tempo sem jogar
- gol marcado
- promoção da base
- transferência futura

## Impacto

A moral deve alterar apenas levemente a força efetiva.

Exemplo:

muito baixa: 0.94
baixa: 0.97
normal: 1.00
alta: 1.02
muito alta: 1.04

Centralizar em MoraleConfig.

## Modelagem

Adicionar:

morale

em players.

Criar:

PlayerMoraleService

## Pós-jogo

Após partida:

processar moral dos jogadores.

## UI

Mostrar moral na tela do jogador.

## Testes

- vitória aumenta moral
- derrota reduz
- limites 0-100
- impacto limitado
- não ultrapassar bônus máximo
