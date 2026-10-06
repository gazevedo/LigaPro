import { UpcomingMatches } from '../components/UpcomingMatches';
import { CupSummary } from '../components/CupSummary';
import { competitionService } from '../services/competitionService';
import { domainStore, resetDomainStores } from '../stores/domainStore';
import { useEffect, useState } from 'react';
import { Button, Text } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { Club } from '../types/game';
import { clubService } from '../services/clubService';
import { useClubStore } from '../stores/clubStore';
import { Field, GamePage, useAction } from '../components/GameUI';
const useCompetitionStore = domainStore(competitionService.get);
export function ClubScreen({ route, navigation }: NativeStackScreenProps<RootStackParamList, 'Club'>) {
  const [club, setClub] = useState<Club | null>(null), [id, setId] = useState('');
  const [confirmResign, setConfirmResign] = useState(false);
  const own = useClubStore(state => state.data?.club?.id);
  const action = useAction();
  const competition = useCompetitionStore();
  const loadCompetition = competition.load;
  useEffect(() => { if (own === route.params.id) void loadCompetition(); }, [own, route.params.id, loadCompetition]);
  useEffect(() => { void action.run(async () => setClub(await clubService.get(route.params.id))); }, [route.params.id]); // eslint-disable-line react-hooks/exhaustive-deps
  return <GamePage loading={action.busy} error={action.error}>{club?.id === route.params.id && <>
    <Text style={{ fontSize: 24, backgroundColor: club.badge?.color }}>{club.badge?.symbol ?? '🛡'} {club.name}</Text><Text>Escudo: {club.badge_id} · País: {club.country?.name ?? club.country_id}</Text>
    <Text>Criado em {new Date(club.created_at).toLocaleDateString('pt-BR')}</Text><Text>Ranking: {club.ranking_position ?? 0} · Pontos: {club.ranking_points ?? club.ranking}</Text><Text>Reputação: {club.reputation ?? 10}/100</Text><Text>Torcida: {club.supporters ?? 1000} · Satisfação: {club.fan_satisfaction ?? 50}/100</Text>
    <Text>Campeonatos: {club.competition_positions.length ? JSON.stringify(club.competition_positions) : 'Nenhum campeonato ativo'}</Text>
    <Text>Troféus: {club.trophies.length ? JSON.stringify(club.trophies) : 'Nenhum troféu'}</Text>
    {own === club.id && competition.error && <Text accessibilityRole="alert">{competition.error}</Text>}
    {own === club.id && competition.data && <>
      <Text>Temporada {competition.data.season.number} · Série {competition.data.division.name}</Text>
      <Text>Classificação · P = pontos, J = jogos, SG = saldo de gols</Text>
      {competition.data.standings.map(row => <Text key={row.id}>
        {row.position}. {row.club_name} · P {row.points} · J {row.games} · SG {row.goal_difference}
      </Text>)}
      <Button title="Atualizar classificação" onPress={() => void loadCompetition()} />
    </>}
    {own === club.id && <UpcomingMatches open={id => navigation.navigate('MatchLive', { id })} />}
    {own === club.id && <CupSummary report={id => navigation.navigate('MatchReport', { id })} />}
    {own === club.id && <Button title="Administrar plantel" onPress={() => navigation.navigate('Squad')} />}
    {own === club.id && !confirmResign && <Button title="Pedir demissão" disabled={action.busy} onPress={() => setConfirmResign(true)} />}
    {own === club.id && confirmResign && <>
      <Text accessibilityRole="alert">Ao pedir demissão, você perderá definitivamente o clube atual, incluindo todo o dinheiro, jogadores, estádio e progresso. O clube será inativado. Você poderá criar um novo clube, sem transferir dinheiro ou patrimônio do anterior. Esta ação não pode ser desfeita.</Text>
      <Button title="Cancelar" disabled={action.busy} onPress={() => setConfirmResign(false)} />
      <Button title="Confirmar demissão e perder o clube" disabled={action.busy} onPress={() => void action.run(async () => {
        const status = await clubService.resign(club.id);
        resetDomainStores();
        useClubStore.setState({ data: status });
      })} />
    </>}
  </>}<Field label="Consultar clube por ID" value={id} onChange={setId} /><Button title="Consultar clube" disabled={!id} onPress={() => navigation.setParams({ id })} /></GamePage>;
}
