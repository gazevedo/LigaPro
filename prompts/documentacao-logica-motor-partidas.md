# Documentação — Lógica do Motor de Partidas

## 1. Objetivo

O motor de partidas transforma a escalação dos dois clubes em um resultado de futebol plausível.

A regra principal é:

> um time melhor deve possuir maior probabilidade de vencer, mas nunca vitória garantida.

A simulação não escolhe diretamente um placar a partir da força média dos clubes.

Ela reproduz uma sequência simplificada do futebol:

**disputa do meio → ataque → chance → finalização → resultado da jogada**

Isso faz com que escalação, formação e qualidade dos setores realmente tenham efeito no jogo.

---

## 2. Modelo simplificado dos jogadores

Nesta fase cada jogador possui quatro informações esportivas principais:

- posição
- força
- nível de treinamento
- doença

Posições:

- GK — goleiro
- DEF — defensor
- MID — médio
- ATT — atacante

O atributo mais importante para a partida é `strength`.

O `training_level` não aumenta diretamente a força durante a partida. Ele é um contador de evolução. Ao chegar a 100, aumenta `strength` em 1 e volta para zero.

---

## 3. Força efetiva

Um jogador não precisa necessariamente utilizar 100% da sua força nominal.

Exemplo:

Jogador:

- força: 70
- condição: 95%

Força efetiva:

70 × 0,95 = 66,5

A doença poderá reduzir esse multiplicador.

Assim, um jogador forte mas em condição ruim pode render menos.

---

## 4. O time não possui apenas uma força

Cada equipe será dividida em quatro valores:

- goleiro
- defesa
- meio
- ataque

Exemplo:

Clube A:

- goleiro: 68
- defesa: 72
- meio: 76
- ataque: 81

Clube B:

- goleiro: 75
- defesa: 78
- meio: 63
- ataque: 65

Não existe, portanto, apenas:

Clube A = 74
Clube B = 70

Isso permite confrontos diferentes dentro da mesma partida.

---

## 5. Contribuição das posições

Um atacante influencia principalmente o ataque.

Um médio influencia fortemente o meio, mas também ajuda ataque e defesa.

Um defensor influencia defesa e um pouco o meio.

Um goleiro influencia essencialmente a defesa.

Exemplo inicial:

| Posição | Defesa | Meio | Ataque |
|---|---:|---:|---:|
| GK | 100% | 0% | 0% |
| DEF | 100% | 20% | 0% |
| MID | 25% | 100% | 35% |
| ATT | 0% | 15% | 100% |

Esses percentuais são parâmetros de balanceamento.

---

## 6. Formação

A formação não cria força do nada.

Ela redistribui a eficiência do time.

Exemplo:

### 4-4-2

Equilibrada.

- defesa: 1,00
- meio: 1,00
- ataque: 1,00

### 4-3-3

Mais ofensiva.

- defesa: 0,96
- meio: 0,98
- ataque: 1,08

### 5-3-2

Mais defensiva.

- defesa: 1,10
- meio: 0,94
- ataque: 0,96

Isso cria escolhas reais para o usuário.

Um time pode ganhar ataque sacrificando parte da defesa.

---

## 7. Mando de campo

O mandante recebe uma pequena vantagem.

Exemplo:

5%.

Essa vantagem não significa 5% a mais de chance direta de vitória.

Ela modifica levemente alguns valores utilizados durante a criação das jogadas, principalmente meio e ataque.

O objetivo é reproduzir a vantagem de jogar em casa sem tornar o resultado previsível.

---

## 8. Divisão dos 90 minutos

Em vez de simular 90 iterações individuais, a primeira versão usa blocos de 5 minutos.

Uma partida possui:

90 / 5 = 18 blocos

Exemplo:

- 1–5
- 6–10
- 11–15
- ...
- 86–90

Em cada bloco o motor decide se algo relevante acontece.

Isso mantém a lógica simples e rápida.

---

## 9. Primeiro passo: quem controla a jogada?

O principal fator é o meio-campo.

Exemplo:

Clube A meio = 70

Clube B meio = 50

Probabilidade aproximada do A controlar a jogada:

70 / (70 + 50)

70 / 120

≈ 58,3%

O Clube B fica com aproximadamente:

41,7%

Depois é aplicada pequena variação aleatória.

Portanto o melhor meio controla mais ações, mas não todas.

---

## 10. Controle não significa chance

Mesmo que o time ganhe a disputa de meio, ele ainda precisa construir o ataque.

São considerados:

- meio ofensivo
- ataque
- defesa adversária

