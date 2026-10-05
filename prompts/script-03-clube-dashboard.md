# Script 3 — Criação do Clube e Dashboard Principal

Objetivo: após login, o usuário cria seu primeiro clube e passa a gerenciá-lo pelo dashboard.

## Criação do clube
Fluxo:
Login -> verificar se possui clube -> se não, CreateClubScreen -> se sim, DashboardScreen.

Campos:
- nome
- país
- escudo

Endpoint inicial: GET /api/game/status e POST /api/clubs.

Collections principais:
- countries
- club_badges
- clubs

Ao criar clube, gerar:
- estádio inicial
- plantel inicial
- dados financeiros iniciais
- lineup inicial

## Dashboard
Módulos:
- Clube
- Plantel
- Estádio
- Financeiro
- Calendário
- Mercado

## Clube
Tela pública para qualquer usuário autenticado consultar qualquer clube.
Mostrar:
- escudo
- nome
- país
- data de criação
- ranking
- posição atual nos campeonatos
- sala de troféus

Outros usuários não veem controles administrativos nem dados financeiros privados.

## Plantel
SquadScreen.
Escolher formação e definir titulares/reservas.
Formações iniciais configuráveis: 4-4-2, 4-3-3, 4-2-3-1, 3-5-2, 5-3-2, 4-5-1, 3-4-3.
Validar 11 titulares, 1 goleiro, sem duplicidade e jogadores pertencentes ao clube.

## Estádio
StadiumScreen.
Construções evolutivas:
Arquibancadas, Gramado, Iluminação, Vestiários, Centro Médico, Centro de Treinamento, Estacionamento, Lojas, Camarotes.
Upgrade cobra saldo e gera transação financeira.

## Financeiro
FinanceScreen com abas:
- Resumo
- Banco
- Bilheteria
- Patrocinadores

financial_transactions deve registrar todas as receitas/despesas.
Saldo é controlado somente no backend.

Banco:
- investimentos
- empréstimos

Bilheteria:
- preço do ingresso
- capacidade
- histórico de público
- renda

Patrocinadores:
- ofertas disponíveis
- requisitos
- duração
- valor
- um patrocinador principal ativo inicialmente

## Calendário
CalendarScreen.
Mostrar programação por lista/mês e permitir filtros por período/tipo.
Tipos previstos: match, training, competition, transfer, financial, stadium, other.
Não gerar partidas fictícias enquanto o módulo de partidas não estiver implementado.

## Mercado
MarketScreen com abas:
- Buscar
- À venda
- Empréstimos
- Minhas negociações
- Minhas ofertas

Permitir compra, venda e empréstimo de jogadores.
Collections:
- transfer_listings
- transfer_offers
- player_loans
- transfer_history

Diferenciar no player:
owner_club_id
current_club_id

Em empréstimo, o dono contratual permanece em owner_club_id e o clube atual em current_club_id.

Aceite de proposta de compra deve, atomicamente:
- validar saldo
- debitar comprador
- creditar vendedor
- transferir jogador
- gerar histórico
- encerrar listing
- encerrar ofertas conflitantes

Pesquisa no mercado deve aceitar filtros por nome, posição, idade, overall, valor, país e tipo de anúncio.

## Permissões
Somente o proprietário pode administrar escalação, estádio, ingresso, patrocínio, investimento, empréstimos e mercado do próprio clube.

## Frontend
Telas principais:
CreateClubScreen
DashboardScreen
ClubScreen
SquadScreen
StadiumScreen
FinanceScreen
BankScreen
TicketingScreen
SponsorsScreen
CalendarScreen
MarketScreen
PlayerDetailsScreen
TransferOffersScreen

Serviços separados e stores por domínio.

## Validação
Testar criação de clube, dados iniciais, dashboard, consulta pública, escalação, estádio, financeiro, ingresso, patrocinador, calendário, colocar jogador à venda, fazer proposta, aceitar compra, empréstimo e permissões.
