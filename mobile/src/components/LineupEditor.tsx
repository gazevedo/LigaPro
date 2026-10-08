import { useState } from 'react';
import { Text, View } from 'react-native';
import { Squad } from '../types/game';
import { squadService } from '../services/squadService';
import { useSquadStore } from '../stores/squadStore';
import { ActionButton, Card, NotificationBubble, palette, useAction } from './GameUI';
const unavailable = (status?: string) => ['injured', 'suspended', 'retired'].includes(status || '');
const sector = (position: string) => position === 'GK' ? 'GOL' : ['CB', 'FB'].includes(position) ? 'DEF' : position === 'MID' ? 'MED' : position === 'ATT' ? 'ATA' : position;
export function LineupEditor({ squad, formation }: { squad: Squad; formation: string }) {
  const [starters, setStarters] = useState(squad.lineup.starters.filter(id => squad.players.some(player => player.id === id && !unavailable(player.status))));
  const action = useAction();
  const selected = squad.players.filter(player => starters.includes(player.id));
  return <Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Escalação</Text>
    <Text style={{ color: palette.muted }}>Titulares: {starters.length}/11 · Entrosamento: {squad.team_chemistry ?? 40}/100</Text>
    <NotificationBubble message={action.error} />
    <View style={{ backgroundColor: '#3b9b77', borderRadius: 20, borderWidth: 3, borderColor: '#bcebd3', padding: 12, gap: 18 }}>
      {['ATA', 'MED', 'DEF', 'GOL'].map(group => <View key={group} style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 10, minHeight: 60 }}>
        {selected.filter(player => sector(player.position) === group).map(player => <View key={player.id} style={{ alignItems: 'center', width: 76, gap: 4 }}>
          <View style={{ backgroundColor: '#fff4c8', width: 34, height: 34, borderRadius: 12, borderWidth: 2, borderColor: '#18364a', justifyContent: 'center', alignItems: 'center' }}><Text style={{ fontWeight: '800', color: palette.ink }}>{player.position}</Text></View>
          <Text numberOfLines={1} style={{ fontSize: 11, color: '#fff', fontWeight: '700' }}>{player.name}</Text>
        </View>)}
        {!selected.some(player => sector(player.position) === group) && <Text style={{ color: '#d9f5e7', alignSelf: 'center' }}>{group}</Text>}
      </View>)}
    </View>
    <Text style={{ color: palette.muted }}>Selecione os jogadores para a formação {formation}. Lesionados e suspensos ficam indisponíveis.</Text>
    {squad.players.map(player => <ActionButton key={player.id} secondary={!starters.includes(player.id)} disabled={action.busy || unavailable(player.status)} title={`${starters.includes(player.id) ? 'Titular' : 'Reserva'} · ${player.position} ${player.name}`} onPress={() => setStarters(ids => ids.includes(player.id) ? ids.filter(id => id !== player.id) : [...ids, player.id])} />)}
    <ActionButton title="Salvar escalação" disabled={action.busy || starters.length !== 11} onPress={() => void action.run(async () => {
      await squadService.save({ formation, starters, reserves: squad.players.filter(player => !starters.includes(player.id) && !unavailable(player.status)).map(player => player.id) });
      await useSquadStore.getState().load();
    })} />
  </Card>;
}
