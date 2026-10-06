import { ActionButton as Button } from './GameUI';
import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';
import { liveMatchService } from '../services/liveMatchService';
export function UpcomingMatches({ open }: { open: (id: string) => void }) {
  const [matches, setMatches] = useState<{ id: string; round?: number; date: string; status: string }[]>([]);
  useEffect(() => { let active = true; void liveMatchService.upcoming().then(rows => { if (active) setMatches(rows); }).catch(() => {}); return () => { active = false; }; }, []);
  return <View>{matches.slice(0, 2).map(m => <View key={m.id}><Text>{m.round ? `Rodada ${m.round}` : 'Amistoso'} · {new Date(m.date).toLocaleString('pt-BR')}</Text><Button title={m.status === 'live' ? 'Acompanhar partida em andamento' : 'Abrir acompanhamento da partida'} onPress={() => open(m.id)} /></View>)}</View>;
}
