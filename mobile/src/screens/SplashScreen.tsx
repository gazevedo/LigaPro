import { ActivityIndicator, Button, StyleSheet, Text, View } from 'react-native';
import { useAppStore } from '../stores/appStore';
export function SplashScreen() {
  const { loading, error, initialize } = useAppStore();
  return <View style={styles.container}>
    <Text style={styles.title}>LigaPro</Text>
    {loading && <ActivityIndicator accessibilityLabel="Conectando à API" />}
    {error && <><Text accessibilityRole="alert">{error}</Text>
      <Button title="Tentar novamente" onPress={() => { void initialize(); }} /></>}
  </View>;
}
const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, gap: 16 },
  title: { fontSize: 32, fontWeight: 'bold' },
});
