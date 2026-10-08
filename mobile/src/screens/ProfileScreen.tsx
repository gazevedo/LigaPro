import { ActionButton as Button, palette } from '../components/GameUI';
import { StyleSheet, Text, View } from 'react-native';
import { useAuthStore } from '../stores/authStore';
export function ProfileScreen() {
  const { user, loading, logout } = useAuthStore();
  return <View style={styles.container}>
    <Text style={{ color: palette.ink, fontSize: 18, fontWeight: '700' }}>{user?.name}</Text><Text style={{ color: palette.muted }}>{user?.email}</Text>
    <Button title="Sair" disabled={loading} onPress={() => { void logout(); }} />
  </View>;
}
const styles = StyleSheet.create({ container: { gap: 16 } });
