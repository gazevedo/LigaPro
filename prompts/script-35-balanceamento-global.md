# Script 35 — Balanceamento Global e Simulação de Temporadas

Objetivo: validar o jogo como sistema completo.

## 1. Runner

Criar:

simulation_season_runner.py

## 2. Escalas

Rodar:

10 temporadas
100 temporadas
1.000 temporadas

Com múltiplas seeds.

## 3. Futebol

Medir:

- gols/jogo
- empates
- vitórias mandante
- cartões
- lesões
- distribuição de força
- domínio dos clubes fortes

## 4. Economia

Medir:

- caixa médio
- faturamento
- folha
- dívida
- premiações
- bilheteria
- patrocínio
- transferências

## 5. Mercado

Medir:

- preço mediano
- P90
- P99
- volume de transferências
- inflação
- concentração de talentos

## 6. Jogadores

Medir:

- força média
- idade média
- evolução
- regressão
- aposentadoria
- entrada de jovens

## 7. Clubes

Medir:

- promoções
- rebaixamentos
- repetição de campeões
- desigualdade
- falências

## 8. Bots

Medir:

- qualidade de escalação
- saúde financeira
- atividade de mercado
- uso de base

## 9. Critérios de alerta

Exemplos:

- dinheiro crescendo exponencialmente
- preços crescendo mais rápido que receita
- campeões repetidos em excesso
- bots quebrando
- jogadores 90+ ficando comuns
- lesões excessivas
- empates fora da faixa

## 10. Relatório

Gerar:

balance_report.json
balance_report.md

Com:

- médias
- percentis
- gráficos
- alertas
- recomendações

## 11. Regra

Nenhum ajuste deve ser feito por sensação sem medir o impacto em simulações amplas.
