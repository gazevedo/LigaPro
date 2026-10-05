# LigaPro — 0.1.0

Base técnica, autenticação, gerenciamento de clubes e ciclo competitivo com partidas e campeonatos.

## Arquitetura
React Native / Expo / TypeScript → API REST FastAPI → MongoDB.
O mobile nunca acessa o banco diretamente. Backend separado em controllers,
services, repositories, models e schemas; configurações em `app/config`.

## Requisitos
Python 3.12+, Node 22.13+ LTS e npm, Docker com Compose; Expo Go ou emulador para mobile.
Antes de iniciar o Compose, crie `backend/.env` a partir de `.env.example` e gere
uma chave privada `JWT_SECRET_KEY` com `python -c 'import secrets; print(secrets.token_urlsafe(48))'`.
Salve a chave somente no `.env` local ou no gerenciador de secrets do deploy, nunca no Git.
Git já inicializado; remoto: `gazevedo/LigaPro` no GitHub.

## Docker
Na raiz:
```sh
docker compose --env-file backend/.env up -d --build
docker compose --env-file backend/.env ps
curl http://localhost:8000/api/health
```
API na porta 8000; Swagger em `/docs`. MongoDB na porta local 27017, volume
`mongodb_data` persistente e replica set `rs0` para transações atômicas. O serviço
`mongodb-init` inicializa o conjunto sem apagar os dados. Conexões locais usam
`mongodb://localhost:27017/?directConnection=true`. `docker compose down` mantém os dados; não use `-v`
se quiser preservá-los. Esta configuração de MongoDB é para desenvolvimento local;
produção exige autenticação, acesso restrito e TLS. Os endpoints de settings exigem autenticação Bearer. Use HTTPS em produção.

## Execução local
```sh
# Na raiz: somente MongoDB em Docker
docker compose --env-file backend/.env up -d mongodb mongodb-init
cd backend
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env  # somente se .env não existir
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Não inicie Uvicorn na porta 8000 junto com a API do Compose.

Neste ambiente de nuvem, o build Docker usa um override local em
`/workspace/ligapro-cloud/compose.yml` e wheels baixadas com TLS verificado,
pois a rede do builder não resolve o proxy. O Dockerfile do projeto permanece
usável em redes comuns. Inicialização de nuvem:
```sh
cd /workspace/LigaPro
python3.12 /workspace/ligapro-cloud/prepare_build.py
DOCKER_CONFIG=/workspace/ligapro-cloud/docker-config docker compose --env-file backend/.env -f docker-compose.yml -f /workspace/ligapro-cloud/compose.yml up -d --build --wait
```

Em outro terminal:
```sh
cd mobile
npm ci
cp .env.example .env  # somente se .env não existir
npm start
```
Use Expo Go/emulador ou `npm run web`. Para dispositivo físico, altere
`EXPO_PUBLIC_API_URL` para o IP LAN da máquina; no emulador Android padrão,
use `http://10.0.2.2:8000/api`. Nunca coloque secrets em `EXPO_PUBLIC_*`.
Fluxo: Splash → health check/restauração → Login/Cadastro → criação de clube
ou Dashboard, conforme `/api/game/status`. Dashboard: Clube, Plantel, Estádio,
Financeiro, Calendário e Mercado. Settings lista configurações; edição disponível pela API.

## Variáveis
| Variável | Uso |
| --- | --- |
| `MONGODB_CONNECTION_STRING` | Obrigatória no backend; conexão MongoDB via `.env` |
| `MONGODB_DATABASE_NAME` | Obrigatória no backend; nome do banco |
| `CORS_ORIGINS` | Lista JSON de origens permitidas; padrão sem origens |
| `ENVIRONMENT` | Identifica ambiente; erros HTTP nunca expõem stack traces |
| `EXPO_PUBLIC_API_URL` | URL pública da API, incluindo `/api` |

O Compose fornece a conexão pelo nome do serviço MongoDB. Os valores de
`.env.example` são exemplos locais, não credenciais. Não versione `.env`.

## Endpoints
| Método | Endpoint | Resultado |
| --- | --- | --- |
| GET | `/api/health` | Valida API e MongoDB; 503 se banco indisponível |
| GET | `/api/settings` | Lista configurações |
| GET | `/api/settings/{key}` | Configuração; 404 se ausente |
| PUT | `/api/settings/{key}` | Cria/atualiza com `{"value": ...}` |

Collection `app_settings`: `_id`, `key`, `value`, `created_at`, `updated_at`;
índice único em `key`. API expõe `id` como string e datas UTC/ISO 8601.

## Validação
Com MongoDB local funcionando:
```sh
cd backend
.venv/bin/ruff check .
.venv/bin/pytest -q
MONGODB_CONNECTION_STRING=mongodb://localhost:27017 MONGODB_DATABASE_NAME=ligapro .venv/bin/python -c 'from app.main import app; print(app.version)'
cd ../mobile
npm run lint
npm run typecheck
npm test
```
Pytest usa banco isolado `ligapro_test_<uuid>` e o remove ao terminar.
CI executa os mesmos checks em pushes/PRs para `main`, com MongoDB real.

