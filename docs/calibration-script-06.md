# Calibração do motor — Script 6

85 cenários × 10.000 partidas; seed inicial 1729, mando alternado. Posse corresponde aos minutos de iniciativa dos blocos, não a tracking de bola.

Resultados completos, configuração, hash do motor e métricas por fase no JSON adjacente. A identifica a equipe sob teste; B é seu adversário. Nas variações de energia, moral, lado e habilidades, somente A recebe a mudança; gols/jogo somam as duas equipes.

| Cenário | Gols/jogo | Gols A/B | Empates | Vitórias A | Posse A | Ataques A/B | Chances A/B |
|---|---:|---:|---:|---:|---:|---:|---:|
| base_70_70 | 2.384 | 1.179/1.205 | 26.4% | 36.3% | 50.0% | 8.99/9.01 | 3.53/3.56 |
| base_75_70 | 2.420 | 1.360/1.060 | 25.8% | 44.6% | 51.6% | 9.28/8.72 | 3.81/3.30 |
| base_80_60 | 2.700 | 2.037/0.663 | 18.9% | 70.2% | 57.0% | 10.27/7.73 | 4.76/2.53 |
| base_60_80 | 2.676 | 0.655/2.021 | 18.9% | 11.2% | 42.8% | 7.71/10.29 | 2.50/4.77 |
| base_90_40 | 4.599 | 4.413/0.186 | 1.4% | 98.4% | 69.3% | 12.47/5.53 | 7.56/1.29 |
| base_40_90 | 4.610 | 0.188/4.422 | 1.6% | 0.3% | 30.8% | 5.54/12.46 | 1.29/7.58 |
| skills_50 | 2.248 | 1.112/1.136 | 27.4% | 35.7% | 50.0% | 9.00/9.00 | 3.53/3.55 |
| skill_passing_70 | 2.445 | 1.405/1.040 | 25.0% | 46.5% | 54.5% | 9.81/8.19 | 4.10/3.23 |
| skill_playmaking_70 | 2.482 | 1.441/1.041 | 25.2% | 47.1% | 54.5% | 9.80/8.20 | 4.20/3.24 |
| skill_finishing_70 | 2.466 | 1.325/1.142 | 26.2% | 41.2% | 50.0% | 9.00/9.00 | 3.53/3.55 |
| skill_tackling_70 | 2.058 | 1.120/0.938 | 28.9% | 40.4% | 49.9% | 8.98/9.02 | 3.54/3.17 |
| skill_goalkeeping_70 | 2.100 | 1.112/0.988 | 28.8% | 38.7% | 50.0% | 9.00/9.00 | 3.53/3.55 |
| skill_speed_70 | 2.085 | 1.147/0.939 | 28.8% | 41.1% | 49.8% | 8.97/9.03 | 3.62/3.18 |
| fit_correct | 2.384 | 1.179/1.205 | 26.4% | 36.3% | 50.0% | 8.99/9.01 | 3.53/3.56 |
| fit_compatible | 2.353 | 0.949/1.404 | 26.2% | 26.0% | 47.4% | 8.52/9.48 | 3.13/3.97 |
| fit_wrong | 2.475 | 0.579/1.896 | 19.3% | 10.6% | 41.8% | 7.52/10.48 | 2.39/4.98 |
| side_correct | 2.384 | 1.179/1.205 | 26.4% | 36.3% | 50.0% | 8.99/9.01 | 3.53/3.56 |
| side_opposite | 2.371 | 1.139/1.232 | 26.9% | 34.4% | 49.6% | 8.92/9.08 | 3.46/3.61 |
| side_both | 2.384 | 1.179/1.205 | 26.4% | 36.3% | 50.0% | 8.99/9.01 | 3.53/3.56 |
| energy_100 | 2.384 | 1.179/1.205 | 26.4% | 36.3% | 50.0% | 8.99/9.01 | 3.53/3.56 |
| energy_80 | 2.386 | 1.030/1.356 | 26.1% | 28.9% | 48.4% | 8.70/9.30 | 3.28/3.82 |
| energy_60 | 2.427 | 0.893/1.534 | 24.8% | 22.6% | 46.6% | 8.39/9.61 | 3.02/4.09 |
| energy_40 | 2.495 | 0.760/1.736 | 22.7% | 16.2% | 44.7% | 8.05/9.95 | 2.76/4.40 |
| morale_0 | 2.373 | 1.080/1.293 | 26.3% | 31.5% | 48.9% | 8.81/9.19 | 3.37/3.72 |
| morale_50 | 2.384 | 1.179/1.205 | 26.4% | 36.3% | 50.0% | 8.99/9.01 | 3.53/3.56 |
| morale_100 | 2.403 | 1.281/1.122 | 26.3% | 41.0% | 50.9% | 9.16/8.84 | 3.68/3.41 |
| formation_4-4-2 | 2.384 | 1.179/1.205 | 26.4% | 36.3% | 50.0% | 8.99/9.01 | 3.53/3.56 |
| formation_4-3-3 | 2.430 | 1.186/1.244 | 26.4% | 35.4% | 49.5% | 8.91/9.09 | 3.48/3.64 |
| formation_5-3-2 | 2.284 | 1.117/1.166 | 26.8% | 35.3% | 49.5% | 8.91/9.09 | 3.41/3.50 |
| formation_3-5-2 | 2.481 | 1.236/1.244 | 25.8% | 37.0% | 50.4% | 9.07/8.93 | 3.65/3.62 |
| style_balanced_balanced | 2.384 | 1.179/1.205 | 26.4% | 36.3% | 50.0% | 8.99/9.01 | 3.53/3.56 |
| style_all_out_attack_balanced | 2.698 | 1.280/1.419 | 24.7% | 34.1% | 49.9% | 8.98/9.02 | 3.79/3.90 |
| style_counter_attack_balanced | 2.383 | 1.087/1.296 | 26.5% | 31.6% | 46.2% | 8.32/9.68 | 3.26/3.82 |
| style_counter_attack_all_out_attack | 2.976 | 1.588/1.387 | 23.7% | 42.6% | 46.1% | 8.30/9.70 | 4.39/4.10 |
| marking_light | 2.384 | 1.179/1.205 | 26.4% | 36.3% | 50.0% | 8.99/9.01 | 3.53/3.56 |
| marking_heavy | 2.192 | 1.131/1.061 | 28.4% | 37.6% | 49.9% | 8.63/8.39 | 3.36/3.13 |
| marking_very_heavy | 1.843 | 1.018/0.825 | 31.8% | 39.1% | 49.8% | 7.87/7.23 | 3.01/2.50 |
| focus_normal | 2.384 | 1.179/1.205 | 26.4% | 36.3% | 50.0% | 8.99/9.01 | 3.53/3.56 |
| focus_center | 2.389 | 1.189/1.200 | 27.7% | 36.0% | 49.8% | 8.96/9.04 | 3.50/3.56 |
| focus_wings | 2.388 | 1.191/1.197 | 27.1% | 36.2% | 49.9% | 8.98/9.02 | 3.53/3.51 |
| tactic_balanced_light__balanced_heavy | 2.170 | 1.032/1.138 | 28.1% | 33.1% | 50.0% | 8.37/8.63 | 3.11/3.37 |
| tactic_balanced_light__balanced_very_heavy | 1.851 | 0.819/1.033 | 30.7% | 29.1% | 50.0% | 7.21/7.92 | 2.50/3.03 |
| tactic_balanced_light__all_out_attack_light | 2.682 | 1.390/1.292 | 24.0% | 40.4% | 49.8% | 8.96/9.04 | 3.87/3.82 |
| tactic_balanced_light__all_out_attack_heavy | 2.442 | 1.213/1.229 | 26.9% | 36.2% | 49.9% | 8.35/8.66 | 3.44/3.64 |
| tactic_balanced_light__all_out_attack_very_heavy | 2.076 | 0.957/1.119 | 28.8% | 31.4% | 50.0% | 7.21/7.91 | 2.76/3.28 |
| tactic_balanced_light__counter_attack_light | 2.384 | 1.266/1.118 | 26.5% | 40.6% | 53.7% | 9.66/8.34 | 3.79/3.29 |
| tactic_balanced_light__counter_attack_heavy | 2.171 | 1.106/1.065 | 28.4% | 36.8% | 53.7% | 8.98/8.01 | 3.34/3.14 |
| tactic_balanced_light__counter_attack_very_heavy | 1.832 | 0.877/0.955 | 31.1% | 32.4% | 53.6% | 7.73/7.34 | 2.67/2.81 |
| tactic_balanced_heavy__balanced_very_heavy | 1.679 | 0.774/0.905 | 32.6% | 30.0% | 49.9% | 6.88/7.38 | 2.37/2.68 |
| tactic_balanced_heavy__all_out_attack_light | 2.467 | 1.336/1.131 | 26.3% | 41.9% | 49.9% | 8.63/8.39 | 3.70/3.38 |
| tactic_balanced_heavy__all_out_attack_heavy | 2.241 | 1.164/1.078 | 28.4% | 38.1% | 49.9% | 8.01/8.06 | 3.28/3.23 |
| tactic_balanced_heavy__all_out_attack_very_heavy | 1.887 | 0.911/0.977 | 30.5% | 33.0% | 50.0% | 6.90/7.38 | 2.63/2.89 |
| tactic_balanced_heavy__counter_attack_light | 2.236 | 1.214/1.023 | 27.4% | 41.4% | 53.8% | 9.29/8.13 | 3.61/3.03 |
| tactic_balanced_heavy__counter_attack_heavy | 2.038 | 1.067/0.971 | 29.6% | 37.9% | 53.7% | 8.62/7.81 | 3.19/2.89 |
| tactic_balanced_heavy__counter_attack_very_heavy | 1.713 | 0.833/0.880 | 32.8% | 32.4% | 53.5% | 7.39/7.17 | 2.54/2.61 |
| tactic_balanced_very_heavy__all_out_attack_light | 2.090 | 1.199/0.891 | 28.9% | 43.5% | 49.8% | 7.88/7.23 | 3.32/2.71 |
| tactic_balanced_very_heavy__all_out_attack_heavy | 1.881 | 1.042/0.839 | 30.5% | 40.3% | 49.7% | 7.32/6.97 | 2.93/2.59 |
| tactic_balanced_very_heavy__all_out_attack_very_heavy | 1.585 | 0.823/0.761 | 33.6% | 35.2% | 49.8% | 6.31/6.37 | 2.36/2.34 |
| tactic_balanced_very_heavy__counter_attack_light | 1.986 | 1.102/0.884 | 31.2% | 40.1% | 53.6% | 8.49/7.76 | 3.24/2.69 |
| tactic_balanced_very_heavy__counter_attack_heavy | 1.788 | 0.942/0.846 | 33.1% | 36.2% | 53.4% | 7.87/7.49 | 2.85/2.59 |
| tactic_balanced_very_heavy__counter_attack_very_heavy | 1.511 | 0.750/0.761 | 35.6% | 31.9% | 53.5% | 6.78/6.84 | 2.29/2.34 |
| tactic_all_out_attack_light__all_out_attack_heavy | 2.763 | 1.313/1.450 | 24.1% | 34.9% | 50.0% | 8.37/8.64 | 3.71/4.01 |
| tactic_all_out_attack_light__all_out_attack_very_heavy | 2.344 | 1.036/1.308 | 26.3% | 29.8% | 50.0% | 7.20/7.92 | 2.97/3.62 |
| tactic_all_out_attack_light__counter_attack_light | 2.977 | 1.369/1.608 | 23.8% | 33.1% | 53.6% | 9.64/8.36 | 4.08/4.44 |
| tactic_all_out_attack_light__counter_attack_heavy | 2.732 | 1.208/1.524 | 23.8% | 30.8% | 53.5% | 8.96/8.04 | 3.60/4.25 |
| tactic_all_out_attack_light__counter_attack_very_heavy | 2.329 | 0.945/1.384 | 26.4% | 26.3% | 53.5% | 7.72/7.35 | 2.88/3.85 |
| tactic_all_out_attack_heavy__all_out_attack_very_heavy | 2.127 | 0.988/1.139 | 27.7% | 32.5% | 49.9% | 6.91/7.38 | 2.84/3.19 |
| tactic_all_out_attack_heavy__counter_attack_light | 2.789 | 1.313/1.476 | 24.9% | 34.1% | 53.6% | 9.28/8.15 | 3.89/4.12 |
| tactic_all_out_attack_heavy__counter_attack_heavy | 2.548 | 1.146/1.403 | 25.7% | 31.5% | 53.6% | 8.64/7.82 | 3.44/3.96 |
| tactic_all_out_attack_heavy__counter_attack_very_heavy | 2.174 | 0.908/1.266 | 27.2% | 27.6% | 53.4% | 7.39/7.18 | 2.74/3.57 |
| tactic_all_out_attack_very_heavy__counter_attack_light | 2.460 | 1.182/1.278 | 26.9% | 34.2% | 53.5% | 8.47/7.77 | 3.49/3.70 |
| tactic_all_out_attack_very_heavy__counter_attack_heavy | 2.219 | 1.020/1.199 | 28.4% | 31.4% | 53.6% | 7.90/7.47 | 3.07/3.53 |
| tactic_all_out_attack_very_heavy__counter_attack_very_heavy | 1.904 | 0.809/1.095 | 29.2% | 28.0% | 53.5% | 6.78/6.85 | 2.46/3.19 |
| tactic_counter_attack_light__counter_attack_heavy | 2.218 | 1.075/1.143 | 27.4% | 34.5% | 50.0% | 8.78/8.63 | 3.26/3.37 |
| tactic_counter_attack_light__counter_attack_very_heavy | 1.978 | 0.949/1.028 | 30.1% | 32.8% | 49.9% | 8.36/7.93 | 2.89/3.05 |
| tactic_counter_attack_heavy__counter_attack_very_heavy | 1.855 | 0.909/0.946 | 31.2% | 33.1% | 49.9% | 8.02/7.74 | 2.76/2.82 |
| quality_40_balanced_light_90 | 4.610 | 0.188/4.422 | 1.6% | 0.3% | 30.8% | 5.54/12.46 | 1.29/7.58 |
| quality_40_balanced_heavy_90 | 4.226 | 0.175/4.051 | 2.0% | 0.4% | 30.8% | 5.33/12.02 | 1.23/7.00 |
| quality_40_balanced_very_heavy_90 | 3.679 | 0.160/3.519 | 3.5% | 0.5% | 30.7% | 4.86/11.24 | 1.12/6.20 |
| quality_40_all_out_attack_light_90 | 5.100 | 0.206/4.894 | 1.0% | 0.2% | 30.7% | 5.52/12.48 | 1.42/8.14 |
| quality_40_all_out_attack_heavy_90 | 4.700 | 0.197/4.503 | 1.3% | 0.2% | 30.8% | 5.34/12.01 | 1.36/7.53 |
| quality_40_all_out_attack_very_heavy_90 | 4.136 | 0.174/3.961 | 2.3% | 0.3% | 30.8% | 4.87/11.23 | 1.23/6.69 |
| quality_40_counter_attack_light_90 | 4.794 | 0.170/4.624 | 1.4% | 0.2% | 27.7% | 4.98/13.02 | 1.16/7.92 |
| quality_40_counter_attack_heavy_90 | 4.395 | 0.159/4.236 | 1.8% | 0.2% | 27.7% | 4.80/12.55 | 1.11/7.31 |
| quality_40_counter_attack_very_heavy_90 | 3.824 | 0.145/3.679 | 2.8% | 0.4% | 27.6% | 4.38/11.73 | 1.00/6.47 |

