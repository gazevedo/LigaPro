import { useEffect } from 'react';
import { AppState, Text, View } from 'react-native';
import { useUpcomingMatchesStore } from '../stores/screenStores';
import { ActionButton, palette } from './GameUI';

export function UpcomingMatches({ open }: { open: (id: string) => void }) {
  const { data: matches, ensure, refresh } = useUpcomingMatchesStore();
  useEffect(() => {
    function load() {
      if (AppState.currentState === 'background' || AppState.currentState === 'inactive') return;
      void refresh();
    }
    void ensure();
    // The server decides when a match starts; the clock alone must not enable watching.
    const timer = setInterval(load, 30000);
    const subscription = AppState.addEventListener('change', state => { if (state === 'active') load(); });
    return () => { clearInterval(timer); subscription.remove(); };
  }, [ensure, refresh]);
  const ordered = [...(matches || [])].sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
  const match = ordered.find(item => item.status === 'live') || ordered.find(item => item.status === 'scheduled');
  const live = match?.status === 'live';
  return <View style={{ gap: 10 }}>
    {match ? <>
      <Text numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.8} style={{ color: live ? palette.primary : palette.ink, fontWeight: '700', fontSize: 15 }}>{live ? 'Partida em andamento' : 'Próxima partida'}</Text>
      <Text numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.7} style={{ color: palette.muted, fontSize: 12 }}>{match.round ? `Rodada ${match.round}` : 'Partida'} · {new Date(match.date).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}</Text>
      {live && <ActionButton title="Assistir" onPress={() => open(match.id)} />}
    </> : matches !== null && <Text style={{ color: palette.muted }}>Nenhuma partida agendada.</Text>}
  </View>;
}
