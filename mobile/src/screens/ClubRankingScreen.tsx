import { useCallback, useState } from 'react';
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
  const [page, setPage] = useState(1);
  const { ensure, refresh } = store;
  const ensurePage = useCallback(() => ensure(page), [ensure, page]);
  const refreshPage = useCallback(() => refresh(page), [refresh, page]);
  useScreenRefresh(ensurePage, refreshPage, true, String(page));
  const data = store.data?.page === page ? store.data : null;
  return <GamePage loading={store.loading || (!data && !store.error)} error={store.error}><Card>
    <View style={{ flexDirection: 'row', gap: 8 }}><Text style={{ width: 36 }}>Pos.</Text><Text style={{ flex: 1, fontWeight: '700' }}>Clube</Text><Text style={{ width: 60, textAlign: 'right' }}>Pontos</Text></View>
    {data?.items.map(club => <Pressable key={club.id} accessibilityRole="button" accessibilityLabel={`Abrir clube ${club.name}`} onPress={() => navigation.navigate(own === club.id ? 'Club' : 'OtherClub', { id: club.id })} style={{ flexDirection: 'row', gap: 8, paddingVertical: 14, borderTopWidth: 1, borderColor: palette.border, backgroundColor: own === club.id ? '#daf4e7' : '#fff' }}>
      <Text style={{ width: 36 }}>{club.ranking_position ? `${club.ranking_position}º` : '—'}</Text><Text style={{ flex: 1, color: palette.ink, fontWeight: '600' }}>{club.name}</Text><Text style={{ width: 60, textAlign: 'right' }}>{club.ranking_points ?? 0}</Text>
    </Pressable>)}
    {data && !data.items.length && <Text style={{ color: palette.muted }}>Nenhum clube classificado.</Text>}
    <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
      <Pressable accessibilityRole="button" accessibilityLabel="Página anterior do ranking" accessibilityState={{ disabled: page <= 1 }} disabled={page <= 1} onPress={() => setPage(current => Math.max(1, current - 1))} style={{ padding: 14, opacity: page <= 1 ? .4 : 1 }}><Text style={{ fontSize: 24, color: palette.primary }}>←</Text></Pressable>
      <View style={{ flex: 1, alignItems: 'center', gap: 4 }}><Text accessibilityLiveRegion="polite">Página {page}{data ? ` de ${data.pages}` : ''}</Text>{data && <Text style={{ color: palette.muted }}>{data.total} clubes</Text>}</View>
      <Pressable accessibilityRole="button" accessibilityLabel="Próxima página do ranking" accessibilityState={{ disabled: !data || page >= data.pages }} disabled={!data || page >= data.pages} onPress={() => setPage(current => current + 1)} style={{ padding: 14, opacity: !data || page >= data.pages ? .4 : 1 }}><Text style={{ fontSize: 24, color: palette.primary }}>→</Text></Pressable>
    </View>
  </Card></GamePage>;
}
