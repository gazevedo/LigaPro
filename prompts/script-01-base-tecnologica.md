# Script 1 — Base tecnológica com Python, MongoDB e GitHub

Objetivo: criar somente a fundação técnica do jogo mobile de gerenciamento de futebol, sem implementar regras esportivas.

## Stack
- React Native
- Expo
- TypeScript
- React Navigation
- Zustand
- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic
- PyMongo
- MongoDB
- Docker
- Git / GitHub

Arquitetura:

Mobile -> API REST FastAPI -> MongoDB

O aplicativo nunca acessa o MongoDB diretamente.

## Estrutura sugerida

project/
  mobile/
  backend/
  docs/
  .github/

Backend:
backend/app/
  main.py
  api/
  controllers/
  services/
  repositories/
  models/
  schemas/
  database/
  core/
  config/
  middleware/
  utils/

tests/
requirements.txt
.env.example

Frontend:
mobile/src/
  app/
  components/
  screens/
  navigation/
  features/
  services/
  stores/
  hooks/
  types/
  utils/
  constants/
  assets/

## Banco
MongoDB como banco principal.
Variáveis:
MONGODB_CONNECTION_STRING
MONGODB_DATABASE_NAME

Collection inicial: app_settings
Campos: _id, key, value, created_at, updated_at
Índice único em key.

## API inicial
GET /api/health
GET /api/settings
GET /api/settings/{key}
PUT /api/settings/{key}

GET /api/health deve validar API e MongoDB.

## Backend
Separar controllers/routes, services, repositories, models e schemas.
Nenhuma rota acessa MongoDB diretamente.
Usar Pydantic, DI quando aplicável, logging centralizado, CORS configurável, tratamento global de erros e UTC/ISO 8601.
ObjectId deve ser exposto como id string, nunca _id bruto.

## Frontend
Criar SplashScreen, HomeScreen e SettingsScreen.
Fluxo: App -> Splash -> health check -> Home.
Home: Novo Jogo, Carregar Jogo, Configurações.
Novo Jogo e Carregar Jogo ainda sem funcionalidade.

Criar apiClient.ts, healthService.ts e settingsService.ts.
Zustand: appStore com initialized, loading, apiAvailable, error.

## Docker
Criar Dockerfile do backend e docker-compose.yml com:
- api na porta 8000
- mongodb na porta 27017
- volume persistente do MongoDB

## Segurança
Não versionar secrets.
Usar .env e .env.example.
Não retornar stack trace em produção.
Não armazenar connection strings no código.

## Testes
Preparar pytest e testes iniciais para health/settings.
Frontend deve compilar com TypeScript strict.

## GitHub
Inicializar Git na raiz e preparar repositório GitHub.
Branch principal: main.

Criar .gitignore cobrindo:
- node_modules
- .expo
- dist/build
- .env e .env.*
- .venv
- __pycache__
- .pytest_cache
- logs
- arquivos temporários
- credenciais e secrets

Manter .env.example versionado.

Criar README principal com arquitetura, requisitos, instalação, execução, Docker, variáveis de ambiente, endpoints e fluxo de desenvolvimento.

Criar .github/workflows/ci.yml para validar pushes/PRs na main.
Backend CI:
- Python 3.12
- instalar dependências
- lint
- pytest
- validar imports

Mobile CI:
- instalar Node
- npm ci
- npm run lint
- npm run typecheck
- npm test

Criar .github/pull_request_template.md.
Criar .github/ISSUE_TEMPLATE/bug_report.md e feature_request.md.
Criar dependabot.yml para npm e pip, semanal.
Não inventar CODEOWNERS sem owner conhecido.

Fluxo de branches:
feature/
fix/
refactor/
docs/
chore/

Commits preferencialmente:
feat:
fix:
refactor:
docs:
test:
chore:

Documentar proteção da main:
- sem push direto
- exigir PR
- exigir CI
- impedir merge com checks falhando

Preparar versionamento semântico, versão inicial 0.1.0 e tags futuras v0.1.0, v0.2.0, v1.0.0.

## Validação final
- backend inicia
- MongoDB conecta
- Swagger /docs abre
- health funciona
- settings funciona
- Docker Compose funciona
- frontend inicia
- Splash/Home/Settings funcionam
- TypeScript sem erros
- testes passam
- nenhum secret versionado
- Git inicializado
- CI criado
- templates de PR/issues criados
- README documentado

Não implementar clubes, jogadores, partidas, campeonatos, transferências ou regras esportivas nesta etapa.
