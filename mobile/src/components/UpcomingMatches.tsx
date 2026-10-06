import { useEffect, useState } from 'react';
import { AppState, Text, View } from 'react-native';
import { liveMatchService } from '../services/liveMatchService';
import { ActionButton, NotificationBubble, palette } from './GameUI';

type UpcomingMatch = Awaited<ReturnType<typeof liveMatchService.upcoming>>[number];

export function UpcomingMatches({ open }: { open: (id: string) => void }) {
  const [matches, setMatches] = useState<UpcomingMatch[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true, loading = false;
    async function load() {
      if (loading || AppState.currentState === 'background' || AppState.currentState === 'inactive') return;
      loading = true;
      try {
        const rows = await liveMatchService.upcoming();
        if (active) { setMatches(rows); setError(null); }
      } catch { if (active) setError('Não foi possível atualizar a próxima partida.'); }
      finally { loading = false; }
    }
    void load();
    // The server decides when a match starts; the clock alone must not enable watching.
    const timer = setInterval(() => { void load(); }, 30000);
    const subscription = AppState.addEventListener('change', state => { if (state === 'active') void load(); });
    return () => { active = false; clearInterval(timer); subscription.remove(); };
  }, []);
  const ordered = [...(matches || [])].sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
  const match = ordered.find(item => item.status === 'live') || ordered.find(item => item.status === 'scheduled');
  const live = match?.status === 'live';
  return <View style={{ gap: 10 }}>
    <NotificationBubble message={error} />
    {match ? <>
      <Text style={{ color: live ? palette.primary : palette.ink, fontWeight: '700', fontSize: 17 }}>{live ? 'Partida em andamento' : 'Próxima partida'}</Text>
      <Text style={{ color: palette.muted }}>{match.round ? `Rodada ${match.round}` : 'Partida'} · {new Date(match.date).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}</Text>
      {live && <ActionButton title="Assistir" onPress={() => open(match.id)} />}
    </> : matches !== null && <Text style={{ color: palette.muted }}>Nenhuma partida agendada.</Text>}
  </View>;
}
