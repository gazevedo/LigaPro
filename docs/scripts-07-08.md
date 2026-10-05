Scripts 7 e 8: táticas persistidas e plano de partida

A tela Táticas salva formação, estilo, marcação e foco e permite programar comandos para partidas futuras. O servidor aceita minutos de 0 a 85. O comando entra no próximo bloco de cinco minutos; o bloco já encerrado não muda. O agendador aplica o plano mesmo com o usuário offline.

São permitidas cinco substituições por clube, sem reentrada. Reservas mantêm sua energia até entrar. Comandos que ficaram inviáveis por transferência, aposentadoria ou expulsão são registrados como `command_rejected`; a partida continua. Formação reorganiza os titulares reais, com penalidade por improvisação e lado inadequado.

Bots escolhem os quatro presets pelo placar, força e perfil do elenco, revisam táticas aos 45/65/80 minutos e fazem substituições aos 60/75. A marcação diminui quando há risco disciplinar.

Validação tática: `calibration-script-07.json`, 36 confrontos com 10.000 jogos cada, alternando mando. Nenhuma combinação supera as outras oito por mais de dois pontos percentuais de vitórias (máximo: sete). A calibração completa do script 6 permanece em seu relatório original; o relatório 7 valida somente a matriz tática.
