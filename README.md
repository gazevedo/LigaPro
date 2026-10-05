# LigaPro — 0.1.0

Fundação técnica do jogo mobile. Nenhuma regra esportiva implementada.

## Arquitetura
React Native / Expo / TypeScript → API REST FastAPI → MongoDB.
O mobile nunca acessa o banco diretamente. Backend separado em controllers,
services, repositories, models e schemas; configurações em `app/config`.

## Requisitos
Python 3.12+, Node 22.13+ LTS e npm, Docker com Compose; Expo Go ou emulador para mobile.
Git já inicializado; remoto: `gazevedo/LigaPro` no GitHub.

## Docker
Na raiz:
```sh
docker compose up -d --build
docker compose ps
curl http://localhost:8000/api/health
```
API na porta 8000; Swagger em `/docs`. MongoDB na porta local 27017, volume
`mongodb_data` persistente. `docker compose down` mantém os dados; não use `-v`
se quiser preservá-los. Esta configuração de MongoDB é para desenvolvimento local;
produção exige autenticação, acesso restrito e TLS. Os endpoints de settings ainda
não têm autenticação e não devem ser expostos publicamente.

## Execução local
```sh
# Na raiz: somente MongoDB em Docker
docker compose up -d mongodb
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
DOCKER_CONFIG=/workspace/ligapro-cloud/docker-config docker compose -f docker-compose.yml -f /workspace/ligapro-cloud/compose.yml up -d --build --wait
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
Fluxo: Splash → health check → Home → Configurações. Se a API falhar,
Splash mostra erro e permite tentar novamente. Novo Jogo e Carregar Jogo
estão desabilitados. Settings lista configurações; edição disponível pela API.

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
Branches: `feature/`, `fix/`, `refactor/`, `docs/`, `chore/`.
Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

Configure proteção de `main` no GitHub: exigir PR e checks `backend` e `mobile`,
impedir push direto e merge com checks falhando. Os arquivos locais não ativam
proteção remota; isso deve ser configurado nas regras do repositório.

Versionamento semântico: versão inicial `0.1.0`. Após revisão e CI aprovado,
releases podem receber tags `v0.1.0`, `v0.2.0`, `v1.0.0`; nenhuma tag criada nesta etapa.

A auditoria npm ainda aponta alertas em dependências transitivas da toolchain Expo/React Native; não foi aplicado `audit fix --force`, que sugere versões incompatíveis. Validação em Android/iOS físico e execução remota do CI continuam pendentes.
