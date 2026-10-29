import { useEffect, useState } from 'react';
import { Text } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { PlayerStars } from '../components/PlayerStars';
import { Player, PlayerSkill } from '../types/game';
import { marketService } from '../services/marketService';
import { ActionButton, GamePage, palette } from '../components/GameUI';
const positions: Record<string, string> = { GK: 'GOL', GOL: 'GOL', CB: 'ZAG', FB: 'LAT', DEF: 'DEF', MID: 'MED', MED: 'MED', ATT: 'ATA', ATA: 'ATA' };
const skills: Record<PlayerSkill, string> = { goalkeeping: 'Defesa do goleiro', speed: 'Velocidade', technique: 'Técnica', passing: 'Passe', tackling: 'Desarme', playmaking: 'Criação de jogadas', finishing: 'Finalização' };
export function PlayerDetailsScreen({ route, navigation }: NativeStackScreenProps<RootStackParamList, 'PlayerDetails'>) {
  const [player, setPlayer] = useState<Player | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    void marketService.player(route.params.id).then(value => { if (active) setPlayer(value); }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'Não foi possível carregar o jogador.'); });
    return () => { active = false; };
  }, [route.params.id]);
  return <GamePage error={error}>{player && <>
    <Text style={{ fontSize: 24 }}>{positions[player.position] ?? player.position} · {player.name}</Text>
    <Text>{player.age} anos · Nota geral: {player.overall}/100 · {player.nationality ?? player.country_id}</Text>
    <Text>Moral: {player.morale ?? 50}% · {(player.morale ?? 50) <= 20 ? 'Muito baixa' : (player.morale ?? 50) <= 40 ? 'Baixa' : (player.morale ?? 50) <= 60 ? 'Normal' : (player.morale ?? 50) <= 80 ? 'Alta' : 'Muito alta'}</Text>
    <PlayerStars count={player.stars} />
    <Text>Energia: {player.energy ?? 100}% · Condição: {player.physical_condition ?? 100}%</Text>
    <Text>Situação: {({ available: 'Disponível', active: 'Ativo', injured: 'Lesionado', suspended: 'Suspenso', free_agent: 'Livre', retired: 'Aposentado' } as Record<string, string>)[player.status ?? 'available'] ?? player.status} · Lado: {({ left: 'Esquerdo', right: 'Direito', both: 'Ambos' } as Record<string, string>)[player.preferred_side ?? 'both'] ?? player.preferred_side}</Text>
    {player.injury_return_at && <Text>Lesão: {player.injury_type} · retorno previsto {new Date(player.injury_return_at).toLocaleDateString('pt-BR')}</Text>}
    {Object.entries(player.individual_skills ?? {}).map(([skill, value]) => <Text key={skill}>{skills[skill as PlayerSkill] ?? skill}: {value}/100</Text>)}
    <Text>Características: {player.innate_characteristics?.join(', ') || '—'}</Text>
    {player.owner_club_id && <Text>Clube proprietário: <Text accessibilityRole="link" style={{ color: palette.primary, textDecorationLine: 'underline' }} onPress={() => navigation.navigate('Club', { id: player.owner_club_id! })}>Ver clube</Text></Text>}
    {player.current_club_id && <Text>Clube atual: <Text accessibilityRole="link" style={{ color: palette.primary, textDecorationLine: 'underline' }} onPress={() => navigation.navigate('Club', { id: player.current_club_id! })}>Ver clube</Text></Text>}
    <ActionButton title="Desempenho e comparação do plantel" onPress={() => navigation.navigate('Performance')} />
    <ActionButton title="📄 Negociação e contrato" onPress={() => navigation.navigate('PlayerNegotiation', { id: player.id })} />
  </>}</GamePage>;
}
