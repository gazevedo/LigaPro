import { ActionButton as Button, NotificationBubble } from '../components/GameUI';
import { useEffect } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';
import { useSettingsStore } from '../stores/screenStores';
import { useAuthStore } from '../stores/authStore';
export function SettingsScreen() {
  const logout = useAuthStore(state => state.logout);
  const loggingOut = useAuthStore(state => state.loading);
  const { data: settings, loading, error, ensure, load } = useSettingsStore();
  useEffect(() => { void ensure(); }, [ensure]);
  return <View style={styles.container}>
    <Button title={loggingOut ? 'Saindo…' : 'Sair da conta'} disabled={loggingOut} onPress={() => { void logout(); }} />
    {loading ? <ActivityIndicator accessibilityLabel="Carregando configurações" /> : error ?
      <><NotificationBubble message={error} />
        <Button title="Tentar novamente" onPress={() => { void load(); }} /></> :
      <FlatList data={settings ?? []} keyExtractor={(item) => item.id}
        ListEmptyComponent={<Text>Nenhuma configuração cadastrada.</Text>}
        renderItem={({ item }) => <Text>{item.key}: {JSON.stringify(item.value)}</Text>} />}
  </View>;
}
const styles = StyleSheet.create({ container: { flex: 1, padding: 24, gap: 16 } });