## Desenvolvimento e GitHub
Use o checkout existente; cada tarefa de nuvem já é isolada, sem necessidade de worktree.
Trabalhe na `main`, sem criar novas branches, conforme orientação atual no `AGENTS.md`.
Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

Configure proteção de `main` no GitHub: exigir PR e checks `backend` e `mobile`,
impedir push direto e merge com checks falhando. Os arquivos locais não ativam
proteção remota; isso deve ser configurado nas regras do repositório.

Versionamento semântico: versão inicial `0.1.0`. Após revisão e CI aprovado,
releases podem receber tags `v0.1.0`, `v0.2.0`, `v1.0.0`; nenhuma tag criada nesta etapa.

A auditoria npm ainda aponta alertas em dependências transitivas da toolchain Expo/React Native; não foi aplicado `audit fix --force`, que sugere versões incompatíveis. Validação em Android/iOS físico e execução remota do CI continuam pendentes.

## Autenticação — Script 2

`POST /api/auth/register` (`name`, `email`, `password`), `/login` (`email`, `password`),
`/google` (`id_token`), `/refresh` e `/logout` (`refresh_token`); `GET /api/auth/me`
exige `Authorization: Bearer <access_token>`. Cadastro/login/Google retornam usuário,
access token e refresh token. Settings também exige Bearer. Logout revoga a sessão,
inclusive seus access tokens, e retorna 204. Senhas usam Argon2id; refresh opaco é
armazenado apenas como SHA-256 e rotacionado atomicamente. Tokens de acesso são JWT
assinados, com issuer/audience e validade configurável. A sessão expira após 30 dias
por padrão, sem renovar indefinidamente esse prazo.

Variáveis adicionais: `JWT_SECRET_KEY` (mínimo 32 caracteres), `JWT_ALGORITHM`
(HS256/HS384/HS512), `ACCESS_TOKEN_EXPIRE_MINUTES` (15), `REFRESH_TOKEN_EXPIRE_DAYS`
(30), `GOOGLE_WEB_CLIENT_ID` e `AUTH_RATE_LIMIT_PER_MINUTE` (10 por IP/endpoint/minuto).
Rate limits são compartilhados via MongoDB; não confie em headers de proxy não autenticados.
As collections `users` e `user_sessions` têm índices de identidade/refresh e TTL;
`auth_rate_limits` usa TTL para limpeza. Nunca dependa apenas do TTL para verificar expiração.

Android/iOS persistem tokens com Expo SecureStore. A versão web mantém sessão somente
em memória. Em 401, uma única operação de refresh atende requisições concorrentes;
refresh inválido limpa a sessão. Login Google usa o módulo nativo em development build,
não Expo Go. Configure IDs públicos nos `.env.example` e consulte
[pendências Google/dispositivos](docs/PENDENCIAS.md). Não há recuperação de senha nem
vinculação automática de conta local com Google nesta etapa.

## Script 3 — clube e gerenciamento inicial

Criação transacional de um clube por usuário, 25 jogadores (3 GOL, 8 DEF, 8 MED,
6 ATA), estádio, escalação e patrocinador inicial. Consulta pública de clube
omite proprietário e finanças; administração sempre usa o clube da sessão.
Não há partidas, campeonatos ou troféus simulados.

Valores monetários são inteiros em centavos. Defaults em `app/models/game.py`:
capital inicial R$ 100.000, patrocínio R$ 5.000 por 90 dias com pagamento único,
estádio de 10.000 lugares, ingresso R$ 20, upgrade R$ 1.000 × nível atual.
Investimentos: 30 dias e 1% por contrato; empréstimos bancários: 30 dias e 5%,
limite R$ 50.000 e um contrato ativo por clube. Estes são defaults iniciais para
esta etapa, configuráveis via `app_settings.game_rules` por administração do
servidor; a API de settings não permite alterar essa chave. Formações também
são configuráveis ali. Jogadores iniciais usam nomes provisórios e overall 50.

Cada receita/despesa registra uma transação; compra e empréstimo de jogador
movimentam saldo, plantéis, anúncio, propostas e histórico na mesma transação.
Empréstimos preservam `owner_club_id`. Uma rotina do backend executa a cada 30s,
mesmo sem usuários conectados, retornos de jogadores, vencimentos de investimentos,
pagamento bancário quando há saldo e expiração de patrocinadores. Contrato bancário
sem saldo fica vencido até pagamento. Transferências preservam um plantel próprio
capaz de escalar 11 jogadores; reservas e escalação são ajustadas no retorno.
Datas usam UTC; sem jogos, bilheteria e eventos de partidas permanecem vazios.

Endpoints autenticados (detalhes e schemas no Swagger):

- `GET /api/game/status`, `GET /api/game/catalog`, `POST /api/clubs`, `GET /api/clubs/{id}`.
- `GET /api/squad`, `PUT /api/squad/lineup`.
- `GET /api/stadium`, `POST /api/stadium/{facility}/upgrade`.
- `GET /api/finance`, `/api/finance/bank`, `/api/finance/tickets`, `/api/finance/sponsors`.
- `POST /api/finance/bank/{investment|bank_loan}`, `/api/finance/contracts/{id}/settle`,
  `/api/finance/sponsors/{id}/accept`; `PUT /api/finance/tickets`.
