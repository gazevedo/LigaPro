import { useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { Competition } from '../types/game';
import { competitionService, CompetitionMatch } from '../services/competitionService';
import { cupService, Cup } from '../services/cupService';
import { useClubStore } from '../stores/clubStore';
import { ActionButton, Card, Choices, GamePage, palette, useAction } from '../components/GameUI';
import { CompetitionStatistics } from '../components/CompetitionStatistics';
export function CompetitionsScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'Competitions'>) {
  const [kind, setKind] = useState<'league' | 'cup'>('league'), [league, setLeague] = useState<Competition | null>(null), [cup, setCup] = useState<Cup | null>(null), [matches, setMatches] = useState<CompetitionMatch[]>([]);
  const clubId = useClubStore(state => state.data?.club?.id), action = useAction();
  const run = action.run;
  useEffect(() => { void run(async () => {
    if (kind === 'league') { const [table, games] = await Promise.all([competitionService.get(), competitionService.matches()]); setLeague(table); setMatches(games); }
    else { const summary = await cupService.get(); setCup(summary); setMatches(summary.matches); }
  }); }, [kind, run]);
  const columns = [{ title: 'Clube', width: 200 }, ...['P', 'J', 'V', 'E', 'D', 'SG'].map(title => ({ title, width: 44 }))];
  return <GamePage loading={action.busy} error={action.error}><Text style={{ fontSize: 28, fontWeight: '800', color: palette.ink }}>Campeonatos</Text>
    <Choices disabled={action.busy} values={['Liga', 'Copa Nacional']} value={kind === 'league' ? 'Liga' : 'Copa Nacional'} onChange={label => setKind(label === 'Liga' ? 'league' : 'cup')} />
    {kind === 'league' && league && <Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Série {league.division.name} · Temporada {league.season.number}</Text><Text style={{ color: palette.muted }}>Classificação · P pontos · J jogos · V vitórias · E empates · D derrotas · SG saldo</Text>
      <ScrollView horizontal><View style={{ gap: 6 }}><View style={{ flexDirection: 'row', backgroundColor: '#e0eafe', borderRadius: 12, paddingVertical: 12 }}>{columns.map(column => <Text key={column.title} style={{ width: column.width, paddingHorizontal: 8, fontWeight: '800', color: palette.ink }}>{column.title}</Text>)}</View>
        {league.standings.map(row => <View key={row.id} style={{ flexDirection: 'row', paddingVertical: 12, borderRadius: 12, backgroundColor: row.club_id === clubId ? '#daf4e7' : '#f4f7fc' }}>{[`${row.position}. ${row.club_name}`, row.points, row.games, row.wins, row.draws, row.losses, row.goal_difference].map((value, i) => <Text key={i} style={{ width: columns[i].width, paddingHorizontal: 8, color: palette.ink }}>{value}</Text>)}</View>)}
      </View></ScrollView>
    </Card>}
    {kind === 'cup' && <Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Copa Nacional</Text><Text>{cup?.entry ? `${cup.entry.phase} · ${cup.entry.status === 'active' ? 'Em disputa' : cup.entry.status === 'eliminated' ? 'Eliminado' : cup.entry.status === 'champion' ? 'Campeão' : cup.entry.status}` : 'Nenhuma participação nesta temporada.'}</Text></Card>}
    {!action.busy && <Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Jogos do clube</Text>{matches.map(match => <View key={match.id} style={{ gap: 8, backgroundColor: '#f4f7fc', borderRadius: 14, padding: 14 }}>
      <Text style={{ color: palette.muted }}>{match.phase || `Rodada ${match.round}`} · {new Date(match.date).toLocaleString('pt-BR')}</Text><Text style={{ fontWeight: '700', color: palette.ink }}>{match.home_name ?? 'Mandante'} × {match.away_name ?? 'Visitante'}</Text>
      {match.status === 'completed' ? <><Text>{match.home_goals ?? 0} × {match.away_goals ?? 0}</Text><ActionButton secondary title="Ver relatório" onPress={() => navigation.navigate('MatchReport', { id: match.id })} /></> : match.status === 'live' || match.status === 'in_progress' ? <ActionButton title="Assistir" onPress={() => navigation.navigate('MatchLive', { id: match.id })} /> : <Text style={{ color: palette.muted }}>Agendada</Text>}
    </View>)}{!matches.length && <Text style={{ color: palette.muted }}>Nenhuma partida neste campeonato.</Text>}</Card>}
    <CompetitionStatistics key={kind} kind={kind} openPlayer={id => navigation.navigate('PlayerDetails', { id })} />
  </GamePage>;
}
