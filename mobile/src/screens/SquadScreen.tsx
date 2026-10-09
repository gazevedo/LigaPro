import { useScreenRefresh } from '../components/useScreenRefresh';
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useSquadStore } from '../stores/squadStore';
import { Card, GamePage, palette } from '../components/GameUI';
import { PlayerPopup } from '../components/PlayerPopup';
import { PlayerStars } from '../components/PlayerStars';
export function SquadScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'Squad'>) {
  const { data, loading, error, ensure } = useSquadStore();
  const [selected, setSelected] = useState<string | null>(null);
  useScreenRefresh(ensure);
  return <GamePage loading={loading} error={error}><Card>
    <View style={{ flexDirection: 'row', gap: 8 }}><Text style={{ flex: 1, fontWeight: '700' }}>Nome</Text><Text style={{ width: 36 }}>Idade</Text><Text style={{ width: 40 }}>Força</Text><Text style={{ width: 65 }}>Estrelas</Text></View>
    {data?.players.map(player => <Pressable key={player.id} accessibilityRole="button" accessibilityLabel={`Detalhes de ${player.name}`} onPress={() => setSelected(player.id)} style={{ flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 14, borderTopWidth: 1, borderColor: palette.border }}>
      <Text style={{ flex: 1, color: palette.ink, fontWeight: '600' }}>{player.name}</Text><Text style={{ width: 36 }}>{player.age}</Text><Text style={{ width: 40 }}>{player.strength ?? player.overall}</Text><View style={{ width: 65 }}><PlayerStars count={player.stars} /></View>
    </Pressable>)}
  </Card><PlayerPopup id={selected} onClose={() => setSelected(null)} navigation={navigation} /></GamePage>;
}
