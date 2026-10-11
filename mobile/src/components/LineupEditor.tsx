import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { Player, Squad } from '../types/game';
import { squadService } from '../services/squadService';
import { useSquadStore } from '../stores/squadStore';
import { NotificationBubble, palette, useAction } from './GameUI';
const unavailable = (status?: string) => ['injured', 'suspended', 'retired'].includes(status || '');
const sector = (position: string) => position === 'GK' ? 'GOL' : ['CB', 'FB'].includes(position) ? 'DEF' : position === 'MID' ? 'MED' : position === 'ATT' ? 'ATA' : position;
function Shirt({ goalkeeper = false, reserve = false }: { goalkeeper?: boolean; reserve?: boolean }) {
  const color = goalkeeper ? '#303743' : reserve ? '#e7c857' : '#288ac0';
  return <View accessible={false} style={{ width: 32, height: 30, alignItems: 'center' }}>
    <View style={{ position: 'absolute', top: 3, width: 32, height: 11, backgroundColor: color, borderRadius: 3 }} />
    <View style={{ width: 20, height: 24, backgroundColor: color, borderRadius: 3, borderBottomWidth: 3, borderBottomColor: '#e7c857' }} />
    <View style={{ width: 18, height: 6, backgroundColor: goalkeeper ? '#202630' : '#f0db78' }} />
  </View>;
}
function PlayerMarker({ player, reserve = false }: { player: Player; reserve?: boolean }) {
  return <>
    <Shirt goalkeeper={sector(player.position) === 'GOL'} reserve={reserve} />
    <Text numberOfLines={1} style={styles.playerName}>{player.name}</Text>
    <Text style={styles.playerEnergy}>{sector(player.position)} · {player.energy ?? player.physical_condition ?? 100}%</Text>
  </>;
}
function PlayerCards({ player }: { player: Player }) {
  const yellows = player.yellow_cards_accumulated || (player.discipline_yellow_suspension && (player.suspension_matches_remaining ?? 0) > 0 ? 3 : 0);
  const red = player.discipline_red_card && (player.suspension_matches_remaining ?? 0) > 0;
  return <View style={{ flexDirection: 'row', gap: 3 }}>
    {yellows > 0 && <View accessible accessibilityRole="image" accessibilityLabel={`${yellows} cartões amarelos`} style={{ backgroundColor: '#f1c232', width: 13, height: 18, borderRadius: 2, alignItems: 'center' }}><Text style={{ fontSize: 10 }}>{yellows}</Text></View>}
    {red && <View accessible accessibilityRole="image" accessibilityLabel="Cartão vermelho" style={{ backgroundColor: '#d83232', width: 13, height: 18, borderRadius: 2 }} />}
  </View>;
}
export function LineupEditor({ squad, formation }: { squad: Squad; formation: string }) {
  const { width } = useWindowDimensions();
  const [starters, setStarters] = useState(squad.lineup.starters.filter(id => squad.players.some(player => player.id === id && !unavailable(player.status))));
  const [replacement, setReplacement] = useState<string | null>(null);
  const [reserveIds, setReserveIds] = useState(squad.lineup.reserves.filter(id => squad.players.some(player => player.id === id && !unavailable(player.status))));
  const action = useAction();
  const selected = starters.map(id => squad.players.find(player => player.id === id)).filter((player): player is Player => !!player);
  const reserves = [...reserveIds, ...squad.players.filter(player => !starters.includes(player.id) && !reserveIds.includes(player.id) && !unavailable(player.status)).map(player => player.id)].map(id => squad.players.find(player => player.id === id)).filter((player): player is Player => !!player);
  const target = squad.players.find(player => player.id === replacement);
  const canSwap = (player: Player) => !target || target.id === player.id || (!starters.includes(target.id) && !starters.includes(player.id)) || sector(target.position) === sector(player.position);
  function tap(player: Player) {
    if (action.busy || unavailable(player.status) || !canSwap(player)) return;
    if (!target) { setReplacement(player.id); return; }
    if (target.id === player.id) { setReplacement(null); return; }
    replace(target, player.id);
  }
  const groups = ['ATA', 'MED', 'DEF', 'GOL'].flatMap(group => {
    const players = selected.filter(player => sector(player.position) === group);
    return group === 'MED' && players.length === 4 ? [players.slice(0, 2), players.slice(2)] : [players];
  });
  function replace(player: Player, identity: string) {
    if (action.busy) return;
    const previous = starters;
    const previousReserves = reserves.map(item => item.id);
    const swap = (id: string) => id === player.id ? identity : id === identity ? player.id : id;
    const next = starters.map(swap);
    const nextReserves = previousReserves.map(swap);
    setStarters(next); setReserveIds(nextReserves); setReplacement(null);
    if (next.length === 11) void action.run(async () => {
      try {
        await squadService.save({ formation, starters: next, reserves: nextReserves });
        await useSquadStore.getState().load();
      } catch (error) { setStarters(previous); setReserveIds(previousReserves); throw error; }
    });
  }
  return <View style={{ gap: 12 }}>
    <Text style={{ color: palette.muted, fontSize: 12 }}>Salvamento automático · Titulares: {starters.length}/11 · Entrosamento: {squad.team_chemistry ?? 40}/100</Text>
    <NotificationBubble message={action.error} />
    <View style={{ flexDirection: width >= 720 ? 'row' : 'column', gap: 12, alignItems: 'stretch' }}>
      <View style={{ flex: width >= 720 ? 3 : undefined, flexDirection: 'row', backgroundColor: '#486b21', padding: 8, gap: 6, borderRadius: 8 }}>
        <View accessibilityLabel={`Campo: formação ${formation}`} style={styles.pitch}>
          {Array.from({ length: 10 }, (_, index) => <View key={index} style={{ position: 'absolute', top: `${index * 10}%`, height: '10%', left: 0, right: 0, backgroundColor: index % 2 ? '#41681f' : '#4a7624' }} />)}
          <View pointerEvents="none" style={styles.boundary} />
          <View pointerEvents="none" style={styles.halfway} />
          <View pointerEvents="none" style={styles.circle} />
          <View pointerEvents="none" style={[styles.penalty, { top: 8 }]} />
          <View pointerEvents="none" style={[styles.penalty, { bottom: 8 }]} />
          <View pointerEvents="none" style={[styles.goalArea, { top: 8 }]} />
          <View pointerEvents="none" style={[styles.goalArea, { bottom: 8 }]} />
          <Text style={styles.formation}>{formation}</Text>
          <View style={styles.positions}>{groups.map((players, index) => <View key={index} style={styles.row}>
            {players.map(player => <Pressable key={player.id} accessibilityRole="button" accessibilityLabel={`Substituir ${player.name}`} disabled={action.busy} onPress={() => tap(player)} style={[styles.marker, replacement === player.id && styles.activeMarker]}>
              <PlayerMarker player={player} />
            </Pressable>)}
          </View>)}</View>
        </View>
        <View style={{ width: 68, gap: 10, alignItems: 'center' }}>
          <Text style={{ color: '#fff', fontWeight: '700', fontSize: 11 }}>Reservas</Text>
          <ScrollView style={{ maxHeight: 450 }} contentContainerStyle={{ gap: 12 }}>
            {reserves.map(player => <Pressable key={player.id} accessibilityRole="button" accessibilityLabel={`Reserva ${player.name}`} disabled={action.busy || !canSwap(player)} onPress={() => tap(player)} style={[styles.marker, replacement === player.id && styles.activeMarker]}><PlayerMarker player={player} reserve /></Pressable>)}
          </ScrollView>
        </View>
      </View>
      <View style={{ flex: width >= 720 ? 2 : undefined, gap: 12 }}>
        <View style={styles.roster}>
          <View style={styles.rosterRow}><Text style={styles.role}>T/R</Text><Text style={styles.position}>Pos.</Text><Text style={[styles.rosterName, { fontWeight: '700' }]}>Nome</Text><Text style={styles.number}>Força</Text><Text style={styles.number}>Energia</Text></View>
          <ScrollView style={{ maxHeight: 310 }}>
            {squad.players.map(player => <Pressable key={player.id} accessibilityRole="button" accessibilityLabel={`${player.name}, ${starters.includes(player.id) ? 'titular' : 'reserva'}, força ${player.strength ?? player.overall}`} disabled={action.busy || unavailable(player.status) || !canSwap(player)} onPress={() => tap(player)} style={[styles.rosterRow, { backgroundColor: replacement === player.id ? '#fff1b8' : starters.includes(player.id) ? '#e1efdb' : '#fff', opacity: unavailable(player.status) ? 0.45 : 1 }]}>
              <Text style={styles.role}>{starters.includes(player.id) ? 'T' : reserves.some(item => item.id === player.id) ? 'R' : '—'}</Text><Text style={styles.position}>{sector(player.position)}</Text><Text numberOfLines={1} style={styles.rosterName}>{player.name}</Text><PlayerCards player={player} /><Text style={styles.number}>{player.strength ?? player.overall}</Text><Text style={styles.number}>{player.energy ?? player.physical_condition ?? 100}%</Text>
            </Pressable>)}
          </ScrollView>
        </View>
      </View>
    </View>
    <Text style={{ color: palette.muted, fontSize: 12 }}>Toque em dois jogadores para trocar. Titulares exigem a mesma posição. T: titular · R: reserva. As alterações são salvas automaticamente.</Text>
  </View>;
}
const styles = StyleSheet.create({
  pitch: { flex: 1, height: 470, overflow: 'hidden', position: 'relative' },
  boundary: { position: 'absolute', top: 8, bottom: 8, left: 6, right: 6, borderWidth: 1, borderColor: '#dce8c3' },
  halfway: { position: 'absolute', top: '50%', left: 6, right: 6, height: 1, backgroundColor: '#dce8c3' },
  circle: { position: 'absolute', top: '40%', left: '30%', width: '40%', height: '20%', borderRadius: 100, borderWidth: 1, borderColor: '#dce8c3' },
  penalty: { position: 'absolute', left: '16%', right: '16%', height: '17%', borderWidth: 1, borderColor: '#dce8c3' },
  goalArea: { position: 'absolute', left: '32%', right: '32%', height: '7%', borderWidth: 1, borderColor: '#dce8c3' },
  formation: { position: 'absolute', top: 14, alignSelf: 'center', color: '#f6e5a2', fontSize: 16, fontWeight: '800' },
  positions: { flex: 1, paddingTop: 45, paddingBottom: 18, justifyContent: 'space-between' },
  row: { flexDirection: 'row', justifyContent: 'space-around', alignItems: 'center', minHeight: 62 },
  marker: { flexShrink: 1, width: 66, alignItems: 'center', gap: 2, paddingVertical: 3 },
  activeMarker: { backgroundColor: '#ffffff33', borderRadius: 6 },
  playerName: { color: '#fff', fontSize: 10, fontWeight: '700', maxWidth: '100%' },
  playerEnergy: { color: '#edf3de', fontSize: 9 },
  roster: { borderWidth: 1, borderColor: '#b5c9a2', backgroundColor: '#fff', borderRadius: 6, overflow: 'hidden' },
  rosterRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 6, paddingVertical: 6, borderBottomWidth: 1, borderColor: '#edf1e8', gap: 4 },
  role: { width: 22, fontSize: 11, fontWeight: '800', color: palette.primary },
  position: { width: 30, fontSize: 11, color: palette.ink },
  rosterName: { flex: 1, fontSize: 12, color: palette.ink },
  number: { width: 42, textAlign: 'right', fontSize: 11, color: palette.ink },
});
