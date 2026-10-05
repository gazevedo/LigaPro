# Script 7 — Sistema Tático Revisado (mais fiel ao Brasfoot)

Objetivo: simplificar o sistema tático e manter apenas opções fortemente documentadas no Brasfoot.

## 1. Remover

Remover como escolhas principais:

- tempo
- pressing
- defensive_line

Essas opções não fazem parte do núcleo clássico documentado que queremos reproduzir.

## 2. Manter

A tática do clube deve possuir:

formation
play_style
marking
attack_focus

## 3. Collection club_tactics

{
  "club_id": "...",
  "formation": "4-4-2",
  "play_style": "balanced",
  "marking": "heavy",
  "attack_focus": "normal",
  "updated_at": "datetime"
}

## 4. Estilo de jogo

Valores:

balanced
all_out_attack
counter_attack

### Balanced

Equilíbrio entre defesa e ataque.

### All Out Attack

Aumenta:
- presença ofensiva
- criação

Reduz:
- proteção defensiva

Não usar bônus global alto.

### Counter Attack

Reduz:
- posse
- ataque posicional

Aumenta:
- eficiência de transições contra adversário exposto

## 5. Marcação

Valores:

light
heavy
very_heavy

### Light
menos faltas e cartões
menor contenção

### Heavy
mais contenção
mais faltas

### Very Heavy
forte contenção
pode reduzir ataques adversários significativamente
aumenta faltas/cartões
também dificulta a própria saída de bola

## 6. Foco dos ataques

Valores:

normal
center
wings

Normal:
distribuição natural.

Center:
aproximadamente 70% dos ataques tendem ao centro.

Wings:
aproximadamente 70% tendem às laterais.

O efeito deve ser probabilístico.

## 7. Formação

Manter formações já existentes:

4-4-2
4-3-3
4-2-3-1
3-5-2
5-3-2
4-5-1
3-4-3

A formação organiza presença setorial.

## 8. Interação com jogadores

Tática deve atuar sobre jogadores reais.

Exemplos:

attack_focus=center:
selecionar com maior frequência MID/ATT centrais

attack_focus=wings:
favorecer FB e jogadores adequados ao lado

all_out_attack:
aumentar participação ofensiva de MID/FB

counter_attack:
favorecer speed + passing + finishing em transições

## 9. Tela

TacticsScreen:

Formação
Estilo
Marcação
Foco dos ataques

Descrições simples.

## 10. Bots

Presets:

balanced
aggressive
counter
defensive_heavy_marking

Bots escolhem conforme:
- placar
- força relativa
- perfil do elenco

## 11. Testes

Matriz de estilos e marcações.

Nenhuma combinação deve dominar todas.
