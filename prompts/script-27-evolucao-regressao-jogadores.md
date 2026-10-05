# Script 27 — Evolução e Regressão dos Jogadores

Objetivo: criar progressão de carreira coerente com idade, treino e uso.

## 1. Fatores

Evolução deve considerar:

- idade
- força atual
- treino
- minutos jogados
- moral
- lesões
- características inatas

## 2. Faixas de idade

14-20:
alta chance de evolução

21-25:
boa evolução

26-29:
evolução baixa/estabilidade

30-34:
estabilidade/regressão leve

35+:
regressão

## 3. Treino

Treino melhora:

- strength
- individual_skills

Não usar potential profissional.

## 4. Minutos

Jogadores usados regularmente têm vantagem pequena de desenvolvimento.

## 5. Moral

Moral deve ter impacto secundário.

## 6. Lesões

Lesões longas podem reduzir evolução.

## 7. Regressão

Após 35:

chance crescente de perder força/habilidades.

## 8. Aposentadoria

Não definir idade máxima fixa.

A partir de 35:

probabilidade de aposentadoria cresce com:

- idade
- regressão
- condição
- falta de contrato

## 9. Atualização

Processar preferencialmente ao fim de temporada.

## 10. Histórico

player_development_history:

player_id
old_strength
new_strength
reason
season_id
created_at

## 11. Testes

Simular 10 temporadas e validar:

- jovens crescem
- veteranos caem
- força média não infla indefinidamente
- aposentadorias ocorrem progressivamente
