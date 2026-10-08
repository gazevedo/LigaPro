import { ActionButton as Button, NotificationBubble } from '../components/GameUI';
import { ActivityIndicator, Image, StyleSheet, View } from 'react-native';
import { useAuthStore } from '../stores/authStore';
import { useAppStore } from '../stores/appStore';
export function SplashScreen() {
  const app = useAppStore();
  const auth = useAuthStore();
  const loading = app.loading || auth.loading;
  const error = app.error ? 'Servidor em manutenção, tente mais tarde.' : auth.error;
  async function retry() { await app.initialize(); await auth.restoreSession(); }
  return <View style={styles.container}>
    <Image accessibilityLabel="Logotipo LigaPro" source={require('../../assets/brand/logo-ligapro.png')} resizeMode="contain" style={styles.logo} />
    {loading && <ActivityIndicator accessibilityLabel="Conectando à API" style={styles.spinner} />}
    {error && <><NotificationBubble message={error} />
      <Button title="Tentar novamente" onPress={() => { void retry(); }} /></>}
  </View>;
}
const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, gap: 16, backgroundColor: '#fff' },
  logo: { width: 192, height: 96 },
  spinner: { position: 'absolute', top: '50%', marginTop: 64 },
});
