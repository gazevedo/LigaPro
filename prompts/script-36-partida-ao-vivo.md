# Script 36 — Partida ao Vivo / Acompanhamento em Tempo Real

Objetivo: permitir acompanhar a partida em tempo real, no estilo Brasfoot, exibindo o avanço do jogo, eventos, estatísticas e permitindo mudanças táticas e substituições durante a simulação.

## 1. Princípio

A partida não deve ser simulada inteira antes de abrir a tela.

O MatchEngine deve avançar progressivamente em blocos curtos e publicar o estado atual.

Fluxo:

MatchStart
→ minuto 0
→ simular próximo bloco
→ gerar eventos
→ atualizar estado
→ publicar para UI
→ aguardar próximo tick
→ aplicar comandos pendentes
→ continuar
→ fim da partida

As mudanças feitas pelo usuário devem afetar apenas os minutos futuros.

## 2. Velocidade da partida

Criar opções:

1x
2x
4x

Também permitir:

- pausar
- continuar
- ir para o intervalo
- ir para o final

Configuração sugerida:

LIVE_MATCH_REAL_SECONDS_PER_GAME_MINUTE = 1.0

Exemplo:

1x:
1 segundo real = 1 minuto de jogo

2x:
0,5 segundo = 1 minuto

4x:
0,25 segundo = 1 minuto

A velocidade deve ser apenas de exibição.

Ela não pode alterar probabilidades ou resultados.

## 3. Estado da partida

Criar:

LiveMatchState

Campos:

match_id
status
current_minute
current_second
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
current_period
simulation_speed
paused
updated_at

## 4. Status

status:

not_started
first_half
halftime
second_half
finished

Preparar futuramente:

extra_time
penalties

## 5. Timeline de eventos

A tela deve possuir feed cronológico.

Eventos:

kickoff
attack
chance
shot_off_target
shot_saved
goal
foul
yellow_card
second_yellow
red_card
penalty_awarded
penalty_goal
penalty_saved
penalty_missed
injury
substitution
formation_change
play_style_change
marking_change
attack_focus_change
halftime
fulltime

## 6. Narração textual

Criar:

MatchNarrationService

Cada evento deve poder gerar uma mensagem curta.

Exemplos:

"12' João avança pelo meio."

"18' Grande chance para o time da casa."

"24' Chute defendido pelo goleiro."

"31' GOL! Carlos finaliza no canto."

"44' Cartão amarelo para Marcos."

"63' Substituição: Paulo entra no lugar de André."

Não precisa narrar cada minuto.

Narrar apenas eventos relevantes.

## 7. Persistência de eventos

Usar:

match_events

Campos:

match_id
minute
second
type
club_id
player_id
secondary_player_id
metadata
created_at

A UI deve ler eventos em ordem cronológica.

## 8. Atualização da interface

A tela deve receber atualizações incrementais.

Opções técnicas:

- WebSocket
- Server-Sent Events
- polling curto

Preferência:

WebSocket

FastAPI deve fornecer endpoint de conexão ao vivo por partida.

Exemplo conceitual:

/ws/matches/{match_id}

## 9. Fluxo WebSocket

Servidor envia:

match_state
match_event
command_applied
command_rejected
match_finished

Cliente envia:

pause
resume
set_speed
substitution
formation_change
tactics_change
combined_change

Comandos sensíveis devem continuar passando pela validação do backend.

## 10. Tela MatchLiveScreen

Estrutura sugerida:

### Cabeçalho

- mandante
- visitante
- placar
- minuto
- período

### Painel de estatísticas

- posse
- ataques
- chances
- finalizações
- finalizações no alvo
- faltas
- cartões

### Feed

Lista de eventos recentes.

### Controles

- velocidade
- pausa
- intervalo
- final

### Área tática

- formação
- estilo
- marcação
- foco dos ataques

### Plantel

- titulares
- condição física
- energia
- cartões
- lesões
- banco

## 11. Substituições ao vivo

Ao tocar em jogador:

- selecionar jogador que sai
- selecionar reserva
- confirmar

Validar:

- limite de substituições
- reserva elegível
- jogador não utilizado anteriormente
- status da partida
- posição/formação válida

## 12. Mudança de formação

Durante a partida permitir escolher nova formação.

Após confirmação:

- recalcular PositionFit
- recalcular setores
- recalcular contribuições futuras

Não alterar eventos passados.

## 13. Mudança de estilo

Permitir:

balanced
all_out_attack
counter_attack

## 14. Mudança de marcação

Permitir:

light
heavy
very_heavy

## 15. Mudança de foco

Permitir:

normal
center
wings

## 16. Pausa

A pausa deve congelar apenas a progressão temporal.

Não deve:

- resetar seed
- reprocessar eventos
- alterar RNG

## 17. Pular para intervalo

Ao escolher:

skip_to_halftime