- `GET /api/calendar?start=...&end=...&type=...`.
- `GET /api/market/players` (nome, posição, país, tipo, intervalos de idade/overall/valor),
  `GET /api/market/mine`, `GET /api/players/{id}`.
- `POST /api/market/listings`, `/api/market/offers`, `/api/market/offers/{id}/accept`,
  `/api/market/listings/{id}/cancel`, `/api/market/offers/{id}/cancel`.

Listas de consulta têm limite de 200 registros (calendário: 500); o plantel e
as validações de escalação consideram todos os jogadores atuais do clube. Google e validações em
dispositivo físico continuam listados em `docs/PENDENCIAS.md`.

## Script 5 — motor de partidas

`backend/app/services/match_engine.py` oferece `MatchEngine.simulate(home, away, seed)`
com `MatchTeam` e onze `MatchPlayer` por escalação. Suporta modos `classic` e `skills`,
posições GK/FB/CB/MID/ATT, fases individuais, táticas, energia, moral e eventos.
`MatchPlayer.from_document` adapta os jogadores atuais sem migrar GOL/DEF/MED/ATA
nem `overall`. O modo `skills` exige as sete habilidades; não inventa atributos ausentes.

O resultado contém placar, eventos, escalações finais e snapshot inicial com seed,
configuração e atributos. O campeonato do script 4 persiste esse resultado em `matches`, com o snapshot
utilizado em cada partida, e executa jogos mesmo sem usuários conectados. Coeficientes em
`MatchConfig` são calibrados pelo script 6; foco usa probabilidade alvo de 70%,
não uma quota por partida.

Testes unitários isolados, sem MongoDB (com as dependências do backend instaladas):
```sh
PYTHONPATH=backend python -m unittest discover -s backend/tests/unit -v
```

## Script 4 — campeonato e desenvolvimento

Divisões de 20 clubes, preenchidas por bots, com turno e returno (38 rodadas).
Novos clubes substituem o pior bot da série mais alta disponível e herdam somente
sua vaga esportiva; resultados originais e auditoria permanecem registrados.
Sem bot disponível, uma nova série é criada. Clubes existentes entram no campeonato
na inicialização, preservando seus jogadores e dados administrativos.

A manutenção a cada 30 segundos joga partidas vencidas e encerra temporadas
idempotentemente. Registra campeão da A, quatro acessos/rebaixamentos por fronteira,
envelhecimento, declínio, aposentadorias, dois jovens e o próximo calendário.
Configuração em `backend/app/config/game.py`, com overrides administrativos em
`app_settings.game_rules`; calendário e regras ficam congelados por temporada.
Defaults: 30 dias, preparação nos dias 0–2 e janela intermediária nos dias 15–17.
Transferências só podem ser concluídas nessas janelas; consultas e propostas continuam disponíveis.

Novos jogadores usam GK/DEF/MID/ATT, força aleatória e `overall` sincronizado;
GOL/MED/ATA antigos continuam compatíveis. Treino ganha um ponto de força a cada
100 cliques válidos, com limite padrão 100. Jovens de 14–17 anos podem ser promovidos
aos 18. Aposentados mantêm histórico e saem do plantel, mercado e treino.
Elencos com menos de onze ativos geram W.O. (3–0; 0–0 se ambos insuficientes).

APIs: `GET /api/competition`, `/api/competition/matches`, `/api/training`, `/api/youth`;
`POST /api/players/{id}/train` e `/api/youth/{id}/promote`.
Mobile: Treinamento e Categorias de Base no dashboard; classificação na tela do clube.
Testes de integração relacionados: `pytest tests/test_game.py tests/test_competition.py -q`.

## Script 6 — calibração

`backend/scripts/calibrate_match_engine.py` executa o motor de produção com seeds
fixas, mando alternado, seis pares de forças e variações controladas de habilidades,
improvisação, lado, energia, moral, formação, estilo, marcação e foco. Inclui as
36 combinações entre nove táticas (três estilos × três marcações) e nove cenários
com táticas distintas contra elenco muito superior. O modo compacto omite snapshots
e escalações finais somente no lote de calibração, mantendo a mesma simulação.

Reproduzir da raiz (sem MongoDB):
```sh
PYTHONPATH=backend python backend/scripts/calibrate_match_engine.py --matches 10000 --workers 4
```
São 85 cenários e 850.000 partidas. Relatórios em
[calibration-script-06.md](docs/calibration-script-06.md) e JSON adjacente incluem
métricas por fase, posse, ataques, chances, finalizações, gols, faltas, cartões,
setores e critérios de aceitação. Posse mede minutos de iniciativa por bloco.
A formação altera presença a partir das posições reais; o mando continua pequeno.
`--categories` e `--matches` permitem lotes exploratórios, que não substituem a
aceitação completa com pelo menos 10.000 partidas por cenário.
