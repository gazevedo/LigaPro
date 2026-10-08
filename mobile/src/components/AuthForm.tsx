import { useState } from 'react';
import { ActivityIndicator, Image, ImageBackground, ImageSourcePropType, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ActionButton, Card, Field, GamePage, NotificationBubble, palette } from './GameUI';
import { useNotificationStore } from '../stores/notificationStore';
import { useAuthStore } from '../stores/authStore';
export function AuthForm({ register = false, onCreateAccount, onLogin, background }: {
  register?: boolean; onCreateAccount?: () => void; onLogin?: () => void; background?: ImageSourcePropType;
}) {
  const [showPassword, setShowPassword] = useState(false);
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
  if (!register) return <ImageBackground source={background} imageStyle={{ width: '100%', height: '100%' }} resizeMode="cover" blurRadius={1} style={styles.background}>
    <View pointerEvents="none" style={styles.overlay} />
    <SafeAreaView style={{ flex: 1 }}><KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.page}>
        <View style={styles.content}><View style={styles.brand}><Image accessibilityLabel="Logotipo LigaPro" source={require('../../assets/brand/logo-ligapro.png')} resizeMode="contain" style={styles.logo} /><Text style={styles.tagline}>Comece sua jornada rumo à glória.</Text></View>
          <View style={styles.form}>
            <NotificationBubble message={validation || auth.error} /><NotificationBubble message={info} tone="info" />
            <View style={styles.field}><Text style={styles.label}>E-mail</Text><TextInput accessibilityLabel="E-mail" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" autoComplete="email" placeholder="seuemail@exemplo.com" placeholderTextColor="#8191a3" editable={!auth.loading} style={styles.input} /></View>
            <View style={styles.field}><Text style={styles.label}>Senha</Text><View style={styles.passwordRow}><TextInput accessibilityLabel="Senha" value={password} onChangeText={setPassword} secureTextEntry={!showPassword} autoCapitalize="none" autoComplete="current-password" maxLength={128} placeholder="Sua senha" placeholderTextColor="#8191a3" editable={!auth.loading} style={[styles.input, styles.passwordInput]} /><Pressable accessibilityRole="button" accessibilityLabel={showPassword ? 'Ocultar senha' : 'Mostrar senha'} accessibilityState={{ disabled: auth.loading }} disabled={auth.loading} hitSlop={6} onPress={() => setShowPassword(value => !value)} style={styles.eye}><Image source={showPassword ? require('../../assets/auth/eye.png') : require('../../assets/auth/eye-off.png')} accessible={false} style={{ width: 24, height: 24 }} /></Pressable></View></View>
            <Pressable accessibilityRole="button" disabled={auth.loading} onPress={() => setInfo('A recuperação de senha ainda não está disponível.')} style={styles.forgot}><Text style={styles.link}>Esqueci a senha</Text></Pressable>
            <Pressable accessibilityRole="button" accessibilityLabel="Entrar" accessibilityState={{ disabled: auth.loading }} disabled={auth.loading} onPress={() => void submit()} style={({ pressed }) => [styles.enter, { opacity: auth.loading ? 0.5 : pressed ? 0.8 : 1 }]}>{auth.loading ? <ActivityIndicator color="#fff" accessibilityLabel="Entrando" /> : <Text style={styles.enterText}>Entrar</Text>}</Pressable>
            <View style={styles.divider}><View style={styles.line} /><Text style={{ color: '#728297' }}>ou</Text><View style={styles.line} /></View>
            <GoogleButton disabled={auth.loading} onPress={() => { auth.clearError(); void auth.loginWithGoogle(); }} />
          </View>
          <View style={styles.signup}><Text style={{ color: '#d5e5ee', fontSize: 15 }}>Não tem conta?</Text><Pressable accessibilityRole="button" disabled={auth.loading} onPress={() => onCreateAccount?.()} hitSlop={8}><Text style={{ color: '#8ce7c9', fontWeight: '800', fontSize: 15 }}>Criar conta</Text></Pressable></View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView></SafeAreaView>
  </ImageBackground>;
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
    <GoogleButton disabled={auth.loading} onPress={() => { auth.clearError(); void auth.loginWithGoogle(); }} />
    {!register && <ActionButton secondary title="Criar conta" disabled={auth.loading} onPress={() => onCreateAccount?.()} />}
    {register && onLogin && <ActionButton secondary title="Já tenho conta" disabled={auth.loading} onPress={onLogin} />}
    </Card></GamePage>;
}