O backend simula rapidamente até minuto 45.

A UI recebe apenas eventos relevantes gerados nesse intervalo.

## 18. Pular para final

Ao escolher:

skip_to_end

O backend simula até o fim mantendo exatamente a mesma lógica e seed.

Não criar resultado diferente do que seria obtido acompanhando minuto a minuto.

## 19. Determinismo

Regra obrigatória:

assistir em 1x, 2x, 4x ou pular não pode alterar o resultado.

Com:

mesma seed
mesma escalação
mesmas táticas
mesmos comandos nos mesmos minutos

→ resultado idêntico.

## 20. Intervalo

Ao minuto 45:

status = halftime

Pausar automaticamente por alguns segundos ou aguardar usuário.

Permitir:

- substituições
- mudança de formação
- mudança tática

Depois:

start_second_half

## 21. Comandos pendentes

Usar:

match_commands

Status:

pending
applied
rejected
cancelled

O MatchEngine aplica comandos antes de iniciar o próximo bloco.

## 22. Concorrência

Proteger partida com lock/version.

Não permitir:

- dois engines simulando a mesma partida
- comando aplicado duas vezes
- evento duplicado

## 23. Reconexão

Se o usuário fechar a tela:

a partida deve continuar conforme configuração.

Ao retornar:

GET /api/matches/{match_id}/live-state

deve reconstruir:

- minuto
- placar
- estatísticas
- eventos
- escalação atual
- tática atual

## 24. Modo não acompanhado

Se o usuário não abrir a partida:

o backend deve conseguir simular normalmente.

Não depender da UI para concluir a partida.

## 25. Bots

Bots usam:

BotMatchManager

Durante partida:

- fazem substituições
- alteram estilo
- alteram marcação
- alteram foco
- respondem ao placar

As decisões dos bots devem ocorrer em minutos lógicos, não em tempo real.

## 26. Áudio

Opcional.

Preparar estrutura para sons:

- apito
- gol
- cartão
- torcida

Não é obrigatório nesta fase.

## 27. Vibração

No mobile, opcionalmente:

- gol
- cartão vermelho
- fim da partida

Usar configuração do usuário.

## 28. Notificações visuais

Eventos importantes podem aparecer como overlay curto:

GOL
CARTÃO VERMELHO
PÊNALTI
LESÃO

Sem bloquear a partida.

## 29. Estatísticas em tempo real

As estatísticas devem vir dos eventos reais.

Não gerar posse, ataques ou chutes independentemente do MatchEngine.

## 30. Posse

Atualizar progressivamente por blocos.

Ao final:

home_possession + away_possession = 100

Com arredondamento adequado.

## 31. Tela simplificada

Modo inicial pode ser somente textual.

Não é necessário:

- campo 2D animado
- jogadores se movimentando
- física visual

O estilo deve lembrar acompanhamento textual/estatístico do Brasfoot.

## 32. Performance

Não fazer consultas Mongo a cada segundo.

Carregar MatchContext em memória.

Persistir:

- eventos
- snapshots periódicos
- estado importante

## 33. Snapshot

Salvar periodicamente:

match_live_snapshot

Campos:

match_id
minute
score
stats
lineups
tactics
substitutions
discipline
updated_at

## 34. Recuperação após falha

Se servidor reiniciar:

- carregar último snapshot
- carregar comandos/eventos posteriores
- continuar sem duplicar eventos

## 35. APIs

GET
/api/matches/{id}/live-state

GET
/api/matches/{id}/events

POST
/api/matches/{id}/commands/substitution

POST
/api/matches/{id}/commands/tactics

POST
/api/matches/{id}/commands/formation

WebSocket:
/ws/matches/{id}

## 36. Segurança

Somente dono do clube pode enviar comandos para o próprio time.

Outros usuários autenticados podem futuramente assistir, mas não controlar.

## 37. Testes

Criar testes para:

- início
- avanço de minuto
- evento
- gol
- intervalo
- segundo tempo
- fim
- pausa
- velocidade
- skip halftime
- skip end
- substituição
- tática
- reconexão
- seed determinística
- comando duplicado
- bot

## 38. Teste crítico de determinismo

Executar a mesma partida:

A:
assistida inteira em 1x

B:
assistida em 4x

C:
skip_to_end

Com nenhuma mudança tática.

Resultado obrigatório:

- mesmo placar
- mesmos eventos
- mesmos minutos
- mesmas estatísticas

## 39. Integração com tela pós-jogo

Ao finalizar:

MatchLiveScreen
→ MatchReportScreen

A tela pós-jogo usa exatamente os eventos e estatísticas produzidos durante a partida.

## 40. Resultado esperado

O usuário deve sentir que está acompanhando a partida acontecendo e conseguir intervir durante o jogo.

A experiência deve ser rápida, textual, estratégica e compatível com o estilo de manager do Brasfoot.