Exemplo conceitual:

Clube A:

meio = 70
ataque = 80

Clube B:

defesa = 75

O A possui boa possibilidade de transformar o controle em ataque.

Se sua força ofensiva fosse muito menor que a defesa adversária, muitos ataques morreriam antes de virar chance.

---

## 11. Ataque x chance

Um ataque pode terminar sem uma oportunidade real.

Fluxo:

controle da bola

→ tentativa de ataque

→ defesa adversária consegue parar?

Se sim:

fim do evento.

Se não:

chance criada.

Isso impede que cada domínio do meio resulte em chute.

---

## 12. Qualidade da chance

Uma chance pode ser:

- baixa
- média
- alta

Exemplos conceituais:

### Baixa

Finalização pressionada ou distante.

Multiplicador:

0,65

### Média

Chance normal.

Multiplicador:

1,00

### Alta

Situação muito favorável.

Multiplicador:

1,40

A qualidade depende principalmente da diferença entre ataque e defesa.

---

## 13. Quem finaliza?

O sistema escolhe um jogador da equipe.

Pesos iniciais:

- atacante: 65
- médio: 25
- defensor: 9
- goleiro: 1

Um atacante, portanto, será escolhido muito mais frequentemente.

Dentro da posição, jogadores mais fortes podem receber peso maior.

Assim, os melhores atacantes tendem a marcar mais gols naturalmente.

---

## 14. Finalização

Depois de selecionar o finalizador, o motor compara ataque contra defesa.

De maneira simplificada:

**Poder ofensivo**

força de ataque do time + força do finalizador

contra:

**Poder defensivo**

força defensiva + goleiro

Depois é aplicado o modificador da qualidade da chance.

---

## 15. Função probabilística

Nunca haverá lógica:

ataque > defesa = gol.

Em vez disso, usamos uma razão:

attackPower / (attackPower + defensePower)

Exemplo:

Ataque = 140

Defesa = 120

140 / 260 = 0,538

Esse valor entra numa segunda fórmula que determina a chance final de gol.

Portanto mesmo uma chance favorável pode ser perdida.

E uma situação difícil ocasionalmente pode terminar em gol.

---

## 16. Resultado da finalização

Uma chance pode terminar em:

- gol
- defesa do goleiro
- chute para fora
- bloqueio

Na primeira versão podemos simplificar os três resultados sem gol em:

- `shot_saved`
- `shot_off_target`

Posteriormente podem existir mais tipos.

---

## 17. Exemplo completo

Clube Azul:

- defesa: 65
- meio: 70
- ataque: 78

Clube Verde:

- defesa: 72
- meio: 62
- ataque: 60

### Minuto 23

O meio do Azul possui vantagem.

O sorteio dá controle ao Azul.

### Construção

Azul tenta transformar a posse em ataque.

Seu meio 70 + ataque 78 enfrentam defesa 72.

O ataque progride.

### Chance

O motor classifica a oportunidade como média.

### Finalizador

Entre os jogadores do Azul é escolhido um atacante força 74.

### Finalização

Poder ofensivo:

ataque do time + atacante

78 + 74 = 152

Poder defensivo:

defesa + goleiro

72 + 68 = 140

O Azul possui vantagem pequena.

O motor sorteia o resultado.

Pode ocorrer:

GOOOOL

ou:

defesa do goleiro.

O mesmo lance com os mesmos valores não é automaticamente gol.

---

## 18. Por que existe aleatoriedade?

Sem aleatoriedade:

time melhor sempre venceria.

Isso destruiria a graça do campeonato.

Com aleatoriedade excessiva:

a força dos jogadores perderia importância.

O objetivo é encontrar um meio termo.

Exemplo esperado em milhares de partidas:

Time muito forte x time fraco:

- forte vence bastante
- alguns empates
- poucas derrotas

Não:

100% de vitórias.

---

## 19. Seed da partida

Cada partida recebe um número chamado `simulation_seed`.

Exemplo:

9283712

Esse número inicializa o gerador aleatório.

Se executarmos novamente:

- mesmo seed
- mesmos jogadores
- mesma formação
- mesma configuração

o resultado deve ser exatamente o mesmo.

Isso é importante para descobrir bugs.

Se um usuário reclamar de uma partida estranha, podemos reproduzi-la.

---

## 20. Estatísticas

As estatísticas devem nascer da simulação.

Não devem ser sorteadas depois.

### Posse

Quantidade de blocos controlados por cada time.

### Ataques

Quantidade de ataques que conseguiram ser iniciados.

### Chances

