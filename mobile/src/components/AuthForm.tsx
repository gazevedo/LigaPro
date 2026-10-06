import { useState } from 'react';
import { Text } from 'react-native';
import { ActionButton, Card, Field, GamePage, NotificationBubble, palette } from './GameUI';
import { useNotificationStore } from '../stores/notificationStore';
import { useAuthStore } from '../stores/authStore';
export function AuthForm({ register = false, onCreateAccount, onLogin }: {
  register?: boolean; onCreateAccount?: () => void; onLogin?: () => void;
}) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [info, setInfo] = useState<string | null>(null);
  const [validation, setValidation] = useState<string | null>(null);
  const auth = useAuthStore();
  async function submit() {
    auth.clearError(); setValidation(null);
    if (!email.trim() || !password || (register && !name.trim())) {
      setValidation('Preencha os campos obrigatórios.'); return;
    }
    if (register && (password.length < 8 || password.length > 128)) {
      setValidation('A senha deve ter entre 8 e 128 caracteres.'); return;
    }
    if (register && password !== confirm) {
      setValidation('As senhas não conferem.'); return;
    }
    if (register) {
      await auth.register(name.trim(), email.trim().toLowerCase(), password);
      if (useAuthStore.getState().authenticated) useNotificationStore.getState().show('Conta criada! Agora escolha a identidade do seu clube.');
    } else await auth.login(email.trim().toLowerCase(), password);
  }
  return <GamePage error={validation || auth.error} loading={auth.loading}>
    <Text style={{ color: palette.primary, fontWeight: '800', letterSpacing: 4 }}>LIGAPRO</Text>
    <Text style={{ fontSize: 36, fontWeight: '800', color: palette.ink }}>{register ? 'Sua história começa aqui.' : 'Seu próximo título começa aqui.'}</Text>
    <Text style={{ color: palette.muted, fontSize: 16 }}>{register ? 'Crie sua conta e entre direto no jogo para montar seu clube.' : 'Entre para comandar seu clube, desenvolver seu elenco e conquistar o campeonato.'}</Text>
    <NotificationBubble message={info} tone="info" /><Card>
    {register && <Field label="Nome" value={name} onChange={setName} maxLength={100} editable={!auth.loading} />}
    <Field label="E-mail" value={email} onChange={setEmail} keyboardType="email-address" autoCapitalize="none" autoComplete="email" editable={!auth.loading} />
    <Field label="Senha" value={password} onChange={setPassword} secureTextEntry autoCapitalize="none" maxLength={128} editable={!auth.loading} />
    {register && <Field label="Confirmar senha" value={confirm} onChange={setConfirm} secureTextEntry autoCapitalize="none" maxLength={128} editable={!auth.loading} />}
    <ActionButton title={register ? 'Criar conta' : 'Entrar'} onPress={() => void submit()} disabled={auth.loading} />
    {!register && <ActionButton secondary title="Esqueci minha senha" disabled={auth.loading} onPress={() => setInfo('A recuperação de senha ainda não está disponível.')} />}
    <ActionButton secondary title="Continuar com Google" disabled={auth.loading} onPress={() => { auth.clearError(); void auth.loginWithGoogle(); }} />
    {!register && <ActionButton secondary title="Criar conta" disabled={auth.loading} onPress={() => onCreateAccount?.()} />}
    {register && onLogin && <ActionButton secondary title="Já tenho conta" disabled={auth.loading} onPress={onLogin} />}
    </Card></GamePage>;
}
