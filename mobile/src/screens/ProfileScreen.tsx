import { ActionButton as Button } from '../components/GameUI';
import { StyleSheet, Text, View } from 'react-native';
import { useAuthStore } from '../stores/authStore';
export function ProfileScreen() {
  const { user, loading, logout } = useAuthStore();
  return <View style={styles.container}>
    <Text>{user?.name}</Text><Text>{user?.email}</Text>
    <Button title="Sair" disabled={loading} onPress={() => { void logout(); }} />
  </View>;
}
const styles = StyleSheet.create({ container: { flex: 1, padding: 24, gap: 16 } });
