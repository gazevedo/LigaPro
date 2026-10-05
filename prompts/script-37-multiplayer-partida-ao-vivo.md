# Script 37 — Partida Multiplayer ao Vivo com 0, 1 ou 2 Usuários

Objetivo: permitir que dois usuários humanos acompanhem e controlem a mesma partida em tempo real, sem tornar a conexão obrigatória para que o jogo aconteça.

A partida deve funcionar corretamente com:
- 0 usuários conectados
- 1 usuário conectado
- 2 usuários conectados

A conexão do usuário nunca pode ser requisito para executar a partida.

## 1. Princípio central

Existe uma única simulação autoritativa no backend.

Nunca criar:
- uma simulação por usuário
- resultado calculado no cliente
- sincronização entre dois motores independentes

Arquitetura:

User A ─┐
        ├── LiveMatchSession ── MatchEngine único
User B ─┘

Configuração obrigatória:

MIN_CONNECTED_USERS_TO_RUN = 0
MATCH_MUST_NEVER_WAIT_FOR_PLAYER_CONNECTION = true

## 2. Cenários de conexão

### 2.1 Dois usuários conectados
Ambos:
- acompanham o mesmo relógio
- recebem os mesmos eventos
- veem o mesmo placar
- recebem as mesmas estatísticas
- controlam apenas o próprio clube

### 2.2 Apenas um usuário conectado
O usuário conectado controla normalmente o próprio clube.

O clube ausente usa:
- escalação pré-jogo
- formação pré-jogo
- estilo pré-jogo
- marcação pré-jogo
- foco pré-jogo

### 2.3 Nenhum usuário conectado
A partida é simulada normalmente até o fim, sem cadência visual obrigatória.

### 2.4 Entrada tardia
Se um usuário entrar no minuto 58, ele recebe o estado atual e passa a controlar o clube dali em diante.

Nada anterior é recalculado.

## 3. LiveMatchSession

Campos:

match_id
home_club_id
away_club_id
home_user_id
away_user_id
status
current_minute
current_period
simulation_speed
paused
started_at
finished_at
version
last_snapshot_at

## 4. Participantes

Criar `match_participants`:

match_id
user_id
club_id
role
connected
joined_at
last_seen_at
disconnected_at

Roles:
- home_manager
- away_manager
- spectator

Nesta fase, usar apenas home_manager e away_manager.

## 5. Autorização

Ao conectar:

user owns club
AND
club participates in match

Se tentar controlar o clube adversário, rejeitar.

## 6. WebSocket

Endpoint:

/ws/matches/{match_id}

Os dois usuários entram na mesma sala lógica.

Criar `MatchRoomManager`.

Cada MatchRoom mantém em memória:

match_id
connections
engine
state
command_queue
lock
rng_state

## 7. Motor independente de conexão

O MatchEngine não usa quantidade de usuários conectados para decidir o resultado.

A conexão influencia apenas:
- apresentação
- emissão de eventos ao vivo
- possibilidade de comandos humanos

## 8. Baixo consumo de servidor

Usar simulação discreta por minuto/bloco.

Fluxo:

simular bloco
→ atualizar estado
→ gerar evento se necessário
→ aguardar tick visual apenas se houver usuário assistindo

Não fazer processamento pesado a cada segundo real.

## 9. Relógio no cliente

Backend envia:
- minuto lógico
- timestamp de referência
- velocidade
- status

React Native anima o relógio localmente.

Não enviar uma mensagem por minuto apenas para atualizar relógio.

Fazer sincronização periódica.

## 10. Event-driven

Transmitir apenas eventos relevantes:

kickoff
attack
chance
shot
goal
foul
card
penalty
injury
substitution
tactics_change
halftime
fulltime

## 11. Estado ao vivo

Criar `LiveMatchState`:

match_id
current_minute
current_period
home_score
away_score
home_possession
away_possession
home_attacks
away_attacks
home_chances
away_chances
home_shots
away_shots
home_shots_on_target
away_shots_on_target
home_fouls
away_fouls
home_yellow_cards
away_yellow_cards
home_red_cards
away_red_cards
paused
simulation_speed
updated_at

## 12. Sensação de realidade

