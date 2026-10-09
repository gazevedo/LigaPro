# LigaPro — 0.1.0

Jogo de gerenciamento de futebol inspirado no Brasfoot, com clubes próprios, campeonatos, mercado, finanças, formação de jogadores e partidas ao vivo. Backend FastAPI/Python, MongoDB e aplicativo React Native/Expo/TypeScript. Implementações dos scripts 1–37 e demissão do técnico integradas na `main`.

Este README concentra a documentação mantida do projeto. Os arquivos em `prompts/` são requisitos originais e podem descrever etapas anteriores; as regras atuais estão abaixo. JSONs de calibração e relatórios gerados permanecem como evidências, sem duplicar instruções de uso.

O dashboard reúne Campeonatos, Clube, Táticas, Plantel, Estádio, Financeiro, Calendário, Mercado, Treinamento e Categorias de Base. Clube mostra o nome do técnico e a bandeira junto ao escudo, com abas Informações e Sala de troféus, histórico, records e logout; Campeonatos possui abas Tabela, Partidas e Artilheiros, com classificação completa e cartões. Escalação e formação são configuradas em Táticas. O Plantel mostra contratos, salários, lesões e desempenho. O calendário é uma agenda mensal e o cabeçalho oferece o correio. Para voltar, deslize da borda esquerda para a direita; no Android, o comando Voltar retorna à tela anterior e permanece no jogo quando chega ao dashboard.

## Índice

