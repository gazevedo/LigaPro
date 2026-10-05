# Relatório de Calibração Inicial do Motor

Foram avaliados cenários de 10.000 partidas usando a primeira versão matemática do motor.

## Problema encontrado na fórmula inicial

A configuração inicial gerava aproximadamente 3,93 gols por partida em confrontos entre times equivalentes (70 x 70).

Isso foi considerado excessivo para a base do jogo.

O principal ajuste foi reduzir a taxa de conversão das chances.

## Configuração recomendada v1

- vantagem de meio do mandante: 3%
- vantagem de ataque do mandante: 4%
- variação aleatória por bloco: ±5%
- criação base de chance: 0,46
- sensibilidade de criação: 0,75
- probabilidade base de gol: 0,30
- sensibilidade da conversão: 0,55
- chance mínima de gol: 4%
- chance máxima de gol: 48%

## Resultados — 10.000 partidas por cenário

| Cenário | Vitória mandante | Empate | Vitória visitante | Gols/jogo | Gols casa | Gols fora |
|---|---:|---:|---:|---:|---:|---:|
| 70 x 70 | 39,9% | 26,1% | 34,0% | 2,54 | 1,33 | 1,21 |
| 75 x 70 | 49,0% | 24,8% | 26,2% | 2,57 | 1,52 | 1,05 |
| 80 x 60 | 73,3% | 17,1% | 9,7% | 2,88 | 2,20 | 0,68 |
| 60 x 80 | 12,2% | 18,9% | 68,9% | 2,80 | 0,74 | 2,06 |
| 90 x 40 | 96,0% | 3,4% | 0,7% | 3,95 | 3,71 | 0,24 |
| 40 x 90 | 0,9% | 4,1% | 95,0% | 3,83 | 0,26 | 3,56 |

## Interpretação

### 70 x 70

O comportamento ficou equilibrado.

A vantagem do mandante existe, mas não é excessiva.

Placares mais frequentes:

1x1, 1x0, 2x1, 0x1 e 1x2.

### 75 x 70

Uma pequena diferença de força já cria vantagem perceptível sem eliminar a possibilidade de empate ou derrota.

### 80 x 60

O time superior vence aproximadamente 73% das partidas.

O inferior ainda vence aproximadamente 10%, mantendo a possibilidade de zebra.

### 90 x 40

A diferença é extrema e o favorito vence aproximadamente 96% das partidas.

Esse comportamento pode ser mantido ou suavizado durante testes de gameplay.

## Conclusão

A configuração v1 é adequada como ponto inicial para implementação.

Ela não deve ser considerada definitiva.

Depois que os jogadores reais, formações e escalações estiverem funcionando, devem ser executadas novas simulações para verificar:

- distribuição real dos níveis dos jogadores
- diferença entre divisões
- impacto do treinamento
- impacto do envelhecimento
- frequência de goleadas
- equilíbrio do mando de campo

A regra principal permanece:

força maior aumenta claramente a probabilidade de vitória, mas não determina o placar.