## Finalizações, faltas, cartões e setores

Valores médios por partida para a equipe A; dados das duas equipes no JSON.

| Cenário | Finalizações | Faltas | Amarelos | Vermelhos | Centro | Alas | Chances/ataque |
|---|---:|---:|---:|---:|---:|---:|---:|
| base_70_70 | 3.56 | 0.285 | 0.050 | 0.008 | 33.4% | 66.6% | 39.3% |
| base_75_70 | 3.83 | 0.273 | 0.048 | 0.008 | 33.4% | 66.6% | 41.0% |
| base_80_60 | 4.79 | 0.243 | 0.042 | 0.007 | 33.5% | 66.5% | 46.3% |
| base_60_80 | 2.53 | 0.322 | 0.055 | 0.009 | 33.5% | 66.5% | 32.5% |
| base_90_40 | 7.60 | 0.171 | 0.029 | 0.004 | 33.4% | 66.6% | 60.6% |
| base_40_90 | 1.31 | 0.384 | 0.074 | 0.010 | 33.8% | 66.2% | 23.3% |
| skills_50 | 3.56 | 0.281 | 0.050 | 0.008 | 33.4% | 66.6% | 39.2% |
| skill_passing_70 | 4.13 | 0.255 | 0.045 | 0.008 | 33.3% | 66.7% | 41.8% |
| skill_playmaking_70 | 4.23 | 0.259 | 0.045 | 0.008 | 33.3% | 66.7% | 42.8% |
| skill_finishing_70 | 3.56 | 0.283 | 0.050 | 0.008 | 33.4% | 66.6% | 39.2% |
| skill_tackling_70 | 3.56 | 0.282 | 0.049 | 0.008 | 33.6% | 66.4% | 39.4% |
| skill_goalkeeping_70 | 3.56 | 0.281 | 0.050 | 0.008 | 33.4% | 66.6% | 39.2% |
| skill_speed_70 | 3.65 | 0.282 | 0.049 | 0.009 | 33.6% | 66.4% | 40.4% |
| fit_correct | 3.56 | 0.285 | 0.050 | 0.008 | 33.4% | 66.6% | 39.3% |
| fit_compatible | 3.16 | 0.293 | 0.054 | 0.007 | 33.3% | 66.7% | 36.7% |
| fit_wrong | 2.41 | 0.322 | 0.056 | 0.009 | 33.5% | 66.5% | 31.7% |
| side_correct | 3.56 | 0.285 | 0.050 | 0.008 | 33.4% | 66.6% | 39.3% |
| side_opposite | 3.49 | 0.286 | 0.051 | 0.008 | 33.4% | 66.6% | 38.8% |
| side_both | 3.56 | 0.285 | 0.050 | 0.008 | 33.4% | 66.6% | 39.3% |
| energy_100 | 3.56 | 0.285 | 0.050 | 0.008 | 33.4% | 66.6% | 39.3% |
| energy_80 | 3.30 | 0.284 | 0.052 | 0.007 | 33.4% | 66.6% | 37.7% |
| energy_60 | 3.04 | 0.297 | 0.054 | 0.008 | 33.4% | 66.6% | 36.0% |
| energy_40 | 2.78 | 0.306 | 0.055 | 0.008 | 33.4% | 66.6% | 34.3% |
| morale_0 | 3.40 | 0.283 | 0.051 | 0.007 | 33.4% | 66.6% | 38.3% |
| morale_50 | 3.56 | 0.285 | 0.050 | 0.008 | 33.4% | 66.6% | 39.3% |
| morale_100 | 3.71 | 0.277 | 0.048 | 0.008 | 33.4% | 66.6% | 40.2% |
| formation_4-4-2 | 3.56 | 0.285 | 0.050 | 0.008 | 33.4% | 66.6% | 39.3% |
| formation_4-3-3 | 3.51 | 0.285 | 0.051 | 0.007 | 33.5% | 66.5% | 39.1% |
| formation_5-3-2 | 3.44 | 0.284 | 0.049 | 0.008 | 33.4% | 66.6% | 38.3% |
| formation_3-5-2 | 3.68 | 0.276 | 0.049 | 0.008 | 33.4% | 66.6% | 40.2% |
| style_balanced_balanced | 3.56 | 0.285 | 0.050 | 0.008 | 33.4% | 66.6% | 39.3% |
| style_all_out_attack_balanced | 3.82 | 0.281 | 0.053 | 0.008 | 33.5% | 66.5% | 42.2% |
| style_counter_attack_balanced | 3.29 | 0.304 | 0.053 | 0.008 | 33.4% | 66.6% | 39.2% |
| style_counter_attack_all_out_attack | 4.42 | 0.295 | 0.054 | 0.007 | 33.2% | 66.8% | 52.9% |
| marking_light | 3.56 | 0.285 | 0.050 | 0.008 | 33.4% | 66.6% | 39.3% |
| marking_heavy | 3.39 | 0.604 | 0.160 | 0.033 | 33.4% | 66.6% | 38.9% |
| marking_very_heavy | 3.03 | 0.877 | 0.318 | 0.071 | 33.6% | 66.4% | 38.2% |
| focus_normal | 3.56 | 0.285 | 0.050 | 0.008 | 33.4% | 66.6% | 39.3% |
| focus_center | 3.53 | 0.282 | 0.054 | 0.007 | 70.0% | 30.0% | 39.0% |
| focus_wings | 3.56 | 0.277 | 0.049 | 0.008 | 30.1% | 69.9% | 39.4% |

