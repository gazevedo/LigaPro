# Script 13 — Entrosamento da Equipe

Objetivo: criar entrosamento para impedir que um elenco recém-montado renda imediatamente no máximo.

## Escala

team_chemistry:

0 a 100

## Influências

Aumenta por:

- repetir escalação
- repetir formação
- jogadores atuando juntos
- tempo no clube
- sequência de partidas

Diminui por:

- muitas contratações
- muitas mudanças na escalação
- troca constante de formação

## Impacto

Aplicar pequeno modificador ao MatchEngine.

Exemplo:

0-20: 0.92
21-40: 0.96
41-60: 1.00
61-80: 1.02
81-100: 1.04

## Modelagem

Criar:

club_chemistry

Campos:

club_id
value
last_lineup_hash
last_formation
updated_at

## Pós-jogo

ChemistryService atualiza valor.

## Mercado

Jogador recém-contratado começa sem integração completa.

## Testes

- escalação repetida melhora entrosamento
- muitas mudanças reduzem
- limites 0-100
- impacto pequeno no motor
