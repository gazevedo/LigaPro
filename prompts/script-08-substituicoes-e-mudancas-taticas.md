# Script 8 — Substituições e Mudanças Táticas Revisado

Objetivo: adaptar mudanças durante a partida ao sistema tático simplificado.

## 1. Substituições

Manter:

MAX_SUBSTITUTIONS = 5

## 2. Alterações permitidas durante a partida

- formação
- estilo
- marcação
- foco dos ataques

Remover comandos de:
- tempo
- pressing
- defensive_line

## 3. Recalcular após mudança

Após substituição ou mudança tática:

- PositionFit
- SideFit
- energia atual
- setores
- formação
- estilo
- marcação
- foco

## 4. Comando tático

Exemplo:

{
  "type": "tactics_change",
  "payload": {
    "play_style": "all_out_attack",
    "marking": "heavy",
    "attack_focus": "center"
  }
}

## 5. Bot

Se perdendo:
- pode mudar para all_out_attack

Se vencendo:
- pode manter balanced ou counter_attack

Contra adversário ofensivo:
- pode optar por counter_attack

Marcação:
- ajustar conforme necessidade, respeitando risco disciplinar

## 6. Histórico

Salvar eventos:

formation_change
play_style_change
marking_change
attack_focus_change
substitution

## 7. Regra temporal

Mudanças afetam apenas blocos futuros.