## Habilidades e fases

A/B são as equipes definidas em cada cenário, com mando alternado. Construção, progressão e criação são taxas condicionais de sucesso da fase; conversão inclui pênaltis.

| Cenário | Construção A/B | Progressão A/B | Criação A/B | Conversão A/B |
|---|---:|---:|---:|---:|
| skills_50 | 80.3%/80.5% | 75.3%/75.2% | 65.1%/65.4% | 31.2%/31.7% |
| skill_passing_70 | 82.2%/80.4% | 75.3%/75.2% | 67.8%/65.5% | 34.0%/31.9% |
| skill_playmaking_70 | 82.1%/80.4% | 77.1%/75.2% | 67.9%/65.5% | 34.1%/31.9% |
| skill_finishing_70 | 80.3%/80.4% | 75.3%/75.2% | 65.0%/65.5% | 37.3%/31.9% |
| skill_tackling_70 | 80.5%/77.8% | 75.3%/72.4% | 65.2%/62.7% | 31.4%/29.3% |
| skill_goalkeeping_70 | 80.3%/80.5% | 75.3%/75.2% | 65.1%/65.4% | 31.2%/27.6% |
| skill_speed_70 | 80.4%/77.8% | 77.1%/72.5% | 65.4%/62.7% | 31.4%/29.3% |

