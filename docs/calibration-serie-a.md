# Calibração da Série A

68,400 partidas; 20 clubes sintéticos de força 70, 38 rodadas, nove estratégias e cenários fixos/pares com adaptação.

## Estratégias fixas

| Estratégia | Jogos | Vitórias | Empates | Derrotas | Pontos/jogo |
| --- | ---: | ---: | ---: | ---: | ---: |
| counter_attack/very_heavy | 7600 | 2927 | 2372 | 2301 | 1.4675 |
| balanced/very_heavy | 7600 | 2843 | 2523 | 2234 | 1.4542 |
| balanced/heavy | 7600 | 2786 | 2279 | 2535 | 1.3996 |
| counter_attack/heavy | 7600 | 2815 | 2188 | 2597 | 1.3991 |
| all_out_attack/very_heavy | 7600 | 2646 | 2305 | 2649 | 1.3478 |
| counter_attack/light | 7600 | 2644 | 2127 | 2829 | 1.3236 |
| balanced/light | 7600 | 2622 | 2192 | 2786 | 1.3234 |
| all_out_attack/heavy | 7600 | 2516 | 2087 | 2997 | 1.2678 |
| all_out_attack/light | 7600 | 2351 | 2027 | 3222 | 1.1947 |

### Padrão de marcação

A marcação muito pesada teve a maior média nos três estilos testados.
Vantagem média da marcação muito pesada contra a leve, agrupando os estilos: +0.1426 ponto/jogo.
Intervalo aproximado de 95%: [+0.1090, +0.1762].
Esse padrão merece acompanhamento; não implica uma combinação universalmente dominante e não inclui efeitos disciplinares entre rodadas.

Nenhuma estratégia atingiu o critério de dominância.

Critério: dez seeds ou mais; vantagem sobre todas as alternativas acima de 0,06 ponto/jogo no limite inferior do intervalo aproximado de 95% por seed.

## Troca após 3 jogos sem vitória

Variação média do clube que troca: -0.233 pontos por temporada.
Intervalo aproximado de 95%: [-2.490, +2.023] pontos.
Trocas realizadas: 414. Só um clube troca em cada comparação; os adversários mantêm suas estratégias.

## Classificações do primeiro cenário

As classificações abaixo exemplificam o primeiro par. O JSON contém os resultados de todos os clubes em todas as temporadas e o histórico de cada troca.

### Estratégias fixas — seed 35000, rotação 0

| Pos. | Clube | P | V | E | D | GP | GC | Estratégias utilizadas (jogos) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | Clube Série A 20 | 63 | 17 | 12 | 9 | 39 | 27 | balanced/heavy: 38 |
| 2 | Clube Série A 09 | 59 | 14 | 17 | 7 | 44 | 31 | counter_attack/very_heavy: 38 |
| 3 | Clube Série A 17 | 58 | 17 | 7 | 14 | 41 | 34 | counter_attack/heavy: 38 |
| 4 | Clube Série A 06 | 57 | 15 | 12 | 11 | 44 | 29 | all_out_attack/very_heavy: 38 |
| 5 | Clube Série A 03 | 57 | 16 | 9 | 13 | 35 | 31 | balanced/very_heavy: 38 |
| 6 | Clube Série A 18 | 55 | 14 | 13 | 11 | 42 | 33 | counter_attack/very_heavy: 38 |
| 7 | Clube Série A 01 | 55 | 14 | 13 | 11 | 44 | 41 | balanced/light: 38 |
| 8 | Clube Série A 10 | 55 | 15 | 10 | 13 | 39 | 36 | balanced/light: 38 |
| 9 | Clube Série A 02 | 54 | 13 | 15 | 10 | 37 | 35 | balanced/heavy: 38 |
| 10 | Clube Série A 15 | 51 | 14 | 9 | 15 | 37 | 39 | all_out_attack/very_heavy: 38 |
| 11 | Clube Série A 19 | 51 | 13 | 12 | 13 | 43 | 47 | balanced/light: 38 |
| 12 | Clube Série A 16 | 51 | 13 | 12 | 13 | 34 | 41 | counter_attack/light: 38 |
| 13 | Clube Série A 11 | 50 | 13 | 11 | 14 | 38 | 42 | balanced/heavy: 38 |
| 14 | Clube Série A 12 | 49 | 11 | 16 | 11 | 24 | 20 | balanced/very_heavy: 38 |
| 15 | Clube Série A 14 | 49 | 13 | 10 | 15 | 46 | 54 | all_out_attack/heavy: 38 |
| 16 | Clube Série A 07 | 47 | 10 | 17 | 11 | 35 | 38 | counter_attack/light: 38 |
| 17 | Clube Série A 04 | 41 | 8 | 17 | 13 | 43 | 49 | all_out_attack/light: 38 |
| 18 | Clube Série A 05 | 40 | 9 | 13 | 16 | 47 | 55 | all_out_attack/heavy: 38 |
| 19 | Clube Série A 13 | 38 | 9 | 11 | 18 | 40 | 54 | all_out_attack/light: 38 |
| 20 | Clube Série A 08 | 35 | 7 | 14 | 17 | 32 | 48 | counter_attack/heavy: 38 |