Ataques que superaram a resistência defensiva.

### Finalizações

Tentativas geradas.

### Finalizações no alvo

Gols + defesas.

### Gols

Chances convertidas.

Portanto todas as estatísticas estão relacionadas entre si.

---

## 21. Exemplo de estatísticas

Resultado:

Azul 2 x 1 Verde

Possível relatório:

| Estatística | Azul | Verde |
|---|---:|---:|
| Posse | 56% | 44% |
| Ataques | 17 | 13 |
| Chances | 8 | 5 |
| Finalizações | 8 | 5 |
| No alvo | 5 | 3 |
| Gols | 2 | 1 |

Esses valores são consequência dos eventos simulados.

---

## 22. Placares

O motor deve naturalmente produzir mais resultados como:

- 0x0
- 1x0
- 1x1
- 2x0
- 2x1
- 2x2
- 3x1

E poucos:

- 5x4
- 6x0
- 7x3

Não haverá regra artificial:

máximo de 5 gols.

Em vez disso, calibramos as probabilidades.

---

## 23. Simulações em massa

Antes de considerar o motor correto, devemos simular milhares de partidas automaticamente.

Exemplo:

10.000 partidas entre times equivalentes.

Analisar:

- vitórias do mandante
- empates
- vitórias do visitante
- média de gols
- distribuição dos placares

Depois:

10.000 partidas de time 80 x time 50.

Isso mostra se a força realmente está funcionando.

---

## 24. Configuração central

Todos os valores matemáticos ficam em um único ponto.

Exemplo:

`MatchEngineConfig`

Isso inclui:

- vantagem de casa
- contribuição das posições
- bônus das formações
- variação aleatória
- chance mínima/máxima
- probabilidade base de gol
- pesos dos finalizadores

Assim podemos balancear o jogo sem reescrever o motor.

---

## 25. Filosofia de balanceamento

Uma diferença pequena de força deve gerar pequena vantagem.

Uma diferença grande deve gerar vantagem clara.

Mas nunca certeza absoluta.

Exemplo conceitual:

### 70 x 70

Muito equilibrado.

### 75 x 70

75 possui vantagem pequena.

### 85 x 60

85 possui vantagem forte.

### 95 x 40

95 deve dominar quase sempre, mas ainda pode existir um resultado extremamente improvável.

---

## 26. Integração com treinamento

Treinamento:

`training_level + 1`

Ao atingir:

100

acontece:

`strength + 1`

Portanto o efeito do treinamento aparece automaticamente no motor.

Não é necessário criar uma regra especial.

Um jogador que passa de força 60 para 61 aumenta ligeiramente a força de seu setor.

---

## 27. Integração com idade

A partir dos 35 anos existe possibilidade de perda de `strength`.

Quando isso ocorrer, o jogador naturalmente passa a contribuir menos para o setor.

Novamente, não há regra especial dentro do motor.

O motor apenas lê a força atual.

---

## 28. Integração com doença

A doença modifica a força efetiva.

Exemplo:

Jogador força 80

Doença gera multiplicador 0,85.

Durante a partida:

80 × 0,85 = 68

Seu valor permanente continua 80.

A redução vale apenas para sua condição atual.

---

## 29. Bots

Bots não recebem tratamento especial.

Eles usam exatamente:

- jogadores
- formação
- força
- MatchEngine

A única diferença é que o sistema escolhe automaticamente a escalação do bot.

Isso evita resultados artificiais.

---

## 30. Evolução futura

Depois que a primeira versão estiver calibrada, o motor poderá receber:

- cartões
- faltas
- pênaltis
- lesões
- substituições
- táticas
- contra-ataques
- pressão
- posse
- retranca
- moral
- entrosamento
- clima
- cansaço
- árbitro
- prorrogação
- pênaltis

Esses sistemas devem ser acrescentados em camadas.

A base permanece:

**força → setores → disputa → ataque → chance → finalização.**

---

## 31. Resumo da lógica

```text
11 JOGADORES
     ↓
FORÇA EFETIVA
     ↓
GOLEIRO / DEFESA / MEIO / ATAQUE
     ↓
FORMAÇÃO
     ↓
MANDO
     ↓
90 MINUTOS
     ↓
DISPUTAS DE MEIO
     ↓
ATAQUES
     ↓
CHANCES
     ↓
FINALIZADORES
     ↓
ATAQUE x DEFESA + GOLEIRO
     ↓
GOL / DEFESA / FORA
     ↓
PLACAR + ESTATÍSTICAS
```

Essa deve ser a fundação matemática do jogo.
