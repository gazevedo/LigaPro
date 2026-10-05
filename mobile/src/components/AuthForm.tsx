import { useState } from 'react';
import { Alert, Button, ScrollView, StyleSheet, Text, TextInput } from 'react-native';
import { useAuthStore } from '../stores/authStore';
export function AuthForm({ register = false, onCreateAccount }: {
  register?: boolean; onCreateAccount?: () => void;
}) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [validation, setValidation] = useState<string | null>(null);
  const auth = useAuthStore();
  function submit() {
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
    if (register) void auth.register(name.trim(), email.trim().toLowerCase(), password);
    else void auth.login(email.trim().toLowerCase(), password);
  }
  return <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
    {register && <TextInput accessibilityLabel="Nome" placeholder="Nome" value={name}
      onChangeText={setName} maxLength={100} style={styles.input} editable={!auth.loading} />}
    <TextInput accessibilityLabel="E-mail" placeholder="E-mail" value={email} onChangeText={setEmail}
      keyboardType="email-address" autoCapitalize="none" autoComplete="email" style={styles.input}
      editable={!auth.loading} />
    <TextInput accessibilityLabel="Senha" placeholder="Senha" value={password} onChangeText={setPassword}
      secureTextEntry autoCapitalize="none" maxLength={128} style={styles.input} editable={!auth.loading} />
    {register && <TextInput accessibilityLabel="Confirmar senha" placeholder="Confirmar senha"
      value={confirm} onChangeText={setConfirm} secureTextEntry autoCapitalize="none" maxLength={128}
      style={styles.input} editable={!auth.loading} />}
    {(validation || auth.error) && <Text accessibilityRole="alert">{validation || auth.error}</Text>}
    <Button title={register ? 'Criar conta' : 'Entrar'} onPress={submit} disabled={auth.loading} />
    {!register && <Button title="Esqueci minha senha" disabled={auth.loading}
      onPress={() => Alert.alert('Recuperação de senha', 'Esta funcionalidade ainda não está disponível.')} />}
    <Button title="Continuar com Google" disabled={auth.loading}
      onPress={() => { auth.clearError(); void auth.loginWithGoogle(); }} />
    {!register && <Button title="Criar conta" disabled={auth.loading} onPress={onCreateAccount} />}
  </ScrollView>;
}
const styles = StyleSheet.create({ container: { padding: 24, gap: 16 },
  input: { borderWidth: 1, borderColor: '#888', borderRadius: 8, padding: 12 } });
