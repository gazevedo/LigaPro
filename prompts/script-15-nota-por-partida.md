# Script 15 — Nota do Jogador por Partida

Objetivo: atribuir nota de desempenho a cada jogador após a partida.

## Escala

5.0 a 10.0

Nota inicial:

6.0

## Influências positivas

- gol
- participação ofensiva
- finalizações
- ações defensivas
- vitória
- clean sheet para goleiro/defesa

## Influências negativas

- cartão
- expulsão
- pênalti perdido
- sofrer muitos gols
- baixa participação

## Regras

Não usar apenas resultado do time.

Um jogador pode jogar bem em derrota.

## Collection

Criar:

player_match_ratings

Campos:

match_id
player_id
club_id
rating
minutes
events_summary

## Serviço

PlayerRatingService

## UI

Relatório da partida deve mostrar nota de todos os jogadores.

## Testes

- nota dentro de 5-10
- gol aumenta nota
- expulsão reduz
- goleiro pode ter nota alta mesmo em derrota