- [Como executar](#como-executar)
- [Configuração e autenticação](#configuração-e-autenticação)
- [Regras e funcionalidades](#regras-e-funcionalidades)
- [Motor de partidas](#motor-de-partidas)
- [Partidas ao vivo](#partidas-ao-vivo)
- [API](#api)
- [Persistência e operação](#persistência-e-operação)
- [Testes e calibração](#testes-e-calibração)
- [Limitações e pendências](#limitações-e-pendências)
- [Desenvolvimento e dependências](#desenvolvimento-e-dependências)

## Como executar

### Requisitos

- Docker com Docker Compose para MongoDB e, opcionalmente, API.
- Node.js 22.13+ e npm para o aplicativo; CI utiliza Node 22.
- Python 3.12+ para executar o backend fora do Docker, testes e calibrações.
- Navegador para a versão web; Android Studio/emulador ou dispositivo para Android. Builds iOS locais exigem macOS/Xcode.

Os comandos abaixo usam shell Bash/Linux/macOS/WSL e partem da raiz do repositório. No Windows, a ativação do ambiente Python em PowerShell é `.venv\Scripts\Activate.ps1`.

### Configuração inicial

Copie os exemplos **somente se os arquivos locais ainda não existirem**:

```bash
cp backend/.env.example backend/.env
cp mobile/.env.example mobile/.env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Cole a chave gerada em `JWT_SECRET_KEY=` no `backend/.env`. Ela deve ter pelo menos 32 caracteres. `.env` não é versionado; não publique a chave. Se não houver Python instalado no host, gere a chave com `docker run --rm python:3.12-slim python -c 'import secrets; print(secrets.token_urlsafe(48))'`.

### API e MongoDB com Docker

```bash
docker compose --env-file backend/.env up -d --build
docker compose --env-file backend/.env ps
curl http://localhost:8000/api/health
```

| Serviço | Endereço local |
| --- | --- |
| API | `http://localhost:8000/api` |
| Health check, incluindo MongoDB | `http://localhost:8000/api/health` |
| Swagger e schemas | `http://localhost:8000/docs` |
| OpenAPI | `http://localhost:8000/openapi.json` |
| MongoDB | `mongodb://localhost:27017/?directConnection=true` |
| Aplicativo web | `http://localhost:8081` |

O Compose cria o replica set `rs0` através de `mongodb-init`, necessário às transações. Com `MONGODB_CONNECTION_STRING` vazio, a API em Docker usa o hostname interno `mongodb`; clientes no host usam `localhost`. Uma URI preenchida no `.env` substitui esse padrão. O volume `mongodb_data` persiste os dados.

### Instalar o app web no Android e iPhone

Abra o frontend publicado em HTTPS (`https://ligapro-mobile.vercel.app/`). No Android, use Chrome → menu ⋮ → **Instalar aplicativo** ou **Adicionar à tela inicial**. No iPhone, use Safari → Compartilhar → **Adicionar à Tela de Início**; mantenha **Abrir como App** ativado se essa opção aparecer. Abra pelo ícone LigaPro para usar a janela sem a barra do navegador.

A exportação web inclui manifesto, ícones Android/iOS e service worker. O app precisa de internet para acessar o jogo; offline, mostra uma tela para tentar novamente. O cache persistente do service worker guarda apenas essa tela e ícones públicos, sem respostas da API ou credenciais. Os dados das telas principais são pré-carregados em memória após entrar no clube e descartados ao trocar de conta ou clube. Campeonatos, Financeiro, Mercado, Treinamento e Calendário atualizam os dados a cada três segundos enquanto a tela está visível, preservando conteúdo e campos em edição sem mostrar loader durante a atualização. As consultas não se sobrepõem e a atualização pausa ao sair da tela ou minimizar o aplicativo. Após atualizar esses arquivos no Git, faça um novo deploy do frontend com `npx expo export --platform web`, saída `dist`. A PWA não habilita o login Google web, que ainda precisa de integração própria.

### Backend local para desenvolvimento

Para instalar somente as dependências Python da API a partir da raiz, execute `python -m pip install -r requirements.txt`. Para desenvolvimento e testes, use `python -m pip install -r backend/requirements-dev.txt`. As dependências do aplicativo continuam em `mobile/package.json` e são instaladas com `npm ci` na pasta `mobile`.

Em `backend/.env`, configure `MONGODB_CONNECTION_STRING=mongodb://localhost:27017/?directConnection=true` para o backend executado no host. Inicie apenas o MongoDB em Docker e execute a API no ambiente virtual:

```bash
docker compose --env-file backend/.env up -d mongodb mongodb-init
cd backend
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

O backend lê `.env` do diretório de execução, portanto execute Uvicorn em `backend/`. Não use a API do Compose e Uvicorn simultaneamente na porta 8000. A versão atual requer **um único processo de API**, inclusive para partidas ao vivo.

### MongoDB Atlas ou servidor externo com credenciais

Edite **`backend/.env`**, nunca `.env.example`, com sua URI e nome de banco:

```dotenv
MONGODB_CONNECTION_STRING=mongodb+srv://SEU_USUARIO:SUA_SENHA_CODIFICADA@SEU_CLUSTER.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE_NAME=ligapro
```

No Atlas, crie um usuário de banco com acesso `readWrite` ao banco `ligapro` em **Database Access**, autorize o IP de saída do backend em **Network Access** e copie a URI em **Connect → Drivers**. Senha e usuário com caracteres especiais devem ser codificados para URL. Para outro servidor, use a URI autenticada fornecida por ele e um replica set com transações. Não inclua credenciais no mobile, no Git nem na conversa.

Para executar a API em Docker contra esse banco, sem iniciar o MongoDB local:

```bash
docker compose --env-file backend/.env up -d --build --no-deps api
curl http://localhost:8000/api/health
```

Depois de alterar credenciais/URI, recrie a API para aplicar a configuração:

```bash
docker compose --env-file backend/.env up -d --no-deps --force-recreate api
```

Com Uvicorn local, basta reiniciar o processo em `backend/`. Mantenha a `JWT_SECRET_KEY` privada já configurada: ela protege a sessão do jogo e é independente da senha do MongoDB. O arquivo `.env` permanece ignorado pelo Git. A autenticação do MongoDB local não é habilitada por preencher uma senha na URI; o serviço de desenvolvimento continua sem usuário/senha.

### Aplicativo web, Android e iOS

Em outro terminal:

```bash
cd mobile
npm ci
npm run web
```

Abra `http://localhost:8081`, cadastre uma conta e crie seu clube. O fluxo é: conexão com API → restauração da sessão → login/cadastro → criação de clube ou dashboard. O cadastro autentica automaticamente; uma conta sem clube segue diretamente para a criação, sem botão voltar.

Para iniciar o servidor Expo, use `npm start`. `npm run android` e `npm run ios` iniciam o Expo para os respectivos ambientes. Para um development build nativo, use `npx expo run:android` ou `npx expo run:ios` com a ferramenta de build instalada. Google Sign-In exige esse build; não está disponível no Expo Go nem no cliente web atual.

Configure `EXPO_PUBLIC_API_URL` em `mobile/.env`, sempre incluindo `/api`:

| Cliente | URL |
| --- | --- |
| Navegador no computador | `http://localhost:8000/api` |
| Emulador Android padrão | `http://10.0.2.2:8000/api` |
| Celular físico na mesma rede | `http://IP_LAN_DO_COMPUTADOR:8000/api` |

No celular, `localhost` aponta para o próprio aparelho. A API precisa estar acessível pela rede e pela porta 8000. Reinicie o Expo após alterar o `.env`.

### Parar, diagnosticar e preservar dados

```bash
docker compose --env-file backend/.env logs --tail=100 api mongodb mongodb-init
docker compose --env-file backend/.env down
```

`down` preserva o volume. `down -v` remove o banco e só deve ser usado para apagar os dados intencionalmente.

| Sintoma | Conferência |
| --- | --- |
| API não inicia | `JWT_SECRET_KEY`, arquivos `.env`, logs e porta 8000 ocupada. |
| MongoDB indisponível/erro de transação | Health check, conclusão de `mongodb-init` e replica set `rs0`; MongoDB standalone não atende às transações. |
| App não conecta | URL com `/api`, host correto para o dispositivo e API acessível; valide `/api/health`. |
| Erro CORS na web | Inclua a origem exata do navegador em `CORS_ORIGINS`; o exemplo permite `http://localhost:8081`. |
| Tela carrega dados antigos após configuração | Reinicie o Expo; não reutilize tokens de sessão revogada ou expirada. |
| Google indisponível | IDs OAuth e development build nativo configurados. |

## Configuração e autenticação

### Variáveis do backend

| Variável | Configuração |
| --- | --- |
| `MONGODB_CONNECTION_STRING` | URI privada do banco. Obrigatória para Uvicorn; no Compose, vazia usa o MongoDB local. Atlas/servidor externo substitui o padrão. |
| `MONGODB_DATABASE_NAME` | Obrigatória; exemplo `ligapro`. |
| `JWT_SECRET_KEY` | Obrigatória, privada e com pelo menos 32 caracteres. |
| `CORS_ORIGINS` | Array JSON; exemplo `["http://localhost:8081"]`. Sem configuração, nenhuma origem web é permitida. |
| `ENVIRONMENT` | Exemplo `development`; o Compose usa `production`. |
| `JWT_ALGORITHM` | `HS256` por padrão; aceita `HS384` e `HS512`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 15 por padrão, intervalo 1–60. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 30 por padrão, intervalo 1–90. |
| `GOOGLE_WEB_CLIENT_ID` | ID OAuth Web público validado pelo backend; necessário apenas para Google. |
| `AUTH_RATE_LIMIT_PER_MINUTE` | 10 por padrão, por IP/endpoint/minuto. |

Variáveis do mobile: `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID`, `EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID` e `GOOGLE_IOS_URL_SCHEME`. Tudo em `EXPO_PUBLIC_*` é público: nunca coloque senhas ou secrets nesses campos.

### Sessões

Cadastro/login retornam usuário, access token JWT e refresh token. Senhas usam Argon2id; refresh tokens são opacos, armazenados como hash SHA-256 e rotacionados atomicamente. Logout recebe `refresh_token`, retorna HTTP 204 e revoga a sessão e seus access tokens, inclusive em WebSocket. A duração máxima da sessão não é prolongada indefinidamente pelo refresh.

Android/iOS usam SecureStore; a web mantém tokens em memória. Em HTTP 401, o cliente tenta uma renovação compartilhada entre requisições concorrentes; falha de renovação limpa a sessão. O backend valida expiração explicitamente, sem depender da exclusão pelo TTL do MongoDB.

O cadastro recebe `name`, `email` e `password`; o login recebe `email` e `password`. Exemplo de acesso à API após obter o token na resposta do login:

```bash
curl http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"seu-email@example.com","password":"sua-senha"}'
curl http://localhost:8000/api/game/status -H 'Authorization: Bearer SEU_ACCESS_TOKEN'
```

### Google

1. Configure um OAuth Client ID Web no Google Cloud e use o mesmo ID em `GOOGLE_WEB_CLIENT_ID` e `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID`.
2. Para Android, configure pacote `com.ligapro.app` e SHA-1 do certificado do development build.
3. Para iOS, configure bundle `com.ligapro.app`, `EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID` e `GOOGLE_IOS_URL_SCHEME` com o scheme reverso do ID iOS.
4. Gere o development build e valide o login no dispositivo.

Não existe client secret no aplicativo. Cadastro/login por e-mail funcionam independentemente dessa configuração.

## Regras e funcionalidades

### Clube, direção e confiança da torcida

A confiança da torcida é o único indicador de confiança do clube, de 0 a 100, exibido na aba Informações. Reutiliza o histórico de satisfação existente, sem zerar os dados dos clubes: vitória aumenta 3 pontos, derrota reduz 3, empate reduz 1 quando a reputação supera 50 e ingressos caros podem reduzir até 3 pontos adicionais. Títulos, acessos e rebaixamentos também alteram o indicador no fechamento da competição. Confiança baixa não causa demissão automática nem perda do clube: o usuário administra o clube como diretor.

Público e bilheteria respondem à confiança, junto com preço, capacidade, torcida e reputação. Novas propostas de patrocínio recebem um multiplicador de `0,5 + confiança / 100`: confiança 50 mantém o valor de referência, 0 reduz pela metade e 100 aumenta em 50%. Ofertas já emitidas valem até seu vencimento, e contratos assinados mantêm seus valores até o fim do prazo. `fan_confidence` é exposto pela API; `fan_satisfaction` continua disponível para compatibilidade. Esta é a regra do LigaPro, sem atribuir esses coeficientes ao Brasfoot.

A criação oferece uma lista pesquisável de 249 países e territórios ISO 3166-1 e oito escudos com cores, padrões e iniciais do clube. Os identificadores antigos de países e escudos continuam válidos. Reinicie a API após atualizar para carregar o catálogo no MongoDB.

O aplicativo apresenta erros e avisos em notificações em bolhas. As requisições têm limite de 30 segundos. O clube só é criado quando o usuário confirma em **Criar clube**. Se a criação exceder esse limite ou a sessão expirar, o aplicativo encerra a sessão local e volta ao login, sem reenviar a criação. No próximo login, uma conta sem clube volta à tela inicial de criação.

Cada usuário administra um único clube criado por ele. A criação é transacional: gera 25 jogadores, escalação, estádio, tática, finanças e contrato de patrocínio inicial. O plantel tem 3 goleiros, 8 defensores, 8 médios e 6 atacantes; os defensores profissionais se dividem em FB/CB. Consulta de outro clube exige autenticação e omite propriedade e dados financeiros privados.

O usuário é o diretor do clube e não perde sua gestão por confiança baixa. Na aba Informações, **Logout** encerra a sessão e **Abandonar gestão** permite sair voluntariamente do clube mediante confirmação. A Sala de troféus não exibe essas ações. Contratação de treinadores e compra de moedas com dinheiro real ainda não fazem parte desta atualização.

Abandonar a gestão usa a API de desligamento voluntário, exigindo `{"confirmed": true}` e bloqueando a ação durante partidas ao vivo. A ação preserva dinheiro, jogadores, contratos, estádio, anúncios, partidas e histórico sob controle de um bot, mas o usuário perde o acesso à gestão e aos recursos desse clube. O aplicativo abre a criação de um novo clube, mantendo a sessão e sem criar nada automaticamente. Clubes transferidos para bots não são substituídos ao cadastrar novos clubes, mas estão sujeitos à extinção da última série sem gestores no fechamento da temporada, descrita abaixo.

### Liga, copa e calendário

O dashboard mostra a data e a hora da próxima partida. **Assistir** aparece somente quando a API informa que a partida está ao vivo, com atualização automática a cada 30 segundos enquanto o aplicativo está ativo.

- Divisões de 20 clubes, completadas por bots, com turno e returno: 38 rodadas e 380 jogos por divisão.
- Um clube novo entra sempre na última série ativa, substituindo um bot elegível e herdando somente sua posição esportiva. Vagas em séries superiores não permitem pular etapas. Sem bot disponível na última série, cria-se uma série inferior com o novo clube e 19 bots. Resultados anteriores e auditoria são preservados.
- No fechamento da temporada, após acessos e rebaixamentos, a última série sem nenhum técnico humano é extinta. Seus clubes são inativados, os contratos dos jogadores profissionais são encerrados e eles ficam livres no mercado; jogadores aposentados permanecem aposentados. Empréstimos de clubes sobreviventes retornam ao proprietário. Clubes, partidas e históricos não são excluídos. A verificação continua nas séries inferiores restantes até encontrar uma com técnico. Se nenhuma restar, o próximo clube inicia novamente a Série A com bots novos.
- Nomes de novos jogadores profissionais e da base combinam aleatoriamente dois ou três componentes. A biblioteca brasileira fica em `backend/app/config/player_names/BR.json`, com listas `first_names`, `second_names` e `third_names`. Para outro país, adicione um arquivo com seu código de duas letras e as mesmas listas; países sem biblioteca usam a brasileira. Nomes existentes permanecem iguais.
- Temporada padrão: 30 dias reais. Preparação/janela inicial nos dias 0–2, janela intermediária nos dias 15–17; duas rodadas por dia de jogos, com intervalo de 12 horas: 20 rodadas antes da janela intermediária e 18 depois, sem jogos da liga durante as janelas. Regras e calendário são congelados por temporada.
- Quatro acessos e quatro rebaixamentos por fronteira de divisões. Fechamento registra classificação, campeão, prêmios, envelhecimento, carreira e próximo calendário.
- Copa Nacional paralela, com até 128 participantes das cinco primeiras divisões por padrão. Sorteio determinístico e folgas quando necessário. Jogo único; empate leva a 30 minutos de prorrogação e, persistindo, disputa de pênaltis com morte súbita. Pênaltis da disputa não contam como gols ou minutos individuais da partida.
- Clubes novos herdam a participação ativa do bot substituído na copa. Campeão, avanço, troféus e premiações são persistidos.
- O calendário interno inclui liga, copa, amistosos, início/fim, janelas, geração de juniores e doze fechamentos financeiros; a agenda do app oculta bilheteria, fechamentos financeiros e janelas de transferências, exibindo os compromissos do dia selecionado. Amistosos precisam de horário livre; humanos convidados aceitam e bots aceitam automaticamente.

Tudo continua sendo processado quando os técnicos estão offline. Dados e eventos usam UTC/ISO 8601; o aplicativo apresenta datas no formato local do usuário.

### Jogadores, treino, base e carreira

Profissionais usam GK/FB/CB/MID/ATT, lado, força, estrelas, condição física, energia, moral e sete habilidades: goleiro (`goalkeeping`), velocidade, técnica, passe, desarme, criação e finalização. Características inatas modificam ações relacionadas. A geração inicial profissional usa força 40–60; a base usa 25–45 e idade 14–17.

O modelo profissional atual **não possui potencial/CPE**. Potencial interno e CPE pertencem à base. O treino evolui a habilidade escolhida, mantém progresso técnico separado e recalcula força e valor de mercado. Lesões impedem escalação e treino normal; desgaste depende de minutos, idade e intensidade, com recuperação por tempo lógico e estrutura médica.

A base aceita até 20 juniores ativos. No início de cada temporada, apresenta três candidatos aleatórios e o técnico escolhe apenas um; os outros dois são descartados. Candidatos não podem treinar ou ser promovidos antes da escolha, e a seleção é protegida por transação para impedir duas escolhas em dispositivos diferentes. Juniores já existentes são preservados. Permite treino, promoção a partir dos 18 anos com contrato profissional e dispensa. A promoção remove o CPE do modelo profissional. Desenvolvimento/regressão anual considera idade, treino, minutos, moral, lesões e características; declínio e aposentadoria são graduais a partir das faixas configuradas. Aposentados preservam histórico e deixam plantel, treino e mercado.

Moral vai de 0–100 e varia por participação, resultados, gols, ausência, promoção e transferências; o multiplicador de desempenho fica entre 0,94–1,04, com faixa normal neutra. Entrosamento responde à continuidade da escalação, formação e integração; seu fator fica entre 0,92–1,04. São regras separadas da aleatoriedade do motor.

### Contratos e mercado

Profissionais iniciais recebem contrato de duas temporadas. Renovação aceita salário positivo e prazo de 1–5 temporadas. Uma temporada corresponde a doze meses do jogo; o período salarial é salvo no contrato. Salários contratados não são alterados retroativamente por novas fórmulas de referência.

Salários vencidos são liquidados uma única vez, incluindo períodos offline. Renovação e transferência liquidam o trabalho proporcional. Obrigações salariais podem deixar caixa negativo; contratação e renovação exigem capacidade para a folha resultante. Fim do contrato libera o jogador e ajusta empréstimos, anúncios e escalações. Aposentadoria encerra o vínculo, preservando registros.

Mercado: proposta → vendedor aceita/contrapropõe/recusa → jogador avalia salário, prazo, reputação, divisão e titularidade → comprador confirma. A confirmação na janela é que movimenta dinheiro e propriedade. Consulta e negociação permanecem disponíveis fora da janela. Agentes livres não têm taxa de transferência, mas avaliam o contrato oferecido.

Empréstimos de jogadores têm prazo, taxa e participação salarial; preservam o proprietário, retornam offline e não incluem compra automática. Transferências não podem concluir durante partidas ao vivo nem deixar o clube sem escalação válida. Preço pedido depende da disponibilidade; valor de mercado e salário de referência são fórmulas separadas e próprias do jogo, sem alegar equivalência à fórmula oficial do Brasfoot.

Valor de mercado considera força, idade, posição, estrelas, últimas notas, divisão, reputação e contrato restante. Mudanças após partidas, treino, promoção, transferência, renovação, vencimento e envelhecimento são registradas em histórico próprio.

### Finanças, patrocínio, estádio e torcida

**Todos os valores monetários da API são centavos inteiros:** `10000000` corresponde a R$ 100.000. `balance` e `cash_balance` são atualizados juntos; receitas/despesas geram transações.

| Regra inicial | Valor padrão |
| --- | --- |
| Caixa de clube humano ou bot novo | R$ 100.000 |
| Patrocínio principal mensal | R$ 5.000 |
| Receita mensal de TV | R$ 10.000 |
| Folha inicial alvo dos 25 profissionais | R$ 13.500 |
| Capacidade inicial do estádio | 10.000 lugares |
| Ingresso inicial | R$ 20 |

Um mês do jogo é 1/12 da temporada, ou 2,5 dias reais no padrão de 30 dias. Fechamento mensal credita receitas e liquida salários/parcelas transacionalmente, com marcador único por clube/período. Bilheteria e prêmios são receitas variáveis. Compras exigem caixa; folha, resultado mensal, receitas, despesas e saúde financeira aparecem no financeiro.

Existe um patrocínio principal por clube. Propostas respondem a reputação, divisão, torcida e desempenho; pagamento considera apenas o período coberto pelo contrato, sem duplicar a receita fixa. Expiração e bônus têm identificação própria. Bots escolhem a melhor proposta.

Torcida e satisfação evoluem por resultados, campanhas, títulos, acessos e rebaixamentos. Público considera preço, satisfação, reputação, divisão, classificação, adversário, importância e capacidade. A propensão inicial de comparecimento é 10% da torcida, não 100% de ocupação automática. A bilheteria apresenta previsão de público. Estruturas médica e de treino afetam recuperação/desenvolvimento; bots só ampliam estádio com demanda recorrente, reserva de caixa e retorno estimado suficiente.

Ranking utiliza divisão, classificação, resultados recentes e títulos, cujo peso diminui com o tempo. Reputação cresce lentamente com história esportiva e torcida. Ambos possuem histórico.

### Crédito e investimentos

| Produto | Parcelas mensais do jogo | Juros totais sobre o principal |
| --- | --- | --- |
| Curto (`short_term`) | 3 | 9% |
| Médio (`medium_term`) | 6 | 18% |
| Longo (`long_term`) | 12 | 36% |

Essas taxas são **totais do contrato, não mensais**. Limite de crédito depende de receitas, caixa positivo, reputação, dívida existente e teto configurado. Atraso bloqueia novo crédito; parcelas sem saldo ficam em atraso, sem criar saque bancário negativo. Quitação/liquidação respeita saldo e idempotência. Investimentos ativos e empréstimos bancários não podem coexistir. Contratos bancários legados continuam suportados. Bots tomam crédito apenas para necessidades imediatas da folha.

### Bots, notícias, estatísticas e histórico

Bots usam os mesmos jogadores, motor e serviços: administram escalação, táticas, substituições, mercado, contratos, finanças, treino, base e estádio. Decisões/impedimentos ficam em `bot_decisions`; não recebem dinheiro artificial para cobrir compras.

Notícias são derivadas de eventos reais de transferência, lesão, suspensão, título, finanças, estádio, patrocínio, base e aposentadoria, com deduplicação. O feed pode mostrar clube ou universo. No dashboard, a carta no canto superior direito abre o correio e mostra o total de mensagens não lidas. Abrir uma mensagem salva sua leitura por usuário no MongoDB e reduz o contador; a caixa possui paginação para mensagens antigas.

Estatísticas individuais por clube/temporada/carreira registram partidas, titularidades, minutos reais, gols, cartões, pênaltis, defesas e jogos sem sofrer gols. Assistências têm estrutura preparada, sem atribuição fictícia. Notas de 5–10 derivam das ações e resultado; reservas não utilizados e W.O. não recebem participação inventada.

Histórico registra temporadas, classificações, campeões, acessos/rebaixamentos, finanças, transferências e carreiras. Recordes incluem transferências, valor de mercado, gols, goleadas, público e sequência de vitórias. Pós-jogo reúne timeline, estatísticas, notas, bilheteria e consequências de energia/moral/condição/lesões/suspensões, com navegação para jogador, classificação e calendário.

## Motor de partidas

O motor puro em `backend/app/services/match_engine.py` não acessa o banco. Expõe `MatchEngine`, `MatchTeam`, `MatchPlayer`, `simulate`, `progressive` e `simulate_knockout`; `MatchPlayer.from_document` adapta os documentos. Suporta modo `classic` e modo `skills`, que exige as sete habilidades.

```text
Escalação → força efetiva e setores → iniciativa/construção
→ progressão/disputa individual → falta ou chance → finalização
→ gol, defesa ou erro → placar, eventos e estatísticas
```

Noventa minutos são dezoito blocos de cinco minutos. GK, defesa, meio e ataque contribuem de maneira diferente; formação redistribui os jogadores reais, sem criar atletas ou força. Improvisação e lado inadequado têm penalidades; energia, condição, moral, entrosamento e habilidades influenciam ações. Mando é um modificador pequeno. Força superior aumenta a probabilidade de vitória, sem fixar placar nem impor teto artificial de gols.

Foco em centro/alas tem probabilidade alvo de 70%, não quota obrigatória. Posse mede minutos de iniciativa por bloco, não tracking da bola. Estatísticas derivam dos eventos: finalizações no alvo correspondem a gols e defesas; faltas, amarelo, segundo amarelo e vermelho direto têm eventos distintos. Disputa individual antecede a falta; marcação, resultado e gravidade influenciam disciplina. Pênaltis usam serviço próprio.

Seed, configuração, escalações iniciais, atributos e comandos permitem reprodução determinística. Snapshot inicial e resultado são persistidos. A mesma sequência de entrada produz o mesmo resultado offline/ao vivo; velocidade e presença de usuários não alteram probabilidades.

Táticas persistem formação, estilo (`balanced`, `all_out_attack`, `counter_attack`), marcação (`light`, `heavy`, `very_heavy`) e foco (`normal`, `center`, `wings`). Formações suportadas: 4-4-2, 4-3-3, 4-2-3-1, 3-5-2, 5-3-2, 4-5-1 e 3-4-3. O plano pré-jogo continua sendo aplicado offline; mudanças só afetam blocos futuros. Até cinco substituições por clube, sem reentrada, e até 30 comandos táticos aceitos por técnico. Comandos inviáveis geram rejeição, sem paralisar o jogo.

Bots usam quatro presets (equilibrado, agressivo, contra-ataque e defensivo com marcação pesada), revisam estratégia em 45/65/80 minutos e substituem em 60/75. Reservas preservam energia até entrar. Menos de onze ativos ou clube inativo gera indisponibilidade/W.O.; o resultado normal é 3–0, ou 0–0 se ambos indisponíveis. Não são inventados jogadores para completar o time.

## Partidas ao vivo

Liga, copa e amistosos compartilham o motor progressivo e o fechamento offline. Abrir uma sala não pré-calcula o resultado. Apenas os técnicos dos dois clubes podem acompanhar/controlar a sala; não há espectadores. Cada técnico controla só seu clube, e a tática exata do adversário é privada também no relatório pós-jogo.

| Presença | Comportamento |
| --- | --- |
| Nenhum usuário | Conclusão automática, sem esperar conexão. |
| Um técnico | O ausente conserva decisões pré-jogo; fallback apenas para lesão, goleiro ausente ou escalação inválida. |
| Dois técnicos | Uma única sala autoritativa, placar, relógio e eventos compartilhados. |

Cadência 1×/2×/4× altera apenas apresentação. Entre clubes humanos, 1×; salto para intervalo/fim não é permitido enquanto o adversário acompanha. Cada usuário tem até três pausas táticas de 15 segundos. O intervalo retoma por confirmação ou timeout; desconexão nunca impede conclusão.

O backend mantém uma sala por partida, lock, versão, sequência e fila de comandos. Comando tático tem `command_id` idempotente, payload e confirmação de pendente/aplicado/rejeitado. Eventos e checkpoints são persistidos juntos (a cada 15 minutos simulados, em lances importantes e no término); recuperação reexecuta contexto inicial e comandos até o checkpoint sem repetir consequências financeiras/esportivas.

WebSocket: `/ws/matches/{id}`, com Bearer no header `Authorization` ou subprotocolo `bearer.TOKEN`, nunca token na URL. Cliente envia `join`/`heartbeat`; heartbeat a cada 15 segundos e timeout de recepção de 45 segundos. Conexão expirada/revogada é rejeitada. Mensagens incluem sync, estado, eventos, presença, comandos e término. O cliente reconecta, deduplica por sequência e interpola o relógio local; pressão visual é derivada de eventos, sem modificar o motor.

Exemplo de comando tático pelo WebSocket:

```json
{"type":"tactics_change","command_id":"tatico-001","payload":{"marking":"heavy"}}
```

No REST, `POST /api/matches/{id}/commands/tactics` recebe `{"command_id":"tatico-001","payload":{"marking":"heavy"}}`. Substituição usa `out_player_id` e `in_player_id` no payload. Comandos de velocidade/pausa/retomada/salto usam os tipos de mensagem do controlador em `backend/app/controllers/live.py`. Mobile inclui narração, estatísticas, elenco/banco, controles, overlays de lances relevantes e transição ao pós-jogo.

**Operação: um único processo FastAPI.** Não configure múltiplos workers/réplicas: ownership/locks distribuídos e pub/sub ainda não foram implementados.

## API

A documentação interativa e os schemas completos estão em `/docs`; o contrato estruturado está em `/openapi.json`. Rotas de jogo/settings exigem `Authorization: Bearer TOKEN`; cadastro, login, Google, refresh, logout e health não exigem access token (refresh/logout usam o refresh token). Administração usa o clube da sessão, com verificação de propriedade.

A tabela utiliza `{id}` como identificador textual. Prefixo `/api`, exceto o WebSocket.

| Área | Rotas |
| --- | --- |
| Autenticação | `POST /api/auth/register`, `/api/auth/login`, `/api/auth/google`, `/api/auth/refresh`, `/api/auth/logout`; `GET /api/auth/me`. |
| Health | `GET /api/health`. |
| Clube | `GET /api/game/status`, `/api/game/catalog`, `/api/clubs/{id}`, `/api/clubs/ranking/current`; `POST /api/clubs`, `/api/clubs/{id}/resign`. |
| Plantel/jogador | `GET /api/squad`, `/api/players/{id}`; `PUT /api/squad/lineup`, `/api/players/{id}/transfer-status`. |
| Táticas | `GET`/`PUT /api/tactics`; `POST /api/competition/matches/{id}/commands` (plano pré-jogo). |
| Treino/base | `GET /api/training`, `/api/youth`; `POST /api/players/{id}/train`, `/api/youth/{id}/promote`, `/api/youth/{id}/release`. |
| Contratos | `GET /api/players/{id}/contract`; `POST /api/players/{id}/contract/renew`, `/api/market/players/{id}/sign`. |
| Mercado | `GET /api/market/players`, `/api/market/mine`; `POST /api/market/listings`, `/api/market/offers`, `/api/market/listings/{id}/cancel`, `/api/market/offers/{id}/accept`, `/api/market/offers/{id}/cancel`. |
| Negociação | `POST /api/market/negotiations`, `/api/market/negotiations/{id}/counter`, `/api/market/negotiations/{id}/{action}`; ações: `accept`, `reject`, `confirm`, `accept_counter`. |
| Campeonato | `GET /api/competition`, `/api/competition/matches`, `/api/competition/cup`, `/api/competition/matches/{id}` (pós-jogo). |
| Calendário | `GET /api/calendar`, `/api/calendar/friendlies`; `POST /api/calendar/friendlies`, `/api/calendar/friendlies/{id}/accept`. |
| Finanças | `GET /api/finance`, `/api/finance/bank`; `POST /api/finance/bank/{kind}`, `/api/finance/contracts/{id}/settle`; `kind`: `investment` ou `bank_loan`. |
| Crédito | `POST /api/finance/loans/{product}`, `/api/finance/loans/{id}/settle`; produtos: `short_term`, `medium_term`, `long_term`. |
| Estádio/público | `GET /api/stadium`, `/api/finance/tickets`; `POST /api/stadium/{facility}/upgrade`; `PUT /api/finance/tickets`. |
| Patrocínio | `GET /api/finance/sponsors`; `POST /api/finance/sponsors/{id}/accept`. |
| Estatísticas/feed/histórico | `GET /api/statistics`, `/api/players/{id}/statistics`, `/api/news?scope=club`, `/api/news?scope=universe`, `/api/news/inbox?offset=0&limit=30`, `/api/history`; `POST /api/news/read` recebe `news_id` para marcar a mensagem como lida. |
| Ao vivo | `GET /api/matches/upcoming`, `/api/matches/{id}/live-state`, `/api/matches/{id}/events?after=0`; `POST /api/matches/{id}/commands/{kind}`, `/api/matches/{id}/pause`, `/api/matches/{id}/resume`, `/api/matches/{id}/speed`; `kind`: `substitution`, `formation`, `tactics`, `combined_change`. |
| WebSocket | `WS /ws/matches/{id}`. |
| Settings | `GET /api/settings`, `/api/settings/{key}`; `PUT /api/settings/{key}` com `{"value": ...}`. |

Datas de filtros são ISO 8601. Consultas comuns têm limites de resultados; calendário limita a 500, e listas administrativas/plantéis usam suas próprias consultas. A resposta pública usa `id` textual no lugar de `_id` e datas UTC. HTTP 401 indica sessão inválida, 403 acesso negado, 409 conflito de regra/estado, 422 dados inválidos e 503 indisponibilidade do banco; erros internos não expõem stack traces.

## Persistência e operação

| Local | Responsabilidade |
| --- | --- |
| `backend/app/controllers`, `schemas` | Endpoints, validação e contratos de entrada. |
| `backend/app/services`, `repositories`, `models` | Regras, persistência e projeções públicas. |
| `backend/app/config` | Configurações de motor, competição, economia, disciplina, carreira e condição. |
| `backend/tests`, `backend/scripts` | Testes e runners de calibração. |
| `mobile/src/screens`, `components`, `navigation` | Telas, controles e fluxo do aplicativo. |
| `mobile/src/services`, `stores`, `types` | Cliente REST/WebSocket, sessão, cache e tipos. |
| `docs/*.json`, `reports/global-balance/` | Dados e relatórios gerados de medição. |
| `prompts/script-*.md` | Requisitos originais de implementação, incluindo o adendo do script 22. |
| `.github/workflows/ci.yml`, `.github/dependabot.yml` | CI e política de atualizações automáticas. |

O mobile acessa somente a API, nunca o MongoDB diretamente. Transações multi-documento e índices únicos protegem propriedade, dinheiro, resultados e deduplicação. Coleções principais: `clubs`, `players`, `lineups`, `club_tactics`, `club_finances`, `financial_transactions`, `player_contracts`, `seasons`, `season_clubs`, `standings`, `matches`, `competitions`, `competition_matches`, `friendly_matches`, `calendar_events`, históricos e estatísticas. Sessões/rate limit usam `users`, `user_sessions` e `auth_rate_limits`. Ao vivo usa `match_contexts`, `match_commands`, `match_participants`, `match_events` e `match_live_snapshots`.

A inicialização testa o banco, cria índices, insere catálogos/regras ausentes e executa bootstraps/migrações idempotentes. Dados financeiros e contratos existentes são preservados; partidas históricas não são recalculadas. O modelo revisado separa progresso técnico dos atributos profissionais e remove potencial profissional legado.

Manutenção embutida roda a cada 30 segundos, com relógio UTC: reclama salas ao vivo vencidas e processa partidas/temporadas, finanças, contratos, bots, negociações expiradas, retornos de empréstimos e obrigações bancárias/patrocínios. Liga, copa e amistosos são ordenados pelas datas lógicas. O servidor precisa estar em execução para processar o universo; ficar sem usuário conectado não é o mesmo que parar o servidor. Reinício recupera partidas ao vivo persistidas e retoma processamento vencido. Fechamentos repetidos não reaplicam resultados, prêmios ou salários.

Regras administrativas estão em `app_settings.game_rules`, combinadas com defaults do código. **A API pública de settings não permite editar `game_rules`**; alterações exigem administração do servidor. A configuração da temporada é congelada, portanto não suponha que mudar uma regra altere partidas já agendadas daquela temporada. A tela Settings consulta as configurações; edição das demais chaves usa API autenticada.

Para deploy, configure HTTPS/WSS, origens CORS exatas, secrets, MongoDB com autenticação/TLS/restrição de rede, volume persistente e backup restaurável. O Compose atual é uma configuração de desenvolvimento, mesmo com `ENVIRONMENT=production` na API: o MongoDB local não tem autenticação. Proxy reverso precisa encaminhar upgrade de WebSocket e permitir heartbeats. Preserve o processo único até haver coordenação distribuída; migrations/bootstraps não substituem backup.

## Testes e calibração

### Validação de código

Com MongoDB replica set local em execução e dependências instaladas, a partir de `backend/`:

```bash
. .venv/bin/activate
ruff check .
PYTHONPATH=.:tests/unit pytest tests/unit -q
PYTHONPATH=.:tests pytest tests --ignore=tests/unit -q
```

As duas coletas são separadas porque existem arquivos de mesmo nome nas pastas de testes unitários e de integração. Testes de integração usam um banco isolado `ligapro_test_<uuid>` e o removem ao terminar; o worker de tempo real é isolado e os cenários avançam o relógio explicitamente. Para mudanças pontuais, execute somente os testes relacionados. Configuração do backend é validada antes da conexão.

Em `mobile/`:

```bash
npm ci
npm run lint
npm run typecheck
npm test
npx expo install --check
```

CI possui jobs backend/mobile em pushes e PRs para `main`, com Python 3.12, MongoDB 8 replica set e Node 22. O workflow atual ainda coleta `pytest -q` conjuntamente; os nomes repetidos podem causar `import file mismatch`. Os comandos locais acima separam a coleta. Execução remota do CI e testes físicos não são comprovados pelos testes locais.

Cobertura existente inclui concorrência/transações, criação e demissão, escalações, transferência/contratos, copa e temporada completa, finanças/crédito, bots, base/carreira, notícias/histórico, determinismo do motor, replay/reconexão/privacidade ao vivo e telas mobile. Na revisão de dependências de 06/10/2026 passaram 65 testes mobile, lint, TypeScript, instalação pelo lockfile e verificação de versões do Expo. Demissão foi validada com cinco testes backend e nove mobile. Esses números são registros daquela execução, não um resultado automaticamente atualizado.

### Reproduzir medições

Com dependências Python instaladas, execute da raiz; os runners usam o motor/regra pura e não exigem MongoDB:

```bash
PYTHONPATH=backend python backend/scripts/calibrate_match_engine.py --matches 10000 --workers 4
PYTHONPATH=backend python backend/scripts/calibrate_player_management.py --output docs/player-management-calibration.json
PYTHONPATH=backend python backend/scripts/simulation_season_runner.py --scales 10 100 1000 --seeds 35 135 235 335 --workers 4 --output reports/global-balance
```

O runner do motor aceita `--seed`, `--categories` e `--output`; `--matches` é quantidade par por cenário, padrão 10.000. O relatório inclui configuração, hash do motor, fases, posse, ataques, chances, finalizações, gols, faltas, cartões, setores e aceitação. Alterar categorias/seeds/quantidade gera uma nova medição, não reproduz necessariamente todos os relatórios históricos. Pode gerar Markdown ao lado do JSON; esses arquivos são saídas automáticas, não documentos de regras mantidos separadamente.

### Evidências históricas de calibração

| Medição | Escopo e resultado registrado | Dados |
| --- | --- | --- |
| Script 6 | 85 cenários × 10.000 jogos = 850.000 partidas; pares de forças, habilidades, improvisação, lado, energia, moral, formação, 36 confrontos táticos e nove cenários de elenco inferior. Base 70×70: 2,3841 gols/jogo e 26,39% de empates. | [JSON](docs/calibration-script-06.json) |
| Script 7 | 36 confrontos × 10.000 partidas, mando alternado; nenhuma tática supera todas as oito alternativas por mais de dois pontos percentuais. | [JSON](docs/calibration-script-07.json) |
| Script 9 — disciplina | 10.000 jogos por marcação; seis critérios aprovados. | [JSON](docs/calibration-script-09.json) |
| Script 9 — regressão | 460.000 partidas de base, estilos e matriz tática; base equivalente: 2,3707 gols/jogo, 26,59% de empates; sem combinação dominante na amostra. | [JSON](docs/calibration-script-09-regression.json) |
| Gestão de jogadores | 10.000 jogadores: mediana R$ 9.600, P90 R$ 29.800 e P99 R$ 74.700. Em 10.000 partidas: 638 lesões (470 leves, 143 moderadas, 25 graves), duração média 2,448 partidas. | [JSON](docs/player-management-calibration.json) |
| Balanceamento global | Escalas somadas de 10, 100 e 1.000 temporadas; 7.600, 76.000 e 760.000 jogos, respectivamente. | [JSON](reports/global-balance/balance_report.json), [relatório gerado](reports/global-balance/balance_report.md), [caixa](reports/global-balance/balance_cash.svg), [força](reports/global-balance/balance_strength.svg) |

A medição de lesões teve 1.250 partidas por subgrupo: jovens com condição 100/35 registraram 0,0336/0,1000 lesão por jogo; idade 36, 0,0488/0,1216. Pequenas inversões entre grupos próximos são variação amostral. A amostra de mercado inclui cauda de elite; não representa o elenco inicial limitado a força 40–60.

O desenho matemático inicial v1 reduziu aproximadamente 3,93 para 2,54 gols/jogo no cenário 70×70, reduzindo conversão de chances. Naquela versão: mando +3% no meio/+4% no ataque, variação por bloco ±5%, criação base 0,46/sensibilidade 0,75, gol base 0,30/sensibilidade 0,55 e faixa de gol 4%–48%. Esses parâmetros são históricos, não defaults atuais. Resultados em seis cenários (10.000 partidas cada):

| Forças casa×fora | Vitórias casa | Empates | Vitórias fora | Gols/jogo | Gols casa | Gols fora |
| --- | --- | --- | --- | --- | --- | --- |
| 70×70 | 39,9% | 26,1% | 34,0% | 2,54 | 1,33 | 1,21 |
| 75×70 | 49,0% | 24,8% | 26,2% | 2,57 | 1,52 | 1,05 |
| 80×60 | 73,3% | 17,1% | 9,7% | 2,88 | 2,20 | 0,68 |
| 60×80 | 12,2% | 18,9% | 68,9% | 2,80 | 0,74 | 2,06 |
| 90×40 | 96,0% | 3,4% | 0,7% | 3,95 | 3,71 | 0,24 |
| 40×90 | 0,9% | 4,1% | 95,0% | 3,83 | 0,26 | 3,56 |

Essa v1 e os relatórios 6/7 precedem alterações posteriores; não são a configuração atual nem substituem nova medição após mudanças. As métricas completas da calibração 6 permanecem no JSON, inclusive critérios de aceitação e distribuições por cenário. Dominância tática é definida para a matriz/amostra controlada, não uma prova sobre todas as escalações. Os seeds são compartilhados entre cenários; variações pequenas têm incerteza estatística.

Comparações históricas de regressão: scripts 11–15 versus `0da0ce4`, 82 cenários × 20 seeds (1.640 jogos), placares/estatísticas iguais com moral/entrosamento neutros; scripts 16–20 versus `42922aa`, 85 × 20 (1.700 jogos), resultados completos iguais. Projeções financeiras de cinco temporadas com elenco fixo verificaram receitas, salários e idempotência; projeção adicional incluiu bilheteria/prêmios/torcida controlada. A validação de carreira incluiu dez temporadas com 800 jogadores. São recortes históricos, não testes reexecutados ao editar este README.

### Limites do balanceamento global

O maior cenário soma quatro universos persistentes independentes, seeds 35/135/235/335, com 250 temporadas consecutivas cada: total de 1.000 temporadas, duas divisões e 760.000 jogos. Usa o motor de produção e regras compartilhadas de carreira, salário, mercado, patrocínio, público e acessos/rebaixamentos.

O modelo em memória simplifica negociações/aceitação, contabiliza fluxo de caixa anual de doze meses e transferências limitadas que conservam caixa, usa desgaste dos titulares e não propaga todas as notas/minutos do banco. Torcida e capacidade são fixas; não mede expansão do estádio ou crescimento de torcida. Exclui transações MongoDB, renda da copa e decisões humanas. Não substitui os testes dos serviços completos dos bots ou da persistência.

A medição registrada não emitiu alertas nas bandas configuradas e não motivou mudança subjetiva de parâmetros. Relatórios declaram metodologia, limitações e unidade monetária em centavos. Reexecutar 1.000 temporadas é custoso; use `--scales 10` para exploração, sem tratá-la como validação equivalente.

## Limitações e pendências

- Sessões ao vivo dependem de processo único. Para múltiplos workers/réplicas faltam ownership/locks distribuídos e pub/sub.
- Google OAuth precisa de IDs/certificados próprios e validação em development builds; login Google web não está implementado.
- Validar em Android/iOS físico: login, fechamento/reabertura, SecureStore/restauração, navegação e reconexão ao vivo.
- Não há recuperação de senha nem vinculação automática de conta Google a conta local.
- Assistências não são inventadas; o contador depende de futura atribuição real pelo motor. Clima/árbitros mencionados no desenho inicial não significam funcionalidades implementadas.
- A auditoria npm tem alertas transitivos da toolchain. Não foi aplicado `audit fix --force`, que pode quebrar compatibilidade Expo/React Native.
- Coleta conjunta dos testes backend/CI precisa considerar nomes de módulos repetidos, como explicado acima. CI remoto, deploy e builds físicos requerem validação própria.
- Produção exige autenticação do MongoDB, backup/restauração, HTTPS/WSS, secrets e configuração de rede. O Compose local não cobre essa implantação.

## Desenvolvimento e dependências

Repositório: `gazevedo/LigaPro`. Trabalhe na **`main`**, sem criar branches, conforme [AGENTS.md](AGENTS.md). Use commits `feat:`, `fix:`, `docs:`, `test:`, `chore:` etc. Valide somente as áreas alteradas, não amplie escopo e não introduza dependências sem necessidade. Versão atual 0.1.0; releases podem usar versionamento semântico, mas não há release/tag criada por esta documentação.

Em 06/10/2026, cinco branches do Dependabot foram revisadas e integradas ao histórico da `main`. Depois os branches remotos foram removidos; restou a `main`. Eram somente atualizações de dependências, sem novas funcionalidades. As seguintes atualizações ficaram nas versões compatíveis:

| Dependência | Atualização proposta | Versão mantida / motivo |
| --- | --- | --- |
| React e `@types/react` | 19.3 | React 19.2.3, tipos ~19.2: renderizador embarcado no React Native 0.86.3 usa React 19.2.3. |
| `react-test-renderer` | 19.3.0 | 19.2.3, alinhado ao React. |
| `react-native-screens` | ~4.28.0 | ~4.26.0, esperado pelo Expo 57. |
| `test-renderer` | ~1.3.0 | ~1.2.0; a 1.3 traz reconciler cujo peer exige React 19.3. |
| TypeScript | ~7.0.2 | ~5.9.2; a 7 quebra o lint do Expo (`TypeFlags.Intrinsic`) e a descoberta de tipos Jest/Node. |

React DOM acompanha React em 19.2.3. Não atualize esses pacotes isoladamente; verifique a matriz do Expo, o renderizador nativo, tipos, lint, testes e builds. `npm ci` usa o lockfile versionado; para verificar alinhamento, execute `npx expo install --check`.

Dependabot utiliza `open-pull-requests-limit: 0` para atualizações de versões npm/pip. Isso interrompe novas PRs automáticas de versões; alertas e atualizações de segurança têm configuração separada no GitHub. Proteção de branch e permissões são configuradas no GitHub, não pelos arquivos locais; mantenha qualquer regra compatível com o fluxo autorizado de trabalho na `main`.

### Versão do aplicativo

O rodapé do login mostra `v1.0.0.0`, no formato principal.secundária.correção.revisão, definido em `mobile/version.json`. O workflow **App version** incrementa automaticamente a revisão após atualizações na `main` e envia um commit com o novo número. A primeira publicação mantém a revisão zero; commits que alteram apenas esse arquivo não reiniciam o workflow. A automação precisa de permissão de escrita na `main`. O deploy do frontend deve usar o commit mais recente, incluindo a atualização automática. Para uma nova versão principal, secundária ou de correção, ajuste esses campos e zere a revisão. Expo usa os três primeiros números; o rodapé inclui os quatro.
