# Script 18 — Ranking e Reputação

Objetivo: separar desempenho esportivo atual de prestígio histórico.

## Ranking

Ranking representa força/desempenho recente.

Considerar:

- divisão
- posição
- resultados
- títulos recentes

Atualizar periodicamente.

## Reputação

Reputação representa tamanho histórico do clube.

Considerar:

- títulos
- temporadas em divisões altas
- campanhas históricas
- torcida

## Campos

clubs:

ranking_points
ranking_position
reputation

## Serviços

ClubRankingService
ClubReputationService

## Impactos

Ranking e reputação podem influenciar:

- patrocinadores
- interesse de jogadores
- valor de mercado
- público

## Histórico

Criar:

club_ranking_history

## UI

ClubScreen deve mostrar:

ranking
reputação

## Testes

- título aumenta ranking e reputação
- resultado recente pesa mais no ranking
- reputação muda mais lentamente
