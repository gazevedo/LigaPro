import { useScreenRefresh } from '../components/useScreenRefresh';
import { useRef, useState } from 'react';
import { Modal, Pressable, Text, TextInput, useWindowDimensions, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useSquadStore } from '../stores/squadStore';
import { useClubStore } from '../stores/clubStore';
import { useAuthStore } from '../stores/authStore';
import { useNotificationStore } from '../stores/notificationStore';
import { squadService } from '../services/squadService';
import { ActionButton, Card, GamePage, NotificationBubble, palette } from '../components/GameUI';
import { PlayerPopup } from '../components/PlayerPopup';
import { PlayerRosterCells, PlayerRosterHeader } from '../components/PlayerRosterColumns';
export function SquadScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'Squad'>) {
  const compact = useWindowDimensions().width < 600;
  const { data, loading, error, ensure } = useSquadStore();
  const [selected, setSelected] = useState<string | null>(null);
  const [editor, setEditor] = useState<string | null>(null), [input, setInput] = useState('');
  const [validation, setValidation] = useState<string | null>(null);
  const [numbers, setNumbers] = useState<Record<string, number>>({});
  const queue = useRef(Promise.resolve()), revisions = useRef<Record<string, number>>({});
  const confirmed = useRef<Record<string, number | null | undefined>>({});
  useScreenRefresh(ensure);
  const players = data?.players ?? [];
  const numberOf = (id: string) => numbers[id] ?? players.find(player => player.id === id)?.shirt_number;
  const duplicates = new Set(players.map(player => numberOf(player.id)).filter(number => number != null && players.filter(player => numberOf(player.id) === number).length > 1));
  const inputNumber = Number(input), inputDuplicate = players.some(player => player.id !== editor && numberOf(player.id) === inputNumber);
  function saveNumber() {
    if (!editor) return;
    if (!/^\d{1,2}$/.test(input) || inputNumber < 1 || inputNumber > 99) { setValidation('Informe um número de camisa de 1 a 99.'); return; }
    if (inputDuplicate) { setValidation('Este número de camisa já está em uso no plantel.'); return; }
    const id = editor, number = inputNumber;
    if (!(id in confirmed.current)) confirmed.current[id] = players.find(player => player.id === id)?.shirt_number;
    const ticket = (revisions.current[id] ?? 0) + 1;
    revisions.current[id] = ticket;
    const owner = useAuthStore.getState().user?.id, club = useClubStore.getState().data?.club?.id;
    const active = () => owner === useAuthStore.getState().user?.id && club === useClubStore.getState().data?.club?.id;
    setNumbers(current => ({ ...current, [id]: number }));
    setEditor(null); setValidation(null);
    queue.current = queue.current.then(async () => {
      if (!active()) return;
      try {
        const result = await squadService.shirtNumber(id, number);
        if (!active()) return;
        confirmed.current[id] = result.shirt_number;
        if (revisions.current[id] === ticket) useSquadStore.setState(state => ({ data: state.data ? { ...state.data, players: state.data.players.map(player => player.id === id ? { ...player, shirt_number: result.shirt_number } : player) } : null }));
      } catch (reason) {
        if (!active() || revisions.current[id] !== ticket) return;
        setNumbers(current => { const next = { ...current }; if (confirmed.current[id] != null) next[id] = confirmed.current[id]!; else delete next[id]; return next; });
        useNotificationStore.getState().show(reason instanceof Error ? reason.message : 'Não foi possível alterar o número da camisa.');
      }
    });
  }
  return <GamePage loading={loading} error={error}><Card><View style={{ width: '100%', minWidth: 0 }}>
    <PlayerRosterHeader compact={compact} trailing="Contrato" />
    {players.map(player => <Pressable key={player.id} accessibilityRole="button" accessibilityLabel={`Detalhes de ${player.name}`} onPress={() => setSelected(player.id)} style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 14, borderTopWidth: 1, borderColor: palette.border }}>
      <Pressable accessibilityRole="button" accessibilityLabel={`Editar camisa de ${player.name}`} onPress={event => { event.stopPropagation(); setInput(String(numberOf(player.id) ?? '')); setValidation(null); setEditor(player.id); }} style={{ width: 42, paddingVertical: 8 }}><Text style={{ fontWeight: '700', color: duplicates.has(numberOf(player.id)) ? '#dc2626' : palette.ink }}>{numberOf(player.id) ?? '—'}</Text></Pressable>
      <PlayerRosterCells player={player} compact={compact} /><Pressable accessibilityRole="button" accessibilityLabel={`Contrato de ${player.name}`} onPress={event => { event.stopPropagation(); navigation.navigate('PlayerNegotiation', { id: player.id }); }} style={{ width: 56, paddingVertical: 8, alignItems: 'center' }}><Text>📄</Text></Pressable>
    </Pressable>)}
    </View>
  </Card><PlayerPopup id={selected} onClose={() => setSelected(null)} navigation={navigation} />
    <Modal visible={editor !== null} transparent animationType="fade" onRequestClose={() => setEditor(null)}>
      <View style={{ flex: 1, justifyContent: 'center', padding: 24, backgroundColor: '#14243a88' }}><View style={{ width: '100%', maxWidth: 420, alignSelf: 'center', padding: 24, gap: 16, borderRadius: 22, backgroundColor: '#fff' }}>
        <Text style={{ color: palette.ink, fontSize: 22, fontWeight: '800' }}>Número da camisa</Text>
        <Text>{players.find(player => player.id === editor)?.name}</Text>
        <TextInput accessibilityLabel="Número da camisa" value={input} onChangeText={value => { setInput(value); setValidation(null); }} keyboardType="numeric" maxLength={2} style={{ padding: 14, borderWidth: 1, borderRadius: 12, borderColor: inputDuplicate ? '#dc2626' : palette.border, color: inputDuplicate ? '#dc2626' : palette.ink }} />
        <NotificationBubble message={validation || (inputDuplicate ? 'Este número de camisa já está em uso no plantel.' : null)} />
        <ActionButton title="Salvar número" onPress={saveNumber} />
        <ActionButton title="Cancelar" secondary onPress={() => setEditor(null)} />
      </View></View>
    </Modal>
  </GamePage>;
}
