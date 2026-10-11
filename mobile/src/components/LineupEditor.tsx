import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { Badge, Player, Squad } from '../types/game';
import { squadService } from '../services/squadService';
import { useSquadStore } from '../stores/squadStore';
import { useClubStore } from '../stores/clubStore';
import { arrangePlayers, positionSector } from './formation';
import { NotificationBubble, palette, useAction } from './GameUI';
const unavailable = (status?: string) => ['injured', 'suspended', 'retired'].includes(status || '');
const sector = positionSector;
function Shirt({ badge, goalkeeper = false }: { badge?: Badge; goalkeeper?: boolean }) {
  const primary = badge?.color ?? '#087f67', accent = badge?.accent ?? '#ffffff';
  const color = goalkeeper ? accent : primary;
  const trim = goalkeeper ? primary : accent;
  return <View accessible={false} style={{ width: 32, height: 30, alignItems: 'center' }}>
    <View style={{ position: 'absolute', top: 3, width: 32, height: 11, backgroundColor: color, borderRadius: 3 }} />
    <View style={{ width: 20, height: 24, backgroundColor: color, borderRadius: 3, overflow: 'hidden' }}>
      {badge?.pattern !== 'plain' && <View style={{ position: 'absolute', top: 0, bottom: 0, left: 8, width: 4, backgroundColor: trim }} />}
      {badge?.pattern === 'cross' && <View style={{ position: 'absolute', top: 8, left: 0, right: 0, height: 4, backgroundColor: trim }} />}
    </View>
    <View style={{ width: 18, height: 6, backgroundColor: trim }} />
  </View>;
}
function PlayerMarker({ player, badge, position, outOfPosition = false }: { player: Player; badge?: Badge; position?: string; outOfPosition?: boolean }) {
  return <>
    <Shirt badge={badge} goalkeeper={sector(position ?? player.position) === 'GOL'} />
    <Text numberOfLines={1} style={styles.playerName}>{player.name}</Text>
    <Text style={styles.playerEnergy}>{sector(position ?? player.position)} · {player.energy ?? player.physical_condition ?? 100}%</Text>
    {outOfPosition && <Text accessibilityLabel={`${player.name}: fora de posição, natural ${sector(player.position)}, escalado em ${sector(position ?? player.position)}`} style={{ color: '#ffe386', fontSize: 9 }}>⚠ {sector(player.position)} → {sector(position ?? player.position)}</Text>}
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
export function LineupEditor({ squad, formation, disabled = false }: { squad: Squad; formation: string; disabled?: boolean }) {
  const badge = useClubStore(state => state.data?.club?.badge);
  const { width } = useWindowDimensions();
  const [starters, setStarters] = useState(() => arrangePlayers(squad.lineup.starters.map(id => squad.players.find(player => player.id === id)).filter((player): player is Player => !!player && !unavailable(player.status)), formation, !!squad.lineup.manual_positions && squad.lineup.formation === formation).map(slot => slot.player.id));
  const [replacement, setReplacement] = useState<string | null>(null);
  const [reserveIds, setReserveIds] = useState(squad.lineup.reserves.filter(id => squad.players.some(player => player.id === id && !unavailable(player.status))));
  const action = useAction();
  const saving = action.busy || disabled;
  const selected = starters.map(id => squad.players.find(player => player.id === id)).filter((player): player is Player => !!player);
  const reserves = [...reserveIds, ...squad.players.filter(player => !starters.includes(player.id) && !reserveIds.includes(player.id) && !unavailable(player.status)).map(player => player.id)].map(id => squad.players.find(player => player.id === id)).filter((player): player is Player => !!player);
  const target = squad.players.find(player => player.id === replacement);
  const canSwap = (player: Player) => !target || (!starters.includes(target.id) && !starters.includes(player.id)) || (sector(target.position) === 'GOL') === (sector(player.position) === 'GOL');
  function tap(player: Player) {
    if (saving || unavailable(player.status) || !canSwap(player)) return;
    if (!target) { setReplacement(player.id); return; }
    if (target.id === player.id) { setReplacement(null); return; }
    replace(target, player.id);
  }
  const assigned = arrangePlayers(selected, formation, true);
  const improvisedIds = new Set(assigned.filter(slot => slot.outOfPosition).map(slot => slot.player.id));
  const groups = ['ATA', 'MED', 'DEF', 'GOL'].flatMap(group => {
    const players = assigned.filter(slot => sector(slot.position) === group);
    if (group !== 'MED') return [players];
    const midfieldRows = formation.split('-').slice(1, -1).map(Number);
    if (midfieldRows.length > 1) {
      let offset = 0;
      return midfieldRows.map(count => { const row = players.slice(offset, offset + count); offset += count; return row; }).reverse();
    }
    return players.length >= 4 ? [players.slice(0, Math.ceil(players.length / 2)), players.slice(Math.ceil(players.length / 2))] : [players];
  });
  function replace(player: Player, identity: string) {
    if (saving) return;
    const previous = starters;
    const previousReserves = reserves.map(item => item.id);
    const swap = (id: string) => id === player.id ? identity : id === identity ? player.id : id;
    const next = starters.map(swap);
    const nextReserves = previousReserves.map(swap);
    setStarters(next); setReserveIds(nextReserves); setReplacement(null);
    if (next.length === 11) void action.run(async () => {
      try {
        await squadService.save({ formation, starters: next, reserves: nextReserves, manual_positions: true });
        await useSquadStore.getState().load();
      } catch (error) { setStarters(previous); setReserveIds(previousReserves); throw error; }
    });
  }
  return <View style={{ gap: 12 }}>
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
          <View style={styles.positions}>{groups.map((players, index) => <View key={index} accessibilityLabel={`Linha ${players.length ? sector(players[0].position) : "vazia"}: ${players.length} jogadores`} style={styles.row}>
            {players.map(({ player, position, outOfPosition }) => <Pressable key={player.id} accessibilityRole="button" accessibilityLabel={`Substituir ${player.name}`} disabled={saving} onPress={() => tap(player)} style={[styles.marker, replacement === player.id && styles.activeMarker]}>
              <PlayerMarker player={player} badge={badge} position={position} outOfPosition={outOfPosition} />
            </Pressable>)}
          </View>)}</View>
        </View>
        <View style={{ width: 68, gap: 10, alignItems: 'center' }}>
          <Text style={{ color: '#fff', fontWeight: '700', fontSize: 11 }}>Reservas</Text>
          <ScrollView style={{ maxHeight: 450 }} contentContainerStyle={{ gap: 12 }}>
            {reserves.map(player => <Pressable key={player.id} accessibilityRole="button" accessibilityLabel={`Reserva ${player.name}`} disabled={saving || !canSwap(player)} onPress={() => tap(player)} style={[styles.marker, replacement === player.id && styles.activeMarker]}><PlayerMarker player={player} badge={badge} /></Pressable>)}
          </ScrollView>
        </View>
      </View>
      <View style={{ flex: width >= 720 ? 2 : undefined, gap: 12 }}>
        <View style={styles.roster}>
          <View style={styles.rosterRow}><Text style={styles.role}>T/R</Text><Text style={styles.position}>Pos.</Text><Text style={[styles.rosterName, { fontWeight: '700' }]}>Nome</Text><Text style={styles.number}>Força</Text><Text style={styles.number}>Energia</Text></View>
          <ScrollView style={{ maxHeight: 310 }}>
            {squad.players.map(player => <Pressable key={player.id} accessibilityRole="button" accessibilityLabel={`${player.name}, ${starters.includes(player.id) ? 'titular' : 'reserva'}, força ${player.strength ?? player.overall}`} disabled={saving || unavailable(player.status) || !canSwap(player)} onPress={() => tap(player)} style={[styles.rosterRow, { backgroundColor: improvisedIds.has(player.id) || replacement === player.id ? '#fff1b8' : starters.includes(player.id) ? '#e1efdb' : '#fff', opacity: unavailable(player.status) ? 0.45 : 1 }]}>
              <Text style={styles.role}>{starters.includes(player.id) ? 'T' : reserves.some(item => item.id === player.id) ? 'R' : '—'}</Text><Text style={styles.position}>{sector(player.position)}</Text><Text numberOfLines={1} style={styles.rosterName}>{player.name}</Text><PlayerCards player={player} /><Text style={styles.number}>{player.strength ?? player.overall}</Text><Text style={styles.number}>{player.energy ?? player.physical_condition ?? 100}%</Text>
            </Pressable>)}
          </ScrollView>
        </View>
      </View>
    </View>
    <Text style={{ color: palette.muted, fontSize: 12 }}>Toque em dois jogadores para trocar. T: titular · R: reserva. Fora de posição: atributos −20% em campo.</Text>
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