### Com troca de estratégia — seed 35000, rotação 0

| Pos. | Clube | P | V | E | D | GP | GC | Estratégias utilizadas (jogos) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | Clube Série A 20 | 63 | 17 | 12 | 9 | 38 | 28 | balanced/heavy: 38 |
| 2 | Clube Série A 09 | 62 | 15 | 17 | 6 | 45 | 30 | counter_attack/very_heavy: 38 |
| 3 | Clube Série A 03 | 60 | 17 | 9 | 12 | 36 | 30 | balanced/very_heavy: 38 |
| 4 | Clube Série A 17 | 58 | 17 | 7 | 14 | 43 | 34 | counter_attack/heavy: 38 |
| 5 | Clube Série A 06 | 56 | 15 | 11 | 12 | 43 | 30 | all_out_attack/very_heavy: 38 |
| 6 | Clube Série A 10 | 56 | 15 | 11 | 12 | 38 | 33 | balanced/light: 38 |
| 7 | Clube Série A 18 | 55 | 14 | 13 | 11 | 44 | 33 | counter_attack/very_heavy: 38 |
| 8 | Clube Série A 02 | 54 | 13 | 15 | 10 | 37 | 35 | balanced/heavy: 38 |
| 9 | Clube Série A 15 | 53 | 15 | 8 | 15 | 37 | 38 | all_out_attack/very_heavy: 38 |
| 10 | Clube Série A 16 | 53 | 14 | 11 | 13 | 35 | 41 | counter_attack/light: 38 |
| 11 | Clube Série A 19 | 51 | 13 | 12 | 13 | 43 | 47 | balanced/light: 38 |
| 12 | Clube Série A 14 | 51 | 14 | 9 | 15 | 47 | 54 | all_out_attack/heavy: 38 |
| 13 | Clube Série A 11 | 49 | 13 | 10 | 15 | 35 | 41 | balanced/heavy: 38 |
| 14 | Clube Série A 01 | 48 | 13 | 9 | 16 | 37 | 45 | balanced/light: 5; balanced/heavy: 4; balanced/very_heavy: 9; all_out_attack/light: 6; all_out_attack/heavy: 3; all_out_attack/very_heavy: 5; counter_attack/light: 6 |
| 15 | Clube Série A 12 | 47 | 10 | 17 | 11 | 23 | 20 | balanced/very_heavy: 38 |
| 16 | Clube Série A 07 | 46 | 10 | 16 | 12 | 34 | 38 | counter_attack/light: 38 |
| 17 | Clube Série A 04 | 41 | 8 | 17 | 13 | 44 | 49 | all_out_attack/light: 38 |
| 18 | Clube Série A 13 | 41 | 10 | 11 | 17 | 43 | 52 | all_out_attack/light: 38 |
| 19 | Clube Série A 05 | 40 | 9 | 13 | 16 | 48 | 54 | all_out_attack/heavy: 38 |
| 20 | Clube Série A 08 | 35 | 7 | 14 | 17 | 31 | 49 | counter_attack/heavy: 38 |

Limites: elencos reiniciados por partida, sem evolução de condição, lesões ou suspensões entre rodadas, mercado ou banco de dados. Intervalos exploratórios, sem correção para comparações múltiplas. A política de troca é cíclica; os resultados não demonstram o efeito de outras políticas.
