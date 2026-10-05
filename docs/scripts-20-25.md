# Scripts 20–25

- **20:** revista a economia, com centavos inteiros, receitas mensais e folha inicial de R$ 13.500 para 25 jogadores. As alterações pendentes dos scripts 16–20 integram esta entrega.
- **21:** curvas não lineares e serviços separados para salário de referência e valor de mercado. Idade, estrelas, posição, desempenho, contrato, divisão e reputação compõem o preço; disponibilidade define a faixa pedida. O salário assinado permanece no contrato. A fórmula é própria, inspirada na escala pedida, sem alegar equivalência à fórmula oficial do Brasfoot.
- **22 e adendo:** profissionais com GK/FB/CB/MID/ATT, lado, sete habilidades e características inatas. Migração idempotente preserva jogadores, contratos e caixa, remove potencial profissional e atributos descontinuados e leva o progresso técnico para registro separado. Potencial interno permanece nos juniores. Treino evolui a habilidade escolhida e recalcula a força geral. As telas usam o modelo revisado.
- **23:** condição física persistente, desgaste por minutos/idade/intensidade e recuperação pelo tempo lógico e centro médico. Lesões têm severidade e retorno previsto, retiram o jogador da partida e bloqueiam escalação e treino normal. Bots substituem lesionados. Liga e copa avançam em ordem cronológica, inclusive no fechamento offline da temporada.
- **24:** gestor dos bots com escalação, tática, substituições, mercado, contratos, finanças, treino, base e estádio. Usa os serviços comuns, respeita caixa e folha, atende carências e anuncia excedentes. Decisões e impedimentos ficam em `bot_decisions`. Obras exigem lotação recorrente e reserva financeira.
- **25:** proposta → vendedor aceita/contrapropõe/recusa → jogador avalia salário, prazo, reputação, divisão e titularidade → comprador confirma. Somente a confirmação na janela movimenta dinheiro e propriedade. Endpoints antigos passam pelo mesmo fluxo. Empréstimos têm prazo, taxa e participação salarial, sem compra automática; retornam offline. Contratação livre tem taxa zero e avaliação salarial do jogador.

## Calibração

Execução reproduzível: `PYTHONPATH=backend python backend/scripts/calibrate_player_management.py --output docs/player-management-calibration.json`.

A amostra explícita de **10.000 jogadores** cobre o mercado, incluindo a cauda de elite; o elenco inicial continua limitado à faixa de força anterior. Mediana **R$ 9.600**, P90 **R$ 29.800**, P99 **R$ 74.700**. Todos dentro das faixas do script 21.

Em **10.000 partidas**, ocorreram **638 lesões** (0,0638 por partida): 470 leves, 143 moderadas e 25 graves. A duração média foi 2,448 partidas. Com condição 100, jovens tiveram 0,0336 lesão/jogo; com condição 35, 0,1000. Para idade 36, as taxas foram 0,0488 e 0,1216, respectivamente. Os grupos têm 1.250 partidas cada; pequenas inversões entre faixas próximas são variação amostral. Os dados completos estão em `player-management-calibration.json`.

## Verificação

Testes relacionados cobrem curvas e migração, bloqueio/recuperação de lesões, negociação e concorrência, empréstimos e salários proporcionais, ações concretas dos bots e temporadas completas com caixa e escalações válidas. O worker de tempo real é isolado nos testes; o avanço offline é acionado explicitamente. Ruff, ESLint, TypeScript e testes mobile verificam as telas e os serviços alterados.