Para usuário conectado, mostrar:
- relógio
- placar
- posse
- ataques
- chances
- finalizações
- cartões
- lesões
- substituições
- condição
- narração
- alterações táticas

## 13. Narração

Criar `MatchNarrationService`.

Exemplos:

"12' João avança pelo meio."
"18' Grande chance para o time da casa."
"24' Defesa do goleiro."
"31' GOL! Carlos finaliza no canto."
"44' Cartão amarelo para Marcos."
"63' Substituição: Paulo entra no lugar de André."

Narrar apenas eventos relevantes.

## 14. Suspense visual

O servidor pode gerar rapidamente:

ataque
→ chance
→ finalização
→ gol/defesa

A UI apresenta os passos com pequenos intervalos visuais.

Isso não altera o motor nem aumenta significativamente CPU.

## 15. Velocidades

Permitir:
- 1x
- 2x
- 4x

Sugestão:
- 1x: 1 minuto virtual ≈ 1 segundo real
- 2x: 0,5 s
- 4x: 0,25 s

Velocidade altera apenas apresentação.

## 16. Partida sem usuário

Se `connections = 0`:

simulate_to_end()

Persistir:
- resultado
- estatísticas
- eventos relevantes
- snapshots necessários

## 17. Partida com usuário

Se houver pelo menos um usuário assistindo:

usar modo cadenciado.

O MatchEngine continua discreto; a sala apenas controla a apresentação.

## 18. Usuário ausente

Não usar IA completa automaticamente.

O clube ausente mantém as decisões pré-jogo.

## 19. Fallback obrigatório

Criar `AutoMatchFallbackService`.

Usar apenas quando necessário para a partida continuar:
- lesão incapacitante
- goleiro expulso
- escalação inválida
- jogador indisponível por erro de estado

O fallback faz o mínimo necessário e não muda estratégia sem necessidade.

## 20. Entrada tardia

Ao conectar, enviar:
- minuto
- placar
- estatísticas
- eventos recentes
- titulares
- banco
- substituições usadas
- cartões
- lesões
- condição
- tática atual

Controle passa a valer no próximo bloco lógico.

## 21. Comandos em jogo

Permitir:
- substitution
- formation_change
- play_style_change
- marking_change
- attack_focus_change
- combined_change

Persistir em `match_commands`.

## 22. Aplicação de comandos

Fluxo:

cliente envia
→ autentica
→ valida clube
→ valida partida
→ adiciona à fila
→ aplica antes do próximo bloco
→ recalcula estado futuro
→ transmite resultado

## 23. Concorrência

Dois usuários podem mandar comandos quase simultaneamente.

Usar:
- command_queue
- match lock
- version
- sequence_number

Ordenação:
1. timestamp do servidor
2. sequence_number

Cada comando afeta apenas o próprio clube.

## 24. Pausa tática

Criar `tactical_pause`.

Sugestão:

MAX_TACTICAL_PAUSES_PER_USER = 3
TACTICAL_PAUSE_SECONDS = 15

Em humano x humano, a pausa é global.

## 25. Intervalo

No minuto 45:

status = halftime

Permitir:
- substituições
- formação
- estilo
- marcação
- foco

Continuar após confirmação ou timeout.

## 26. Desconexão

Se usuário desconectar:
- marcar offline
- remover conexão
- partida continua

Não:
- reiniciar
- cancelar
- pausar indefinidamente

## 27. Reconexão

Ao voltar:

GET /api/matches/{id}/live-state

ou reconexão WebSocket.

Enviar snapshot + eventos posteriores.

## 28. Queda dos dois usuários

Se `connections = 0`, preferir:

simulate_to_end()

Isso libera recursos.

## 29. Determinismo

Mesma seed + mesmos inputs + mesmos comandos nos mesmos minutos = mesmo resultado.

Independente de:
- 0/1/2 usuários
- velocidade
- reconexão
- dispositivo

## 30. Snapshots

Não salvar Mongo a cada minuto.

Sugestão:
0'
15'
30'
45'
60'
75'
90'

Collection `match_live_snapshots`:

match_id
minute
rng_state
score
stats
lineups
tactics
discipline
condition
substitutions
created_at

