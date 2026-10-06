import { ActionButton as Button, NotificationBubble } from '../components/GameUI';
import { useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';
import { settingsService } from '../services/settingsService';
import { AppSetting } from '../types/api';
export function SettingsScreen() {
  const [settings, setSettings] = useState<AppSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  async function fetchSettings() {
    try { setSettings(await settingsService.list()); }
    catch (error) {
      setError(error instanceof Error ? error.message : 'Falha ao carregar configurações.');
    } finally { setLoading(false); }
  }
  useEffect(() => {
    let active = true;
    void settingsService.list()
      .then((items) => { if (active) setSettings(items); })
      .catch((error: unknown) => {
        if (active) setError(error instanceof Error ? error.message : 'Falha ao carregar configurações.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  function load() {
    setLoading(true);
    setError(null);
    void fetchSettings();
  }
  return <View style={styles.container}>
    {loading ? <ActivityIndicator accessibilityLabel="Carregando configurações" /> : error ?
      <><NotificationBubble message={error} />
        <Button title="Tentar novamente" onPress={() => { void load(); }} /></> :
      <FlatList data={settings} keyExtractor={(item) => item.id}
        ListEmptyComponent={<Text>Nenhuma configuração cadastrada.</Text>}
        renderItem={({ item }) => <Text>{item.key}: {JSON.stringify(item.value)}</Text>} />}
  </View>;
}
const styles = StyleSheet.create({ container: { flex: 1, padding: 24, gap: 16 } });
