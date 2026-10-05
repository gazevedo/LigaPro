# Script 23 — Lesões e Condição Física

Objetivo: adicionar desgaste, recuperação e lesões sem tornar o jogo excessivamente punitivo.

## 1. Condição física

Adicionar ao jogador:

physical_condition: 0..100

Valor inicial recomendado:
100

A condição física deve cair após partidas e se recuperar entre jogos.

## 2. Desgaste por partida

O desgaste deve considerar:

- minutos jogados
- idade
- energia
- intensidade da partida
- marcação muito pesada
- estilo ataque total
- prorrogação futuramente

Não criar desgaste aleatório puro.

## 3. Efeito no desempenho

A condição física deve afetar levemente o rendimento.

Sugestão:

85-100:
1.00

70-84:
0.98

55-69:
0.95

40-54:
0.90

abaixo de 40:
0.84

Usar configuração central.

## 4. Recuperação

Criar:

PhysicalConditionService

A recuperação deve depender de:

- tempo entre partidas
- idade
- condição atual
- nível do departamento médico/estrutura
- descanso

## 5. Lesões

Criar:

InjuryService

A chance de lesão deve considerar:

- condição física baixa
- idade
- disputa forte
- falta perigosa
- marcação muito pesada
- sequência de partidas

## 6. Tipos de lesão

Categorias:

minor
moderate
serious

Exemplo de duração:

minor:
1 a 2 partidas

moderate:
3 a 6 partidas

serious:
7+ partidas

Usar dias/partidas lógicas, não tempo real absoluto.

## 7. Collection player_injuries

Campos:

player_id
club_id
injury_type
severity
started_at
expected_return_at
recovered_at
status
created_at

## 8. Status do jogador

status:

available
injured
suspended
retired

Jogador lesionado:

- não pode ser titular
- não pode ir para o banco
- não pode treinar normalmente

## 9. Lesão durante partida

Evento:

injury

Se a lesão impedir continuidade:

- remover jogador
- permitir substituição
- se não houver substituição disponível, time segue com menos um

## 10. Bots

Bots devem substituir automaticamente jogador lesionado.

## 11. Tela

Mostrar:

- condição física
- status
- lesão
- previsão de retorno

## 12. Testes

Validar:

- desgaste proporcional a minutos
- recuperação
- lesão por baixa condição
- indisponibilidade
- retorno
- substituição automática de bot

## 13. Calibração

Meta inicial:

lesões devem ser relevantes, mas não frequentes a ponto de destruir o elenco.

Rodar 10.000 partidas e medir:

- lesões por jogo
- duração média
- distribuição por idade
- correlação com condição física
