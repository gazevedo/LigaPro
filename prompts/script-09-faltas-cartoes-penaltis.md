# Script 9 — Faltas, Cartões e Pênaltis Revisado

Objetivo: integrar disciplina diretamente ao sistema de marcação do Brasfoot.

## 1. Principal fator tático

A chance de falta deve ser fortemente relacionada à marcação:

light
heavy
very_heavy

## 2. Modificadores iniciais

Usar valores calibráveis.

Sugestão inicial:

light:
0.75

heavy:
1.00

very_heavy:
1.35

Esses valores são ponto inicial, não fórmula oficial.

## 3. Relação com construção

very_heavy:
- aumenta contenção
- reduz ataques adversários
- aumenta faltas
- aumenta amarelos/vermelhos
- também pode piorar a própria saída de bola

## 4. Faltas

Resolver após disputa real:

duel
→ foul?
→ severity
→ card?
→ penalty_area?

## 5. Cartões

Manter:

yellow
second_yellow
direct_red

## 6. Pênaltis

Manter serviço separado.

## 7. Expulsão

Ao expulsar:

- remover jogador
- recalcular PositionFit e setores
- continuar com inferioridade numérica

## 8. Calibração

Comparar 10.000 partidas com:

light
heavy
very_heavy

Esperado:

very_heavy:
- menos ataques adversários
- mais faltas
- mais cartões
- mais expulsões
- menor fluidez própria

## 9. Regra de fidelidade

Não usar pressing/tempo como fatores disciplinares principais após revisão.

Marcação é o principal vínculo entre tática e disciplina.
