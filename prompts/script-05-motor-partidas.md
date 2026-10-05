# Script 5 — Motor de Partidas Revisado (mais próximo do Brasfoot)

Objetivo: substituir o modelo excessivamente agregado por um motor baseado em contribuição individual, posição, energia, moral, formação, estilo, marcação e foco dos ataques.

## 1. Princípio

Não decidir jogadas apenas com:

attack_strength vs defense_strength.

O fluxo deve usar jogadores e setores.

Fluxo:

ESCALAÇÃO
→ posição correta / improvisação
→ lado preferido
→ energia
→ moral
→ força/habilidades
→ características inatas
→ formação
→ estilo
→ marcação
→ foco dos ataques
→ construção
→ disputa
→ finalização
→ goleiro
→ evento

## 2. Modos de atributo

O motor deve suportar:

### Modo clássico
Usar `strength` como atributo geral.

### Modo habilidades individuais
Usar:
- goalkeeping
- speed
- technique
- passing
- tackling
- playmaking
- finishing

## 3. Posições

Usar:

GK
FB
CB
MID
ATT

## 4. Improvisação

Criar:

PositionFitCalculator

Regras:

posição correta:
1.00

posição compatível:
penalidade leve

posição inadequada:
penalidade maior

Não usar valores finais fixos sem calibração.

## 5. Lado preferido

Para jogadores de lado:

preferred_side:
left
right
both

Jogar no lado errado deve gerar penalidade menor que jogar fora da posição.

## 6. Energia

energy:
0 a 100

A energia afeta a força efetiva.

Exemplo de função suave:

effective_energy_factor = clamp(0.70, 1.00, 0.70 + energy/333)

Não usar degraus bruscos.

## 7. Moral

Moral deve ter efeito pequeno.

Sugestão:

muito baixa:
0.96

normal:
1.00

muito alta:
1.04

Limitar aproximadamente a ±4%.

## 8. Características inatas

Aplicar apenas em situações relacionadas.

Exemplos:

speed:
ajuda em transição e duelo contra marcação

passing:
melhora construção

playmaking:
melhora criação

finishing:
melhora finalização

marking/tackling:
melhora contenção

goalkeeping/reflexes/positioning:
melhora defesa do goleiro

Não adicionar bônus global.

## 9. Formação

Formação organiza quantidade de jogadores por setor.

Ela não deve gerar grande multiplicador arbitrário.

Exemplo:

4-3-3:
mais presença ofensiva

5-3-2:
mais presença defensiva

3-5-2:
mais presença no meio

A força do setor deve vir principalmente dos jogadores realmente escalados.

## 10. Construção de jogada

Criar fases:

1. saída/construção
2. progressão
3. criação
4. finalização

### Construção

Considerar:

passing
technique
playmaking
energy
morale
opponent marking
position fit

### Progressão

Considerar:

speed
technique
playmaking
opponent tackling
opponent marking

### Criação

Considerar:

playmaking
passing
attack focus
formation presence

### Finalização

Considerar:

finishing
strength clássico se modo clássico
chance quality
goalkeeper

## 11. Foco dos ataques

Usar:

normal
center
wings

Quando center ou wings estiver ativo:

aproximadamente 70% dos ataques devem tender ao setor escolhido.

Não obrigar exatamente 70% em cada partida; usar como probabilidade-alvo.

## 12. Estilos

Usar somente:

balanced
all_out_attack
counter_attack

### balanced
sem grande modificador.

### all_out_attack
- mais participação ofensiva
- maior exposição defensiva

### counter_attack
- menor posse
- menos ataques posicionais
- maior efetividade em transições contra adversário exposto

## 13. Marcação

Usar:

light
heavy
very_heavy

### light
- menos faltas/cartões
- menos contenção

### heavy
- maior contenção
- mais faltas

### very_heavy
- pode reduzir significativamente ataques adversários
- alvo de calibração: até ~20% em cenários adequados
- também prejudica saída/construção própria
- aumenta faltas/cartões/expulsões

## 14. Mando

Manter vantagem pequena de mando.

Não permitir que mando seja mais importante que diferença real de elenco.

## 15. Blocos

Continuar usando blocos de tempo, por exemplo 5 minutos.

Cada bloco:

1. escolher equipe com iniciativa
2. escolher foco do ataque
3. selecionar jogadores participantes
4. resolver construção
5. resolver disputa
6. gerar chance ou perda
7. resolver finalização
8. registrar evento

## 16. Eventos

Manter:

attack
chance
shot_saved
shot_off_target
goal
foul
yellow_card
red_card
penalty_awarded

## 17. Seed

Mesma seed + mesmos inputs + mesma config = mesmo resultado.

## 18. Snapshot

Salvar:

lineup
formation
style
marking
attack_focus
energy
morale
player strengths/skills relevantes

## 19. Serviços

Criar/ajustar:

MatchEngine
PlayerEffectiveStrengthCalculator
PositionFitCalculator
SectorContributionCalculator
BuildUpResolver
ProgressionResolver
ChanceCreator
FinishingResolver
GoalkeeperResolver

## 20. Regra de fidelidade

Evitar:
- multiplicadores táticos grandes e genéricos
- atributos inventados
- força de equipe única decidindo tudo

Priorizar:
- jogadores
- posições
- habilidades
- energia
- moral
- formação
- estilo
- marcação
- foco
