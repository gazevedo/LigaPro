import { useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { ActionButton as Button, Choices, GamePage, NotificationBubble, palette } from '../components/GameUI';
import { LiveState, liveMatchService } from '../services/liveMatchService';
export function MatchLiveScreen({ route, navigation }: NativeStackScreenProps<RootStackParamList, 'MatchLive'>) {
  const [state, setState] = useState<LiveState | null>(null), [error, setError] = useState(''), [connected, setConnected] = useState(false), [clock, setClock] = useState(0);
  const [formation, setFormation] = useState('4-4-2'), [style, setStyle] = useState('balanced'), [marking, setMarking] = useState('light'), [focus, setFocus] = useState('normal');
  const [outgoing, setOutgoing] = useState(''), [incoming, setIncoming] = useState(''), [notice, setNotice] = useState('');
  const counter = useRef(0), initialized = useRef(false);
  useEffect(() => {
    let mounted = true, pending = false;
    initialized.current = false;
    async function update() {
      if (pending) return;
      pending = true;
      try {
        const data = await liveMatchService.state(route.params.id);
        if (!mounted) return;
        setState(data); setClock(data.current_minute); setConnected(true); setError('');
        if (data.own_team && !initialized.current) {
          initialized.current = true;
          setFormation(data.own_team.formation); setStyle(data.own_team.style);
          setMarking(data.own_team.marking); setFocus(data.own_team.attack_focus);
        }
        if (data.status === 'finished') navigation.replace('MatchReport', { id: route.params.id });
      } catch (reason) {
        if (mounted) { setConnected(false); setError(reason instanceof Error ? reason.message : 'Falha ao atualizar a partida.'); }
      } finally { pending = false; }
    }
    void update();
    const timer = setInterval(() => { void update(); }, 2000);
    return () => { mounted = false; clearInterval(timer); };
  }, [route.params.id, navigation]);
  useEffect(() => {
    if (!state) return;
    const update = () => {
      const elapsed = Math.max(0, Date.now() - new Date(state.updated_at).getTime()) / 1000;
      const stop = state.status === 'extra_time' ? 120 : 90;
      setClock(state.paused || ['not_started', 'finished'].includes(state.status) ? state.current_minute : Math.min(stop, state.current_minute + 5, state.current_minute + elapsed / (state.real_seconds_per_game_minute ?? (300 / 90))));
    };
    const timer = setInterval(update, 250); return () => clearInterval(timer);
  }, [state]);
  async function send(type: string, payload: Record<string, string>) {
    counter.current += 1;
    setError('');
    try {
      await liveMatchService.command(route.params.id, type === 'substitution' ? 'substitution' : 'combined_change', payload, liveMatchService.commandId(counter.current));
      setNotice('Comando aguardando o próximo lance.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Falha ao enviar o comando.'); }
  }
  const team = state?.own_team;
  const enabled = connected && !!state && !['not_started', 'finished'].includes(state.status);
  return <GamePage loading={!state && !error} error={error}>
    <Text style={{ fontSize: 20, fontWeight: '800', color: palette.ink }}>Acompanhamento da partida</Text>
    <Text style={{ color: palette.muted }}>{connected ? 'Ao vivo' : 'Atualizando partida'} · Duração: 5 minutos</Text>
    {state && <>
      <View style={{ backgroundColor: '#123d32', borderRadius: 16, padding: 20, gap: 12 }}>
        <Text style={{ fontSize: 24, color: '#fff', fontWeight: '800', textAlign: 'center' }}>{state.home_name} {state.home_score} × {state.away_score} {state.away_name}</Text>
        <View accessibilityRole="progressbar" accessibilityLabel="Tempo da partida" accessibilityValue={{ min: 0, max: 90, now: Math.min(90, Math.floor(clock)) }} style={{ height: 6, backgroundColor: '#376358', borderRadius: 3 }}><View style={{ height: 6, borderRadius: 3, backgroundColor: '#6ee7a4', width: `${Math.min(100, clock / 90 * 100)}%` }} /></View>
      </View>
      <Text>{Math.floor(clock)}′ {String(Math.floor((clock % 1) * 60)).padStart(2, '0')}″ · {({not_started: 'Aguardando início', first_half: 'Primeiro tempo', halftime: 'Intervalo', second_half: 'Segundo tempo', extra_time: 'Prorrogação', penalties: 'Pênaltis', finished: 'Fim de jogo'} as Record<string, string>)[state.status] ?? state.status}{state.paused ? ' · Pausado' : ''}</Text>
      <Text>Posse: {state.home_possession.toFixed(0)}% × {state.away_possession.toFixed(0)}% · Ataques: {state.home_attacks} × {state.away_attacks}</Text>
      <Text>Chances: {state.home_chances} × {state.away_chances} · Chutes: {state.home_shots} × {state.away_shots} · No alvo: {state.home_shots_on_target} × {state.away_shots_on_target}</Text>
      <Text>Faltas: {state.home_fouls} × {state.away_fouls} · Amarelos: {state.home_yellow_cards} × {state.away_yellow_cards} · Vermelhos: {state.home_red_cards} × {state.away_red_cards}</Text>
      <Text>Pressão recente: {Object.values(state.match_momentum).join(' × ')}</Text>
      <Text>Narração</Text>{[...state.events].reverse().map(e => <Text key={e.sequence} style={{ paddingVertical: 8, color: e.type === 'goal' ? palette.primary : palette.ink, fontWeight: e.type === 'goal' ? '800' : '400' }}>{e.narration}</Text>)}
      {team && <><Text>Tática do seu clube · {team.formation} · {team.style} · {team.marking} · {team.attack_focus}</Text>
        <Choices values={['4-4-2', '4-3-3', '5-3-2', '3-5-2']} value={formation} onChange={setFormation} disabled={!enabled} />
        <Choices values={['balanced', 'all_out_attack', 'counter_attack']} value={style} onChange={setStyle} disabled={!enabled} />
        <Choices values={['light', 'heavy', 'very_heavy']} value={marking} onChange={setMarking} disabled={!enabled} />
        <Choices values={['normal', 'center', 'wings']} value={focus} onChange={setFocus} disabled={!enabled} />
        <Button title="Aplicar mudanças táticas" disabled={!enabled} onPress={() => void send('combined_change', { formation, play_style: style, marking, attack_focus: focus })} />
        <Text>Titulares · escolha quem sai · {team.substitutions_used}/3 substituições</Text>{team.lineup.map(p => <Button key={p.id} disabled={!enabled || (p.dismissed && !p.injured)} title={`${outgoing === p.id ? '✓ ' : ''}${p.name} · ${p.assigned_position} · Energia ${Math.round(p.energy)} · Condição ${Math.round(p.physical_condition)} · ${p.yellow_cards} amarelo(s)${p.injured ? ' · Lesionado' : ''}${p.dismissed && !p.injured ? ' · Expulso' : ''}`} onPress={() => setOutgoing(p.id)} />)}
        <Text>Banco · escolha quem entra</Text>{team.reserves.map(p => <Button key={p.id} disabled={!enabled || p.injured} title={`${incoming === p.id ? '✓ ' : ''}${p.name} · ${p.position} · Energia ${Math.round(p.energy)} · Condição ${Math.round(p.physical_condition)}`} onPress={() => setIncoming(p.id)} />)}
        <Button title="Confirmar substituição" disabled={!enabled || !outgoing || !incoming || team.substitutions_used >= 3} onPress={() => { void send('substitution', { out_player_id: outgoing, in_player_id: incoming }); setOutgoing(''); setIncoming(''); }} />
      </>}
      <NotificationBubble message={notice} tone="info" />
    </>}
    <Button title="Voltar ao calendário" onPress={() => navigation.navigate('Calendar')} />
  </GamePage>;
}
