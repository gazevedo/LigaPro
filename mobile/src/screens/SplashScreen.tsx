import { ActivityIndicator, Button, StyleSheet, Text, View } from 'react-native';
import { useAuthStore } from '../stores/authStore';
import { useAppStore } from '../stores/appStore';
export function SplashScreen() {
  const app = useAppStore();
  const auth = useAuthStore();
  const loading = app.loading || auth.loading;
  const error = app.error || auth.error;
  async function retry() { await app.initialize(); await auth.restoreSession(); }
  return <View style={styles.container}>
    <Text style={styles.title}>LigaPro</Text>
    {loading && <ActivityIndicator accessibilityLabel="Conectando à API" />}
    {error && <><Text accessibilityRole="alert">{error}</Text>
      <Button title="Tentar novamente" onPress={() => { void retry(); }} /></>}
  </View>;
}
const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, gap: 16 },
  title: { fontSize: 32, fontWeight: 'bold' },
});
