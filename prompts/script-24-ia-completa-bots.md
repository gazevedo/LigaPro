# Script 24 — IA Completa dos Bots

Objetivo: fazer bots administrarem clube, elenco, tática e finanças usando as mesmas regras dos usuários.

## 1. Princípio

Bots não recebem:

- dinheiro infinito
- força extra
- conhecimento do RNG futuro
- permissões exclusivas

## 2. BotManagerService

Criar serviço central:

BotManagerService

Submódulos:

- BotLineupService
- BotTacticsService
- BotMatchManager
- BotTransferService
- BotContractService
- BotFinanceService
- BotTrainingService
- BotYouthService
- BotStadiumService

## 3. Escalação

BotLineupService deve:

- ignorar lesionados/suspensos
- respeitar posições
- considerar condição
- considerar força
- escolher formação válida
- montar banco

## 4. Tática

Escolher:

- formation
- play_style
- marking
- attack_focus

Baseado em:

- força própria
- força adversária
- mando
- placar
- momento da partida

## 5. Substituições

BotMatchManager deve considerar:

- lesão
- condição baixa
- placar
- cartões
- necessidade ofensiva/defensiva

## 6. Mercado

BotTransferService deve:

- identificar carência por posição
- listar excedentes
- avaliar preço
- respeitar caixa
- respeitar folha
- comprar
- vender
- emprestar

## 7. Contratos

BotContractService:

- renovar jogadores importantes
- liberar jogadores caros/inúteis
- respeitar orçamento

## 8. Finanças

BotFinanceService:

- preservar reserva de caixa
- evitar folha crítica
- evitar compras inviáveis
- pagar salários
- considerar empréstimos apenas quando necessário

## 9. Treinamento

BotTrainingService deve priorizar:

- jovens
- titulares
- jogadores próximos de evolução

## 10. Base

BotYouthService:

- avaliar juniores
- promover
- dispensar
- preencher carências

## 11. Estádio

BotStadiumService só investe quando:

- caixa suficiente
- lotação recorrente alta
- reserva mínima preservada

## 12. Perfis de bot

Opcionalmente criar:

conservative
balanced
aggressive

Afetam decisão financeira e de mercado, não força artificial.

## 13. Auditoria

Criar:

bot_decisions

Campos:

club_id
decision_type
payload
reason
created_at

## 14. Testes

Simular temporadas completas e validar:

- bots não quebram sistematicamente
- bots mantêm elenco válido
- bots compram/vendem
- bots renovam
- bots usam base
- bots alteram tática
