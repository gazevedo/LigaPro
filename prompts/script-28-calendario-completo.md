# Script 28 — Calendário Completo

Objetivo: centralizar todos os eventos da temporada.

## 1. Tipos de evento

calendar_events:

league_match
friendly
transfer_window_open
transfer_window_close
season_start
season_end
youth_generation
financial_close
training_event
other

## 2. Temporada

Manter:

SEASON_DURATION_DAYS = 30

PRESEASON_DAYS = 2

MIDSEASON_TRANSFER_WINDOW_DAYS = 2

## 3. Campeonato

38 partidas por clube em liga de 20 times.

Distribuir rodadas durante a temporada lógica.

## 4. Conflitos

Não permitir:

- dois jogos do mesmo clube no mesmo horário lógico
- evento financeiro duplicado
- fechamento de temporada antes da última rodada

## 5. Janelas

Registrar explicitamente abertura/fechamento.

## 6. Amistosos

Permitir em períodos livres.

## 7. UI

Calendário mensal/cronológico.

Mostrar:

- jogos
- janelas
- eventos
- fechamento financeiro

## 8. Bots

Bots também obedecem ao calendário.

## 9. Testes

Validar:

- 38 jogos
- sem duplicidade
- janela correta
- temporada termina corretamente
