import { useState } from 'react';
import { FlatList, Modal, Pressable, Text, View } from 'react-native';
import { Catalog } from '../types/game';
import { ActionButton, Field, palette } from './GameUI';
export function CountryPicker({ countries, value, onChange, disabled = false }: { countries: Catalog['countries']; value: string; onChange: (id: string) => void; disabled?: boolean }) {
  const [open, setOpen] = useState(false), [search, setSearch] = useState('');
  const normalize = (text: string) => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const items = countries.filter(country => normalize(`${country.name} ${country.id}`).includes(normalize(search.trim())));
  return <View style={{ gap: 8 }}><Text style={{ fontWeight: '600', color: palette.ink }}>País do clube</Text><ActionButton secondary disabled={disabled} title={`✓ ${countries.find(country => country.id === value)?.name || 'Escolher país'}`} onPress={() => { setSearch(''); setOpen(true); }} />
    <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}><View style={{ flex: 1, backgroundColor: '#14243a88', padding: 24, justifyContent: 'center' }}><View style={{ backgroundColor: '#fff', borderRadius: 24, padding: 24, gap: 16, width: '100%', maxWidth: 560, height: '80%', alignSelf: 'center' }}><Text style={{ fontSize: 24, fontWeight: '700', color: palette.ink }}>Escolha o país</Text><Field label="Buscar país" value={search} onChange={setSearch} placeholder="Nome ou código do país" autoCapitalize="none" />
    <FlatList data={items} keyExtractor={item => item.id} keyboardShouldPersistTaps="handled" ListEmptyComponent={<Text>Nenhum país encontrado.</Text>} renderItem={({ item }) => <Pressable accessibilityRole="button" accessibilityState={{ selected: item.id === value }} onPress={() => { onChange(item.id); setOpen(false); }} style={{ padding: 16, borderBottomWidth: 1, borderColor: palette.border, flexDirection: 'row', gap: 12 }}><Text style={{ color: palette.muted }}>{item.id}</Text><Text style={{ flex: 1, color: palette.ink }}>{item.name}</Text>{item.id === value && <Text>✓</Text>}</Pressable>} />
    <ActionButton secondary title="Fechar lista de países" onPress={() => setOpen(false)} /></View></View></Modal>
  </View>;
}
