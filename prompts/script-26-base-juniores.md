# Script 26 — Base de Juniores

Objetivo: criar geração, desenvolvimento, avaliação e promoção de jovens.

## 1. Geração

A cada temporada:

YOUTH_PLAYERS_PER_SEASON = 2

## 2. Idade

Juniores:

14 a 17 anos

## 3. Campos

youth_players:

club_id
name
nationality
age
position
preferred_side
strength
estimated_potential_capacity
energy
morale
innate_characteristics
individual_skills
created_at

## 4. CPE

estimated_potential_capacity representa talento estimado da base.

Não deve existir como atributo profissional depois da promoção.

## 5. Treinamento

Juniores podem evoluir:

- strength
- individual_skills

## 6. Promoção

A partir de 18 anos:

pode promover ao profissional.

Ao promover:

- remover CPE da ficha profissional
- criar contrato
- definir salário
- criar market_value

## 7. Dispensa

Permitir liberar jogador da base.

## 8. Limite

Definir:

MAX_YOUTH_PLAYERS

Evitar acumulação infinita.

## 9. Bots

Bots devem avaliar:

- força
- idade
- CPE
- carência de posição

## 10. UI

Tela Base:

- lista
- idade
- posição
- força
- CPE
- promover
- dispensar

## 11. Testes

Validar:

- geração
- idade
- CPE
- promoção
- remoção do CPE no profissional
- limite