## Critérios de aceitação

- PASS — sample_size: `10000`
- PASS — equal_goals: `2.3841`
- PASS — equal_draws: `0.2639`
- PASS — small_home_advantage: `0.006900000000000017`
- PASS — base_75_70_quality: `0.1493`
- PASS — base_80_60_quality: `0.5926`
- PASS — base_90_40_quality: `0.9824999999999999`
- PASS — base_60_80_quality: `0.5878`
- PASS — base_40_90_quality: `0.9791`
- PASS — attribute_passing: `{"metric": "build_success_rate", "baseline": 0.8033080864335042, "changed": 0.8216202951010767}`
- PASS — attribute_passing_bounded: `0.4647`
- PASS — attribute_playmaking: `{"metric": "create_success_rate", "baseline": 0.6505531726892845, "changed": 0.6787862131401965}`
- PASS — attribute_playmaking_bounded: `0.471`
- PASS — attribute_finishing: `{"metric": "shot_conversion", "baseline": 0.3122876000561719, "changed": 0.37254626244445693}`
- PASS — attribute_finishing_bounded: `0.4121`
- PASS — attribute_tackling: `{"metric": "chances", "baseline": 3.5529, "changed": 3.1737}`
- PASS — attribute_tackling_bounded: `0.4041`
- PASS — attribute_goalkeeping: `{"metric": "shot_conversion", "baseline": 0.3171535496844104, "changed": 0.275959336424063}`
- PASS — attribute_goalkeeping_bounded: `0.3868`
- PASS — attribute_speed: `{"metric": "progress_success_rate", "baseline": 0.753220282580663, "changed": 0.7708263819374931}`
- PASS — attribute_speed_bounded: `0.4109`
- PASS — attribute_goalkeeping_phase_local: `0.0`
- PASS — attribute_finishing_phase_local: `0.0003166666666662432`
- PASS — position_penalties: `[1.1793, 0.9493, 0.5786]`
- PASS — side_penalty_smaller: `0.04049999999999998`
- PASS — both_equals_correct: `1.1793`
- PASS — gradual_energy: `[1.1793, 1.0305, 0.8926, 0.7597]`
- PASS — small_morale_effect: `[0.3152, 0.3627, 0.4097]`
- PASS — formation_4-4-2_bounded: `0.3627`
- PASS — formation_4-3-3_bounded: `0.3541`
- PASS — formation_5-3-2_bounded: `0.3529`
- PASS — formation_3-5-2_bounded: `0.3699`
- PASS — all_out_more_chances_both: `[3.7907, 3.8973]`
- PASS — counter_lower_volume: `0.4621444444444351`
- PASS — counter_transition_efficiency: `[0.3920371216310437, 0.5288840183528222]`
- PASS — marking_attack_reduction: `0.19693790316313042`
- PASS — marking_cost: `[0.803386200896741, 0.7851118585333537]`
- PASS — marking_more_fouls_cards: `0.8771`
- PASS — focus_center_70_percent: `0.7003792526491913`
- PASS — focus_wings_70_percent: `0.6994343236381454`
- PASS — no_dominant_tactic: `{"balanced/light": 3, "balanced/heavy": 5, "balanced/very_heavy": 7, "all_out_attack/light": 0, "all_out_attack/heavy": 1, "all_out_attack/very_heavy": 4, "counter_attack/light": 3, "counter_attack/heavy": 4, "counter_attack/very_heavy": 7}`
- PASS — quality_40_balanced_light_90_squad_dominates: `0.9791`
- PASS — quality_40_balanced_heavy_90_squad_dominates: `0.9724999999999999`
- PASS — quality_40_balanced_very_heavy_90_squad_dominates: `0.9553`
- PASS — quality_40_all_out_attack_light_90_squad_dominates: `0.9861`
- PASS — quality_40_all_out_attack_heavy_90_squad_dominates: `0.9821000000000001`
- PASS — quality_40_all_out_attack_very_heavy_90_squad_dominates: `0.9703`
- PASS — quality_40_counter_attack_light_90_squad_dominates: `0.9829`
- PASS — quality_40_counter_attack_heavy_90_squad_dominates: `0.9775`
- PASS — quality_40_counter_attack_very_heavy_90_squad_dominates: `0.9643999999999999`

## Limites da medição

As matrizes cobrem três estilos × três marcações, com forças, formação e foco controlados. Dominância significa superar cada alternativa por mais de 2 pontos percentuais na diferença entre vitórias e derrotas; não é uma prova sobre todas as escalações possíveis. A amostragem usa os mesmos seeds por cenário; variações pequenas ainda têm incerteza estatística. Moral limita a força efetiva a ±4%; a variação de vitórias não é esse multiplicador.
