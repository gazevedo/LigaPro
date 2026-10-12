import { Pressable, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useClubRankingStore } from '../stores/screenStores';
import { useClubStore } from '../stores/clubStore';
import { useScreenRefresh } from '../components/useScreenRefresh';
import { Card, GamePage, palette } from '../components/GameUI';
export function ClubRankingScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'ClubRanking'>) {
  const store = useClubRankingStore();
  const own = useClubStore(state => state.data?.club?.id);
  useScreenRefresh(store.ensure);
  return <GamePage loading={store.loading} error={store.error}><Card>
    <View style={{ flexDirection: 'row', gap: 8 }}><Text style={{ width: 36 }}>Pos.</Text><Text style={{ flex: 1, fontWeight: '700' }}>Clube</Text><Text style={{ width: 60, textAlign: 'right' }}>Pontos</Text></View>
    {store.data?.map(club => <Pressable key={club.id} accessibilityRole="button" accessibilityLabel={`Abrir clube ${club.name}`} onPress={() => navigation.navigate(own === club.id ? 'Club' : 'OtherClub', { id: club.id })} style={{ flexDirection: 'row', gap: 8, paddingVertical: 14, borderTopWidth: 1, borderColor: palette.border, backgroundColor: own === club.id ? '#daf4e7' : '#fff' }}>
      <Text style={{ width: 36 }}>{club.ranking_position}º</Text><Text style={{ flex: 1, color: palette.ink, fontWeight: '600' }}>{club.name}</Text><Text style={{ width: 60, textAlign: 'right' }}>{club.ranking_points}</Text>
    </Pressable>)}
    {store.data && !store.data.length && <Text style={{ color: palette.muted }}>Nenhum clube classificado.</Text>}
  </Card></GamePage>;
}
