import { useState } from 'react';
import { Text, View } from 'react-native';
import { Squad } from '../types/game';
import { squadService } from '../services/squadService';
import { useSquadStore } from '../stores/squadStore';
import { ComboBox } from './ComboBox';
import { Card, NotificationBubble, palette, useAction } from './GameUI';
const unavailable = (status?: string) => ['injured', 'suspended', 'retired'].includes(status || '');
const sector = (position: string) => position === 'GK' ? 'GOL' : ['CB', 'FB'].includes(position) ? 'DEF' : position === 'MID' ? 'MED' : position === 'ATT' ? 'ATA' : position;
export function LineupEditor({ squad, formation }: { squad: Squad; formation: string }) {
  const [starters, setStarters] = useState(squad.lineup.starters.filter(id => squad.players.some(player => player.id === id && !unavailable(player.status))));
  const action = useAction();
  const selected = squad.players.filter(player => starters.includes(player.id));
  return <Card>
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
    {['GOL', ...Object.keys(squad.formations[formation] ?? {})].flatMap(group => {
      const count = group === 'GOL' ? 1 : squad.formations[formation][group];
      const current = selected.filter(player => sector(player.position) === group);
      return Array.from({ length: count }, (_, index) => {
        const player = current[index];
        return <ComboBox key={`${group}-${index}`} label={`${group} ${index + 1}`} value={player?.id ?? ''} disabled={action.busy}
          options={squad.players.filter(candidate => sector(candidate.position) === group && !unavailable(candidate.status) && (!starters.includes(candidate.id) || candidate.id === player?.id)).map(candidate => ({ value: candidate.id, label: `${candidate.name} · ${candidate.strength ?? candidate.overall}` }))}
          onChange={identity => {
            const next = player ? starters.map(id => id === player.id ? identity : id) : [...starters, identity];
            setStarters(next);
            if (next.length === 11) void action.run(async () => {
              await squadService.save({ formation, starters: next, reserves: squad.players.filter(candidate => !next.includes(candidate.id) && !unavailable(candidate.status)).map(candidate => candidate.id) });
              await useSquadStore.getState().load();
            });
          }} />;
      });
    })}

  </Card>;
}
