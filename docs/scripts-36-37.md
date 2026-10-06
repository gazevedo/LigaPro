# Scripts 36–37

Uma sessão autoritativa avança o mesmo motor de produção por blocos. Abrir a sala não pré-calcula o resultado. Liga, copa (incluindo prorrogação/pênaltis) e amistosos usam o mesmo fechamento e relatório das partidas offline.

- WebSocket autenticado `/ws/matches/{id}`; token em Authorization ou subprotocolo, nunca na URL.
- Estado, eventos e comandos REST em `/api/matches/{id}/live-state`, `/events`, `/commands/{substitution|formation|tactics}`, `/pause`, `/resume` e `/speed`.
- Técnicos controlam apenas o próprio clube. A tática exata do adversário permanece privada.
- Zero usuários: conclusão automática. Um usuário: o ausente conserva suas decisões pré-jogo. Dois usuários: mesma sala, relógio, placar e eventos.
- Velocidade 1×/2×/4× altera apenas cadência. Entre clubes humanos, 1×; nenhum técnico pode pular enquanto o outro acompanha.
- Três pausas táticas de até 15 segundos por usuário; intervalo retoma por confirmação ou timeout. Desconexão nunca impede a conclusão.
- Comandos têm identificador idempotente, sequência do servidor, fila, lock e confirmação. Substituições respeitam banco, elegibilidade e limite de cinco.
- Eventos e snapshots são gravados juntos por checkpoint, sem consultas por segundo. Reinício recupera contexto inicial e comandos até o checkpoint, sem repetir efeitos financeiros ou esportivos.
- Fallback mínimo para lesão incapacitante, goleiro ausente ou escalação inválida, sem inventar estratégia para humanos ausentes.
- Mobile: relógio local, narração, estatísticas, pressão visual, tática, elenco, banco, overlays e transição para pós-jogo.

Esta versão pressupõe **um processo FastAPI**. Múltiplas instâncias exigirão ownership/locks distribuídos e pub/sub, conforme o script 37.

Validação: determinismo offline/ao vivo, velocidades/presença/skip, comandos a partir de 60', copa/prorrogação/pênaltis, pausa, WebSocket com dois técnicos, privacidade, reconexão/replay, deduplicação e conclusão após desconexão; testes mobile e regressões relacionadas.