## 31. Eventos persistidos

Persistir:
- goal
- card
- penalty
- injury
- substitution
- tactics_change
- halftime
- fulltime

Eventos menores podem ser agregados.

## 32. Baixo consumo de banco

No início:
carregar `MatchContext` em memória.

Durante:
processar em memória.

Persistir apenas eventos importantes, snapshots e estado final.

## 33. Escalabilidade inicial

Primeira versão:

FastAPI único
MatchRoomManager em memória

rooms[match_id]

Sem Redis inicialmente.

## 34. Escalabilidade futura

Quando houver múltiplas instâncias:

usar Redis para:
- distributed lock
- room ownership
- pub/sub
- presence
- command routing

## 35. Humano x bot

Mesma arquitetura.

Humano usa WebSocket.
Bot usa BotMatchManager.

## 36. Bot x bot

Sem WebSocket.

simulate_to_end()

## 37. Endpoints

WebSocket:
/ws/matches/{match_id}

REST:
GET /api/matches/{id}/live-state
GET /api/matches/{id}/events
POST /api/matches/{id}/commands/substitution
POST /api/matches/{id}/commands/formation
POST /api/matches/{id}/commands/tactics
POST /api/matches/{id}/pause
POST /api/matches/{id}/resume

## 38. Mensagens WebSocket

Servidor → cliente:
- match_state
- match_event
- sync
- command_applied
- command_rejected
- participant_connected
- participant_disconnected
- halftime
- match_finished

Cliente → servidor:
- join
- heartbeat
- substitution
- formation_change
- tactics_change
- pause_request
- resume

## 39. Heartbeat

Sugestão:
10 a 20 segundos.

## 40. Velocidade humano x humano

Velocidade compartilhada pela sala.

Sugestão inicial:
- humano x humano: 1x fixo
- humano x bot: 1x, 2x ou 4x

## 41. Pular para final

Humano x humano:
não permitir unilateralmente enquanto o outro estiver conectado.

0 usuários:
simulate_to_end()

Humano x bot:
permitir pular para final.

## 42. Privacidade tática

Não revelar configuração exata do adversário.

Exemplo:
"O adversário adotou postura mais ofensiva."

Evitar:
"Adversário mudou para all_out_attack + very_heavy + center."

## 43. Interface

Cabeçalho:
- clubes
- placar
- minuto

Centro:
- narração
- eventos
- indicador de pressão

Estatísticas:
- posse
- ataques
- chances
- chutes

Controles:
- tática
- formação
- substituição

## 44. Indicador de pressão

Criar `match_momentum` apenas visual.

Derivar dos últimos minutos:
- ataques
- chances
- posse
- finalizações

Não alterar o motor.

## 45. Testes obrigatórios

### Teste A
2 usuários conectados:
- mesmo estado
- mesmos eventos
- comandos independentes

### Teste B
1 usuário:
- partida continua
- ausente mantém configuração

### Teste C
0 usuários:
- partida termina normalmente

### Teste D
entrada no minuto 60:
- estado correto
- controle dali em diante

### Teste E
desconexão/reconexão:
- sem duplicidade

### Teste F
comandos simultâneos:
- ordem determinística

## 46. Teste crítico de presença

Executar mesma partida:

A: 0 usuários
B: 1 usuário assistindo sem comandos
C: 2 usuários assistindo sem comandos

Obrigatório:
- mesmo placar
- mesmos eventos
- mesmas estatísticas

A presença do usuário nunca altera o resultado.

## 47. Teste de decisão

Mesma seed.

Partida A:
sem alteração.

Partida B:
usuário muda tática no minuto 60.

Até 60':
eventos idênticos.

Após 60':
podem divergir por causa da decisão.

## 48. Objetivo final

Entregar:
- sensação de jogo ao vivo
- decisões durante a partida
- 2 usuários no mesmo jogo
- funcionamento com usuário ausente
- baixo consumo de servidor
- baixo I/O de banco
- determinismo
- reconexão
- segurança
- escalabilidade futura

Regra principal:

A partida existe independentemente dos usuários estarem online.

Estar online apenas permite acompanhar e tomar decisões enquanto ela acontece.
