# Script 11 — Potencial dos Jogadores

Objetivo: criar potencial de desenvolvimento para diferenciar jogadores comuns de grandes promessas.

## Campo

Adicionar ao jogador:

potential

Escala:

1 a 100

A força atual continua sendo:

strength

Exemplo:

strength = 42
potential = 81

## Regras

- strength nunca deve evoluir indefinidamente acima do potential por treinamento normal.
- jogadores da base devem ter potencial mais variável.
- potencial deve ser oculto ou parcialmente oculto ao usuário inicialmente.
- bots usam potencial nas decisões de mercado.

## Geração

PlayerGeneratorService deve gerar:

strength
potential

Regra:

potential >= strength

## Categorias de base

Jogadores jovens devem ter maior chance de potencial alto.

## Evolução

Quando training_level atingir 100:

- se strength < potential:
  - strength += 1
- se strength >= potential:
  - evolução normal deve ser muito reduzida ou bloqueada

## Mercado

potential influencia:

market_value

## API

Não expor potencial exato publicamente por padrão.

Criar campo interno e DTO controlado.

## Testes

- potential nunca menor que strength
- treino respeita teto
- jovens com distribuição de potencial
- mercado considera potencial
