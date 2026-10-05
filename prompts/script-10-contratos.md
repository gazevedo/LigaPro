# Script 10 — Contratos de Jogadores

Objetivo: implementar contratos profissionais, salários, renovação, término de vínculo e jogadores livres.

## Regras principais

- Cada jogador profissional deve possuir contrato.
- Campos mínimos:
  - player_id
  - club_id
  - salary
  - started_at
  - expires_at
  - status
- Status:
  - active
  - expiring
  - expired
  - terminated
- O salário deve impactar o Financeiro.
- O contrato deve ter duração baseada em temporadas do jogo.
- Ao final do contrato, o jogador pode:
  - renovar
  - sair do clube
  - tornar-se jogador livre
- Não apagar histórico de contratos.

## Collection

Criar:

player_contracts

Campos:

player_id
club_id
salary
started_at
expires_at
status
created_at
updated_at

Criar também:

contract_history

## Renovação

Criar endpoint:

POST /api/players/{player_id}/contract/renew

O backend deve validar:

- propriedade do jogador
- contrato atual
- salário
- duração
- capacidade financeira do clube

## Jogadores livres

Criar situação:

free_agent

Jogador sem contrato não pertence a nenhum clube.

Pode ser contratado pelo mercado.

## Folha salarial

Financeiro deve mostrar:

- folha mensal
- custo por jogador
- custo total
- histórico

## Encerramento

Ao expirar:

1. marcar contrato como expired
2. remover vínculo contratual
3. definir jogador como free_agent
4. preservar histórico

## Testes

Testar:

- criação de contrato
- renovação
- expiração
- jogador livre
- tentativa de renovar jogador de outro clube
- impacto financeiro
- histórico

Não implementar agentes ou cláusulas complexas nesta etapa.