function GoogleButton({ disabled, onPress }: { disabled: boolean; onPress: () => void }) {
  return <Pressable accessibilityRole="button" accessibilityLabel="Continuar com Google" accessibilityState={{ disabled }} disabled={disabled} onPress={onPress} style={({ pressed }) => [styles.google, { backgroundColor: pressed ? '#f2f6fc' : '#fff', opacity: disabled ? 0.5 : 1 }]}>
    <Image accessible={false} source={require('../../assets/auth/google.png')} style={{ width: 18, height: 18 }} />
    <Text style={styles.googleText}>Continuar com Google</Text>
  </Pressable>;
}

const styles = StyleSheet.create({
  background: { flex: 1, width: '100%', overflow: 'hidden', backgroundColor: '#031d30' },
  overlay: { position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, backgroundColor: '#00132355' },
  page: { flexGrow: 1, justifyContent: 'center', paddingHorizontal: 24, paddingVertical: 24 },
  content: { width: '100%', maxWidth: 420, alignSelf: 'center', gap: 14 },
  brand: { alignItems: 'center', gap: 6 },
  logo: { width: '100%', maxWidth: 310, height: 104, backgroundColor: '#fffffff5', borderRadius: 22 },
  tagline: { color: '#e2f2f7', fontSize: 17, lineHeight: 25, textAlign: 'center', maxWidth: 310 },
  form: { backgroundColor: '#fffffff5', borderRadius: 26, padding: 24, gap: 18, borderWidth: 1, borderColor: '#ffffffaa', boxShadow: '0 16px 48px #00000040' },
  field: { gap: 8 },
  label: { color: '#19374b', fontSize: 14, fontWeight: '700' },
  input: { color: '#19374b', fontSize: 16, backgroundColor: '#eff4f7', borderWidth: 1, borderColor: '#d6e1e7', borderRadius: 14, paddingHorizontal: 15, paddingVertical: 15, minHeight: 52 },
  passwordRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#eff4f7', borderWidth: 1, borderColor: '#d6e1e7', borderRadius: 14 },
  passwordInput: { flex: 1, backgroundColor: 'transparent', borderWidth: 0 },
  eye: { minWidth: 48, minHeight: 48, alignItems: 'center', justifyContent: 'center' },
  forgot: { alignSelf: 'flex-end', paddingVertical: 3, marginTop: -8 },
  link: { color: '#087f67', fontWeight: '700', fontSize: 13 },
  enter: { minHeight: 54, backgroundColor: '#087f67', borderRadius: 14, justifyContent: 'center', alignItems: 'center', boxShadow: '0 4px 0 #066551' },
  enterText: { color: '#fff', fontWeight: '800', fontSize: 16, letterSpacing: 1, textTransform: 'uppercase' },
  divider: { flexDirection: 'row', alignItems: 'center', gap: 14, marginTop: 6 },
  line: { flex: 1, height: 1, backgroundColor: '#d6e1e7' },
  google: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 12, paddingHorizontal: 12, backgroundColor: '#fff', borderWidth: 1, borderColor: '#747775', borderRadius: 4, minHeight: 44 },
  googleText: { color: '#1f1f1f', fontSize: 14, fontWeight: '500', letterSpacing: 0.25 },
  signup: { flexDirection: 'row', justifyContent: 'center', flexWrap: 'wrap', gap: 7 },
});
