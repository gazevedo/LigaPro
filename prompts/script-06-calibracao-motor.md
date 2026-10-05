# Script 6 — Calibração Revisada do Motor

Objetivo: recalibrar o motor após a mudança para uma lógica mais próxima do Brasfoot.

## 1. Cenários-base

Rodar pelo menos 10.000 partidas por cenário:

70 x 70
75 x 70
80 x 60
60 x 80
90 x 40
40 x 90

Alternar mando.

## 2. Regressão de gols

Meta inicial para times iguais:

2,2 a 2,9 gols por jogo

Empates:

22% a 32%

Pequena vantagem de mandante.

## 3. Testes de atributos

Comparar, mantendo todo resto igual:

- passing 50 vs 70
- playmaking 50 vs 70
- finishing 50 vs 70
- tackling 50 vs 70
- goalkeeping 50 vs 70
- speed 50 vs 70

Validar que cada atributo altera principalmente a fase correspondente.

## 4. Improvisação

Cenários:

posição correta
posição compatível
posição errada

A penalidade deve ser clara, mas não destruir completamente o jogador.

## 5. Lado preferido

Comparar:

lado correto
lado oposto
both

A penalidade de lado deve ser menor que a penalidade de posição.

## 6. Energia

Comparar:

100
80
60
40

O rendimento deve cair gradualmente.

## 7. Moral

Comparar extremos.

O efeito deve permanecer pequeno, aproximadamente até ±4%.

## 8. Formação

Testar:

4-4-2
4-3-3
5-3-2
3-5-2

A formação deve alterar perfil de jogo, não entregar vitória automática.

## 9. Estilo

Testar:

balanced x balanced
all_out_attack x balanced
counter_attack x balanced
counter_attack x all_out_attack

Esperado:

all_out_attack:
mais chances pró e contra

counter_attack:
menos posse e menor volume, mas melhor eficiência em transições

## 10. Marcação

Testar:

light
heavy
very_heavy

A marcação muito pesada deve:
- reduzir ataques adversários de forma perceptível
- aumentar faltas/cartões
- também reduzir eficiência da própria construção

Meta de referência:
efeito máximo próximo de ~20% na redução de ataques adversários em cenários favoráveis.

## 11. Foco de ataques

Testar 10.000 partidas com:

normal
center
wings

Quando center ou wings estiver selecionado:

meta aproximada de 70% dos ataques naquele setor.

## 12. Aceitação

Nenhuma combinação tática deve dominar todas as demais.

Nenhum atributo isolado deve decidir jogo sozinho.

Força e qualidade do elenco continuam sendo fatores principais.

## 13. Relatório

Gerar:

- gols
- posse
- ataques
- chances
- finalizações
- gols
- faltas
- cartões
- ataques por setor
- eficiência por estilo
- efeito de improvisação
- efeito de energia
