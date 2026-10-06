import { ClubBadge } from '../components/ClubBadge';
import { UpcomingMatches } from '../components/UpcomingMatches';
import { NewsFeed } from '../components/NewsFeed';
import { CupSummary } from '../components/CupSummary';
import { Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useClubStore } from '../stores/clubStore';
import { ActionButton, Card, GamePage, palette } from '../components/GameUI';
export function DashboardScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'Dashboard'>) {
  const club = useClubStore(state => state.data?.club);
  return <GamePage><Card><View style={{ flexDirection: 'row', gap: 20, alignItems: 'center' }}><ClubBadge badge={club?.badge} name={club?.name} /><View style={{ flex: 1, gap: 8 }}><Text style={{ color: palette.primary, fontWeight: '700', letterSpacing: 2 }}>CENTRAL DO TÉCNICO</Text><Text style={{ fontSize: 30, fontWeight: '800', color: palette.ink }}>{club?.name}</Text><Text style={{ color: palette.muted }}>{club?.country?.name || club?.country_id} · Sua próxima conquista começa no planejamento.</Text></View></View></Card><Card><UpcomingMatches open={id => navigation.navigate('MatchLive', { id })} /><CupSummary /></Card><Card><NewsFeed /></Card><Text style={{ color: palette.ink, fontSize: 22, fontWeight: '700' }}>Gerencie seu clube</Text><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>
    <ActionButton secondary title="Histórico" onPress={() => navigation.navigate('History')} />
    <ActionButton secondary title="Clube" onPress={() => club && navigation.navigate('Club', { id: club.id })} />
    <ActionButton secondary title="Estatísticas" onPress={() => navigation.navigate('Statistics')} />
    <ActionButton secondary title="Táticas" onPress={() => navigation.navigate('Tactics')} />
    <ActionButton secondary title="Plantel" onPress={() => navigation.navigate('Squad')} />
    <ActionButton secondary title="Estádio" onPress={() => navigation.navigate('Stadium')} />
    <ActionButton secondary title="Financeiro" onPress={() => navigation.navigate('Finance')} />
    <ActionButton secondary title="Calendário" onPress={() => navigation.navigate('Calendar')} />
    <ActionButton secondary title="Mercado" onPress={() => navigation.navigate('Market')} />
    <ActionButton secondary title="Treinamento" onPress={() => navigation.navigate('Training')} />
    <ActionButton secondary title="Categorias de Base" onPress={() => navigation.navigate('YouthAcademy')} />
    <ActionButton secondary title="Perfil" onPress={() => navigation.navigate('Profile')} />
    <ActionButton secondary title="Configurações" onPress={() => navigation.navigate('Settings')} />
  </View></GamePage>;
}
