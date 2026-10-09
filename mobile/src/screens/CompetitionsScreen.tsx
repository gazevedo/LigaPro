import { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useCompetitionStore, useCompetitionMatchesStore, useCupStore } from '../stores/screenStores';
import { useScreenRefresh } from '../components/useScreenRefresh';
import { useClubStore } from '../stores/clubStore';
import { ActionButton, Card, GamePage, palette } from '../components/GameUI';
import { CompetitionStatistics } from '../components/CompetitionStatistics';
function Tabs({ values, selected, onChange, disabled = false, buttons = false }: { values: string[]; selected: string; onChange: (value: string) => void; disabled?: boolean; buttons?: boolean }) {
  return <View accessibilityRole={buttons ? undefined : 'tablist'} style={{ flexDirection: 'row', gap: buttons ? 8 : 0, backgroundColor: buttons ? 'transparent' : '#fff', borderBottomWidth: buttons ? 0 : 1, borderBottomColor: palette.border }}>
    {values.map(value => {
      const active = selected === value;
      return <Pressable key={value} accessibilityRole={buttons ? 'button' : 'tab'} accessibilityState={{ selected: active, disabled }} disabled={disabled} onPress={() => onChange(value)} style={{
        flex: 1, minHeight: 50, paddingHorizontal: 4, alignItems: 'center', justifyContent: 'center',
        borderRadius: buttons ? 14 : 0,
        backgroundColor: buttons && active ? palette.primary : '#fff',
        borderWidth: buttons ? 2 : 0,
        borderColor: buttons && active ? '#086550' : palette.border,
        borderBottomWidth: buttons ? 2 : 3,
        borderBottomColor: buttons ? active ? '#086550' : palette.border : active ? palette.primary : 'transparent',
      }}><Text style={{ fontWeight: active ? '800' : '600', color: buttons && active ? '#fff' : active ? palette.primary : palette.muted, textAlign: 'center' }}>{value}</Text></Pressable>;
    })}
  </View>;
}
export function CompetitionsScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'Competitions'>) {
  const [kind] = useState<'league' | 'cup'>('league'), [tab, setTab] = useState('Tabela');
  const table = useCompetitionStore(), games = useCompetitionMatchesStore(), cupStore = useCupStore();
  const league = table.data, cup = cupStore.data, matches = (kind === 'league' ? games.data : cup?.matches) ?? [];
  const clubId = useClubStore(state => state.data?.club?.id);
  const loading = kind === 'league' ? table.loading || games.loading : cupStore.loading;
  const error = kind === 'league' ? table.error || games.error : cupStore.error;
  useScreenRefresh(() => Promise.all([table.ensure(), games.ensure()]), () => Promise.all([table.refresh(), games.refresh()]), kind === 'league');
  useScreenRefresh(cupStore.ensure, cupStore.refresh, kind === 'cup');
  const columns = [{ title: 'Clube', width: 160 }, ...['P', 'J', 'V', 'E', 'D', 'GP', 'GC', 'SG', 'CV', 'CA'].map(title => ({ title, width: 34 }))];
  return <GamePage loading={loading} error={error}>
    <Tabs values={['Tabela', 'Partidas', 'Artilheiros']} selected={tab} onChange={setTab} />
    {tab === 'Tabela' && kind === 'league' && league && <View style={{ marginHorizontal: -24, paddingVertical: 16, gap: 12, backgroundColor: '#fff' }}><Text style={{ paddingHorizontal: 8, fontSize: 18, fontWeight: '800', color: palette.ink }}>Série {league.division.name} · Temporada {league.season.number}</Text>
      <ScrollView horizontal><View style={{ gap: 4 }}><View style={{ flexDirection: 'row', backgroundColor: '#e0eafe', paddingVertical: 8 }}>{columns.map((column, index) => <Text key={column.title} style={{ width: column.width, paddingHorizontal: 4, fontSize: 12, textAlign: index ? 'center' : 'left', fontWeight: '800', color: palette.ink }}>{column.title}</Text>)}</View>
        {league.standings.map(row => <View key={row.id} style={{ flexDirection: 'row', paddingVertical: 8, backgroundColor: row.club_id === clubId ? '#daf4e7' : '#f4f7fc' }}>{[`${row.position}. ${row.club_name}`, row.points, row.games, row.wins, row.draws, row.losses, row.goals_for, row.goals_against, row.goal_difference, row.red_cards ?? 0, row.yellow_cards ?? 0].map((value, i) => <Text key={i} style={{ width: columns[i].width, paddingHorizontal: 4, fontSize: 12, textAlign: i ? 'center' : 'left', color: palette.ink }}>{value}</Text>)}</View>)}
      </View></ScrollView>
    </View>}
    {tab === 'Tabela' && kind === 'cup' && <Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Copa Nacional</Text><Text>{cup?.entry ? `${cup.entry.phase} · ${cup.entry.status === 'active' ? 'Em disputa' : cup.entry.status === 'eliminated' ? 'Eliminado' : cup.entry.status === 'champion' ? 'Campeão' : cup.entry.status}` : 'Nenhuma participação nesta temporada.'}</Text></Card>}
    {tab === 'Partidas' && <Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Jogos do clube</Text>{matches.map(match => <View key={match.id} style={{ gap: 8, backgroundColor: '#f4f7fc', borderRadius: 14, padding: 14 }}>
      <Text style={{ color: palette.muted }}>{match.phase || `Rodada ${match.round}`} · {new Date(match.date).toLocaleString('pt-BR')}</Text><Text style={{ fontWeight: '700', color: palette.ink }}>{match.home_name ?? 'Mandante'} × {match.away_name ?? 'Visitante'}</Text>
      {match.status === 'completed' ? <><Text>{match.home_goals ?? 0} × {match.away_goals ?? 0}</Text><ActionButton secondary title="Ver relatório" onPress={() => navigation.navigate('MatchReport', { id: match.id })} /></> : match.status === 'live' || match.status === 'in_progress' ? <ActionButton title="Assistir" onPress={() => navigation.navigate('MatchLive', { id: match.id })} /> : <Text style={{ color: palette.muted }}>Agendada</Text>}
    </View>)}{!matches.length && <Text style={{ color: palette.muted }}>Nenhuma partida neste campeonato.</Text>}</Card>}
    {tab === 'Artilheiros' && <CompetitionStatistics key={kind} kind={kind} openPlayer={id => navigation.navigate('PlayerDetails', { id })} />}
  </GamePage>;
}
