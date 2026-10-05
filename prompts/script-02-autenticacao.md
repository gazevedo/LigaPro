# Script 2 — Cadastro, Login e Autenticação com Google

Objetivo: implementar exclusivamente identidade e autenticação do usuário.

## Funcionalidades
- cadastro por nome, e-mail e senha
- login por e-mail e senha
- login com Google
- sessão persistente
- access token e refresh token
- logout
- endpoint /me
- proteção de rotas autenticadas

## Collection users
Campos principais:
_id, name, email, password_hash, auth_provider, google_id, avatar_url, email_verified, active, created_at, updated_at, last_login_at.

Índice único por e-mail; índice para google_id.
Senha nunca em texto puro. Preferir Argon2id.

## Endpoints
POST /api/auth/register
POST /api/auth/login
POST /api/auth/google
POST /api/auth/refresh
POST /api/auth/logout
GET /api/auth/me

## JWT
Access Token curto, sugestão 15 min.
Refresh Token longo, sugestão 30 dias.
Configuração por ambiente:
JWT_SECRET_KEY
JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS
GOOGLE_WEB_CLIENT_ID

## Sessões
Criar user_sessions com user_id, refresh_token_hash, device_id, device_name, created_at, expires_at, revoked_at, last_used_at.
Nunca salvar refresh token puro.
Preferir rotação de refresh token.

## Google
Tela com botão Continuar com Google.
Usar integração compatível com React Native + Expo via development build quando necessário.
App recebe credencial Google, envia id_token ao FastAPI, backend valida assinatura, issuer, audience, expiração e identidade.
Nunca usar client secret no app.

Se google_id não existir, buscar por e-mail. Não criar conta duplicada automaticamente quando já existir conta local; retornar orientação segura ou preparar vinculação futura.

## Frontend
Telas:
LoginScreen
RegisterScreen
ProfileScreen

Fluxo:
App -> Splash -> restaurar sessão -> AuthNavigator ou AppNavigator.

LoginScreen:
E-mail
Senha
Entrar
Esqueci minha senha
Continuar com Google
Criar conta

RegisterScreen:
Nome
E-mail
Senha
Confirmar senha
Criar conta
Continuar com Google

Criar authStore com user, authenticated, loading, initialized, error e ações login/register/loginWithGoogle/logout/refreshSession/restoreSession/clearError.

Criar authService.ts, tokenService.ts e integrar apiClient com Authorization Bearer.
Tokens em armazenamento seguro do dispositivo, não AsyncStorage puro.

Ao receber 401 por token expirado: fazer um único refresh concorrente e repetir a requisição. Se refresh inválido/expirado/revogado, limpar sessão e voltar ao Login.

## Segurança
Normalizar e-mail.
No login usar mensagem genérica: “E-mail ou senha inválidos.”
Adicionar rate limit em login/register/google/refresh.
Não expor detalhes internos.

## Validação
Testar cadastro, duplicidade, senha inválida, login válido/inválido, usuário inativo, access/refresh, logout, /me, Google válido/inválido, restauração de sessão e navegação autenticada.

Não implementar ainda recuperação de senha, 2FA, Apple/Facebook, edição de perfil, alteração de senha ou exclusão de conta.
