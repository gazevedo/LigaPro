# Script 14 — Estatísticas Individuais

Objetivo: registrar desempenho de cada jogador por temporada e carreira.

## Estatísticas

Registrar:

- jogos
- titularidades
- minutos
- gols
- cartões amarelos
- cartões vermelhos
- pênaltis convertidos
- pênaltis perdidos

Preparar estrutura para:

- assistências
- defesas
- clean sheets

## Collection

Criar:

player_season_stats

Campos:

player_id
club_id
season_id
matches
starts
minutes
goals
yellow_cards
red_cards
penalties_scored
penalties_missed

Criar também histórico de carreira agregado.

## Integração

Atualizar automaticamente após cada partida.

## Rankings

Criar endpoints para:

- artilharia
- mais jogos
- mais cartões

## UI

Adicionar tela:

StatisticsScreen

## Testes

- gol atualiza jogador correto
- substituição calcula minutos
- cartão atualiza
- temporada separada corretamente
