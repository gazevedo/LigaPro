# Script 22 — Modelagem de Jogador Fiel ao Brasfoot

Objetivo: manter apenas atributos de jogador compatíveis com o Brasfoot e eliminar atributos inventados.

## 1. Atributos principais

- name
- nationality
- age
- position
- preferred_side
- strength
- energy
- morale
- stars
- salary
- market_value
- contract_status
- contract_expires_at
- status
- innate_characteristics
- individual_skills

## 2. Posições confirmadas tecnicamente

GK = Goleiro
FB = Lateral
CB = Zagueiro
MID = Meia
ATT = Atacante

## 3. Lado preferido

- left
- right
- both

## 4. Força geral

Campo:

strength

Escala:

1 a 100

## 5. Energia

Campo:

energy

Escala:

0 a 100

A engenharia reversa confirma energia/condição armazenada com limite superior de 100.

## 6. Estrelas

Campo:

stars

Representa status/fama.

As estrelas também participam do recálculo de salário no Brasfoot 22/23.

## 7. Moral

Campo:

morale

Manter como atributo de gameplay.

Escala interna sugerida:

0 a 100

## 8. Habilidades individuais confirmadas

Quando o modo de habilidade individual estiver ativo:

- goalkeeping
- speed
- technique
- passing
- tackling
- playmaking
- finishing

Escala:

0 a 100

Esses sete atributos são confirmados no bytecode/documentação técnica do Brasfoot 22/23.

## 9. Características inatas

Goleiros:

- positioning
- rushing_out
- reflexes
- penalty_saving

Jogadores de linha:

- playmaking
- heading
- crossing
- tackling
- dribbling
- finishing
- marking
- passing
- stamina
- speed

## 10. Salário

Campo:

salary

É separado do valor de mercado.

O recálculo de salário deve considerar:

- strength
- age
- position
- stars

Não usar potential profissional.

## 11. Valor de mercado

Campo:

market_value

Possui lógica separada de salário.

Usar MarketValueService do Script 21.

## 12. Contrato

Campos:

contract_status
contract_expires_at

Status:

active
expiring
expired

## 13. Status esportivo

Valores:

available
injured
suspended
retired

## 14. Estatísticas

Não colocar estatísticas acumuladas dentro da entidade-base.

Usar:

player_season_stats
player_match_ratings

## 15. Estrutura MongoDB

```json
{
  "_id": "ObjectId",
  "owner_club_id": "ObjectId|null",
  "current_club_id": "ObjectId|null",

  "name": "string",
  "nationality": "BR",
  "age": 24,

  "position": "MID",
  "preferred_side": "right",

  "strength": 67,
  "energy": 100,
  "morale": 58,
  "stars": 0,

  "individual_skills": {
    "goalkeeping": 5,
    "speed": 68,
    "technique": 71,
    "passing": 74,
    "tackling": 52,
    "playmaking": 70,
    "finishing": 61
  },

  "innate_characteristics": [
    "passing",
    "playmaking"
  ],

  "salary": 620,
  "market_value": 14500,

  "contract_status": "active",
  "contract_expires_at": "datetime",

  "status": "available",
  "retired": false,

  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## 16. Remover

Remover como atributos profissionais:

- potential
- experience
- chemistry individual
- training_level permanente
- acceleration
- vision
- decisions
- composure
- leadership
- aggression
- work_rate
- quaisquer outros atributos não existentes no Brasfoot

## 17. Base/juniores

Potencial estimado pode existir somente para jogadores de base, como conceito separado.

Não transportar isso como atributo profissional permanente.

## 18. MatchEngine

Considerar apenas:

- strength ou individual_skills
- position
- preferred_side
- energy
- morale
- innate_characteristics
- stars quando calibrado

## 19. Treinamento

Treinamento deve evoluir:

- goalkeeping
- speed
- technique
- passing
- tackling
- playmaking
- finishing

A força geral pode ser recalculada conforme o modo de jogo.

## 20. Regra de fidelidade

A ficha profissional não deve crescer com atributos que não fazem parte do Brasfoot.

Campos técnicos de banco podem existir, mas não devem ser tratados como atributos esportivos do jogador.
