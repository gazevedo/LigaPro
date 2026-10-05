# Script 32 — Notícias e Eventos

Objetivo: dar contexto narrativo às mudanças do jogo.

## 1. NewsItem

Campos:

type
title
body
club_id
player_id
competition_id
reference_id
created_at

## 2. Tipos

transfer
injury
suspension
title
promotion
relegation
top_scorer
record
financial
sponsor
stadium
youth
retirement

## 3. Geração

Gerar automaticamente a partir de eventos reais.

Não criar notícias desconectadas do estado do jogo.

## 4. Feed

Dashboard deve mostrar notícias recentes.

## 5. Eventos especiais

Podem existir eventos raros, desde que controlados por configuração.

## 6. Bots

Notícias também cobrem clubes bots.

## 7. Testes

Validar:

- notícia de transferência
- lesão
- título
- aposentadoria
- ausência de duplicidade
