import { useState } from 'react';
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { ClubBadge } from '../components/ClubBadge';
import { DashboardIcon, DashboardIconName } from '../components/DashboardIcon';
import { UpcomingMatches } from '../components/UpcomingMatches';
import { RootStackParamList } from '../navigation/types';
import { useClubStore } from '../stores/clubStore';
import { Card, GamePage, palette } from '../components/GameUI';

type Shortcut = { icon: DashboardIconName; title: string; open: () => void; disabled?: boolean };

export function DashboardScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'Dashboard'>) {
  const club = useClubStore(state => state.data?.club);
  const { width } = useWindowDimensions();
  const [gridWidth, setGridWidth] = useState(Math.max(0, Math.min(width, 1000) - 48));
  const columns = gridWidth >= 600 ? 4 : gridWidth >= 330 ? 3 : 2;
  const tileWidth = Math.max(0, Math.floor((gridWidth - 12 * (columns - 1)) / columns));
  const shortcuts: Shortcut[] = [
    { icon: 'competitions', title: 'Campeonatos', open: () => navigation.navigate('Competitions') },
    { icon: 'club', title: 'Clube', disabled: !club, open: () => { if (club) navigation.navigate('Club', { id: club.id }); } },
    { icon: 'tactics', title: 'Táticas', open: () => navigation.navigate('Tactics') },
    { icon: 'squad', title: 'Plantel', open: () => navigation.navigate('Squad') },
    { icon: 'stadium', title: 'Estádio', open: () => navigation.navigate('Stadium') },
    { icon: 'finance', title: 'Financeiro', open: () => navigation.navigate('Finance') },
    { icon: 'calendar', title: 'Calendário', open: () => navigation.navigate('Calendar') },
    { icon: 'market', title: 'Mercado', open: () => navigation.navigate('Market') },
    { icon: 'training', title: 'Treinamento', open: () => navigation.navigate('Training') },
    { icon: 'youth', title: 'Categorias de Base', open: () => navigation.navigate('YouthAcademy') },
  ];

  return <GamePage>
    <Card><View style={styles.hero}>
      <ClubBadge badge={club?.badge} name={club?.name} />
      <View style={styles.identity}>
        <Text style={styles.eyebrow}>CENTRAL DO TÉCNICO</Text>
        <Text style={styles.clubName}>{club?.name}</Text>
        <Text style={styles.subtitle}>{club?.country?.name || club?.country_id} · Sua próxima conquista começa no planejamento.</Text>
      </View>
    </View></Card>
    <View style={styles.sectionHeading}>
      <Text style={styles.sectionTitle}>Gerencie seu clube</Text>
      <Text style={styles.subtitle}>Tudo para comandar sua equipe.</Text>
    </View>
    <View style={styles.grid} onLayout={event => setGridWidth(event.nativeEvent.layout.width)}>
      {shortcuts.map(shortcut => <Pressable key={shortcut.icon}
        accessibilityRole="button" accessibilityLabel={shortcut.title}
        accessibilityState={{ disabled: !!shortcut.disabled }}
        disabled={shortcut.disabled} onPress={shortcut.open}
        style={({ pressed }) => [styles.tile, { width: tileWidth },
          pressed && styles.tilePressed, shortcut.disabled && styles.tileDisabled]}>
        <DashboardIcon name={shortcut.icon} />
        <Text style={styles.tileTitle}>{shortcut.title}</Text>
      </Pressable>)}
    </View>
    <Card><UpcomingMatches open={id => navigation.navigate('MatchLive', { id })} /></Card>
  </GamePage>;
}

const styles = StyleSheet.create({
  hero: { flexDirection: 'row', gap: 20, alignItems: 'center' },
  identity: { flex: 1, gap: 8 },
  eyebrow: { color: palette.primary, fontWeight: '700', letterSpacing: 2 },
  clubName: { fontSize: 30, fontWeight: '800', color: palette.ink },
  subtitle: { color: palette.muted, lineHeight: 20 },
  sectionHeading: { gap: 6, marginTop: 4 },
  sectionTitle: { color: palette.ink, fontSize: 22, fontWeight: '700' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  tile: {
    minHeight: 156, paddingHorizontal: 8, paddingVertical: 16,
    justifyContent: 'center', alignItems: 'center', gap: 10,
    backgroundColor: '#fff', borderRadius: 20,
    borderWidth: 2, borderColor: palette.border,
    boxShadow: '0 4px 0 #d8e3ef',
  },
  tilePressed: { backgroundColor: '#eef4fb', borderColor: '#9cb3d0', transform: [{ scale: 0.98 }] },
  tileDisabled: { opacity: 0.45 },
  tileTitle: { color: '#082957', textAlign: 'center', fontSize: 14, fontWeight: '700', lineHeight: 18 },
});
