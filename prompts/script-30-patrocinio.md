# Script 30 — Sistema de Patrocínio

Objetivo: evoluir o patrocínio fixo para um sistema de propostas.

## 1. Base

Manter valor inicial de referência:

R$ 5.000 por mês

## 2. Oferta

SponsorOffer:

club_id
sponsor_name
monthly_value
duration_months
bonus
status
created_at

## 3. Fatores

Valor deve considerar:

- divisão
- reputação
- torcida
- desempenho recente

## 4. Contrato

Um patrocinador principal por clube.

## 5. Faixa

Evitar diferenças exageradas.

Clube forte recebe mais, mas não múltiplos absurdos.

## 6. Bots

Bots escolhem melhor proposta considerando:

- valor
- duração
- risco

## 7. Histórico

sponsor_contracts

## 8. Testes

Validar:

- proposta
- aceite
- expiração
- novo contrato
- diferença por reputação/divisão
