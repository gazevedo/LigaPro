# Script 4 — Campeonato, Jogadores, Treinamento e Categorias de Base

Objetivo: implementar o ciclo competitivo principal do jogo.

## Campeonato
- 20 clubes por divisão
- divisões em séries: A, B, C, D, E... sem limite fixo
- completar vagas com bots
- novo usuário entra na divisão mais alta que ainda possua bot
- se todas estiverem lotadas com humanos, criar nova divisão inferior com 1 humano + 19 bots

## Entrada durante temporada
O novo usuário pode substituir bot mesmo com campeonato em andamento.
Ele herda integralmente a situação esportiva do bot:
- divisão
- posição
- pontos
- jogos
- vitórias
- empates
- derrotas
- gols pró
- gols contra
- saldo
- calendário restante
- resultados já computados

O usuário NÃO herda plantel, dinheiro, estádio, patrocinadores ou demais dados administrativos do bot.
Recebe sua própria estrutura e 25 jogadores.

Quando houver vários bots, usar estratégia configurável; inicial: substituir o pior colocado da divisão mais alta com bot.
Registrar substituição em club_replacements e preservar auditoria/histórico.
Operação deve ser atômica e segura contra concorrência.

## Temporada
Duração aproximada: 30 dias reais.
- 2 dias iniciais de preparação e negociações
- campeonato
- 2 dias de janela intermediária
- continuação
- encerramento

Com 20 clubes em turno e returno: 38 jogos por clube. O calendário pode ter múltiplas rodadas em uma mesma data e deve ser configurável.

Pontuação:
- vitória 3
- empate 1
- derrota 0

Classificação: jogos, vitórias, empates, derrotas, gols pró, gols contra, saldo, pontos e posição.

Promoção/rebaixamento:
- Série A: 1 campeão e 4 rebaixados
- Série B e inferiores: 4 sobem e 4 descem
- última divisão: 4 sobem; só rebaixa se existir divisão inferior

Bots participam normalmente e podem subir, cair ou ser campeões.

Collections sugeridas:
seasons
divisions
season_clubs
standings
club_replacements

## Jogadores
Cada novo clube recebe 25 jogadores aleatórios.
Posições somente:
- GK goleiro
- DEF defensor
- MID médio
- ATT atacante

Distribuição sugerida configurável:
3 GK
8 DEF
8 MID
6 ATT

Atributos iniciais nesta fase:
- nome
- idade
- posição
- força
- nível de treinamento
- doença

Criar PlayerGeneratorService.

## Dashboard
Adicionar:
- Treinamento
- Categorias de Base

Dashboard final desta etapa:
Clube
Plantel
Estádio
Financeiro
Calendário
Mercado
Treinamento
Categorias de Base

## Treinamento
TrainingScreen lista jogadores e botão Treinar.
Cada clique válido:
training_level += 1

Quando training_level atingir 100:
strength += 1
training_level = 0

Backend calcula tudo; frontend apenas envia o comando de treino.
Endpoint: POST /api/players/{player_id}/train

## Categorias de base
YouthAcademyScreen.
A cada nova temporada/mês o clube recebe 2 jogadores da base.
Idade inicial sugerida: 14 a 17 anos.
Eles também podem ser treinados pela mesma regra.
A partir dos 18 anos podem ser promovidos ao profissional por decisão do usuário.

Collection: youth_players.
Endpoint de promoção: POST /api/youth/{player_id}/promote

## Envelhecimento
Cada temporada concluída adiciona +1 ano de idade a todos os jogadores profissionais e da base.
Não existe limite máximo de idade.

## Declínio e aposentadoria
A partir dos 35 anos, o jogador pode perder força e pode se aposentar.
Probabilidades devem ser configuráveis e aumentar com a idade.
Exemplo provisório de declínio:
35: 10%
36: 15%
37: 20%
38: 30%
39: 40%
40+: 50%

Exemplo provisório de aposentadoria:
35: 1%
36: 2%
37: 5%
38: 10%
39: 15%
40: 25%
41: 35%
42+: 50%

Ao aposentar:
- status retired
- remover de plantel ativo, escalação, mercado e treinamento
- preservar histórico

Criar PlayerAgingService.

## Fim de temporada
Criar SeasonFinalizationService idempotente.
Ordem:
1. finalizar partidas
2. calcular classificação
3. definir campeão
4. registrar troféu
5. definir acessos/rebaixamentos
6. atualizar divisões
7. envelhecer jogadores
8. processar declínio
9. processar aposentadorias
10. envelhecer base
11. gerar 2 novos jogadores da base
12. preparar próxima temporada

## Mercado e janelas
Mercado pode ser consultado sempre, mas transferências só podem ser concluídas durante os 2 dias iniciais e os 2 dias da janela intermediária.

## GameConfig
Centralizar:
TEAMS_PER_DIVISION = 20
PRESEASON_DAYS = 2
MIDSEASON_TRANSFER_WINDOW_DAYS = 2
SEASON_DURATION_DAYS = 30
RELEGATION_COUNT = 4
PROMOTION_COUNT = 4
INITIAL_SQUAD_SIZE = 25
MAX_PLAYER_LEVEL = 100
YOUTH_PLAYERS_PER_SEASON = 2
YOUTH_PROMOTION_AGE = 18
PLAYER_DECLINE_AGE = 35
BOT_REPLACEMENT_STRATEGY = lowest_ranked

## Validação
Testar divisões, bots, substituição de bot durante temporada, herança de pontos, concorrência, nova divisão, 25 jogadores, treino, nível 100 -> força +1, base, promoção aos 18, envelhecimento, declínio, aposentadoria, campeão, 4 acessos, 4 rebaixamentos e janelas de transferência.
