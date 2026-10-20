import { Text, View } from 'react-native';
import { Player } from '../types/game';
import { palette } from './GameUI';
import { PlayerStars } from './PlayerStars';
export function PlayerRosterHeader({ compact, trailing }: { compact: boolean; trailing: string }) {
  return <View style={{ flexDirection: 'row', gap: 6 }}><Text style={{ width: 42, fontSize: 12 }}>Camisa</Text><Text style={{ width: 28, fontSize: 12 }}>Pos.</Text><Text style={{ flex: 1, minWidth: 0, fontWeight: '700' }}>Nome</Text>{!compact && <><Text style={{ width: 36 }}>Idade</Text><Text style={{ width: 40 }}>Força</Text><Text style={{ width: 65 }}>Estrelas</Text></>}<Text style={{ width: 56, fontSize: 12 }}>{trailing}</Text></View>;
}
export function PlayerRosterCells({ player, compact }: { player: Player; compact: boolean }) {
  return <><Text style={{ width: 28, fontSize: 12 }}>{({ GK: 'GOL', CB: 'ZAG', FB: 'LAT', MID: 'MED', ATT: 'ATA' } as Record<string, string>)[player.position] ?? player.position}</Text><View style={{ flex: 1, minWidth: 0, gap: 4 }}><Text numberOfLines={2} style={{ color: palette.ink, fontWeight: '600' }}>{player.name}</Text>{compact && <Text style={{ color: palette.muted, fontSize: 11 }}>{player.age} anos · Força {player.strength ?? player.overall} · ★ {player.stars ?? 0}</Text>}</View>{!compact && <><Text style={{ width: 36 }}>{player.age}</Text><Text style={{ width: 40 }}>{player.strength ?? player.overall}</Text><View style={{ width: 65 }}><PlayerStars count={player.stars} /></View></>}</>;
}
