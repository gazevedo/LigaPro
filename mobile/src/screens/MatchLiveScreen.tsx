import { useEffect, useRef, useState } from 'react';
import { Button, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { Choices, GamePage } from '../components/GameUI';
import { LiveEvent, LiveMessage, LiveState, liveMatchService } from '../services/liveMatchService';
export function MatchLiveScreen({ route, navigation }: NativeStackScreenProps<RootStackParamList, 'MatchLive'>) {
  const [state, setState] = useState<LiveState | null>(null), [error, setError] = useState(''), [connected, setConnected] = useState(false), [clock, setClock] = useState(0), [overlay, setOverlay] = useState('');
  const [formation, setFormation] = useState('4-4-2'), [style, setStyle] = useState('balanced'), [marking, setMarking] = useState('light'), [focus, setFocus] = useState('normal');
  const [outgoing, setOutgoing] = useState(''), [incoming, setIncoming] = useState(''), [notice, setNotice] = useState('');
  const socket = useRef<WebSocket | null>(null), counter = useRef(0), initialized = useRef(false);
  useEffect(() => {
    let mounted = true, retry: ReturnType<typeof setTimeout> | undefined, overlayTimer: ReturnType<typeof setTimeout> | undefined;
    const receiveState = (data: LiveState) => {
      if (!mounted) return;
      setState(data); setClock(data.current_minute);
      if (data.own_team && !initialized.current) { initialized.current = true; setFormation(data.own_team.formation); setStyle(data.own_team.style); setMarking(data.own_team.marking); setFocus(data.own_team.attack_focus); }
      if (data.status === 'finished') navigation.replace('MatchReport', { id: route.params.id });
    };
    function open() {
      if (!mounted) return;
      try {
        const ws = liveMatchService.connect(route.params.id); socket.current = ws;
        ws.onopen = () => { if (mounted) { setConnected(true); setError(''); ws.send(JSON.stringify({ type: 'join' })); } };
        ws.onmessage = event => {
          if (!mounted) return;
          const message = JSON.parse(String(event.data)) as LiveMessage;
          if (['match_state', 'sync', 'halftime', 'match_finished', 'participant_connected', 'participant_disconnected'].includes(message.type)) receiveState(message.data as LiveState);
          else if (message.type === 'match_event') {
            const e = message.data as LiveEvent;
            setState(current => current && current.events.some(old => old.sequence === e.sequence) ? current : current ? { ...current, events: [...current.events, e].slice(-40) } : current);
            if (['goal', 'red_card', 'injury', 'penalty_awarded'].includes(e.type)) { setOverlay(e.narration); if (overlayTimer) clearTimeout(overlayTimer); overlayTimer = setTimeout(() => { if (mounted) setOverlay(''); }, 3000); }
          } else if (message.type === 'command_rejected') { setError((message.data as { reason?: string }).reason ?? 'O comando foi rejeitado.'); }
          else if (message.type === 'command_applied') setNotice('Comando aplicado.');
          else if (message.type === 'command_pending') setNotice('Comando aguardando o próximo bloco.');
        };
        ws.onerror = () => { if (mounted) setError('Conexão interrompida. A partida continua no servidor.'); };
        ws.onclose = event => {
          if (!mounted) return;
          setConnected(false);
          if (event.code === 1008) { setError('Sessão expirada ou partida de outro clube.'); return; }
          retry = setTimeout(open, 1500);
        };
      } catch (reason) { if (mounted) setError(reason instanceof Error ? reason.message : 'Falha na conexão.'); }
    }
    open();
    const heartbeat = setInterval(() => { if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ type: 'heartbeat' })); }, 15000);
    return () => { mounted = false; clearInterval(heartbeat); if (retry) clearTimeout(retry); if (overlayTimer) clearTimeout(overlayTimer); socket.current?.close(); socket.current = null; };
  }, [route.params.id, navigation]);
  useEffect(() => {
    if (!state) return;
    const update = () => {
      const elapsed = Math.max(0, Date.now() - new Date(state.updated_at).getTime()) / 1000;
      const stop = state.current_minute < 45 ? 45 : state.status === 'extra_time' ? 120 : 90;
      setClock(state.paused || ['not_started', 'finished'].includes(state.status) ? state.current_minute : Math.min(stop, state.current_minute + 5, state.current_minute + elapsed * state.simulation_speed));
    };
    const timer = setInterval(update, 250); return () => clearInterval(timer);
  }, [state]);
  function send(type: string, payload?: Record<string, string>, speed?: number) {
    if (socket.current?.readyState !== WebSocket.OPEN) { setError('Aguarde a reconexão para enviar o comando.'); return; }
    counter.current += 1;
    setError(''); socket.current.send(JSON.stringify({ type, ...(payload ? { payload, command_id: liveMatchService.commandId(counter.current) } : {}), ...(speed ? { speed } : {}) }));
  }
  const team = state?.own_team;
  const enabled = connected && !!state && !['not_started', 'finished'].includes(state.status);
  return <GamePage loading={!state && !error} error={error}>
    <Text>{connected ? 'Ao vivo' : 'Reconectando'} · {state?.connected_users ?? 0} técnico(s) acompanhando</Text>
    {state && <>
      <Text style={{ fontSize: 24 }}>{state.home_name} {state.home_score} × {state.away_score} {state.away_name}</Text>
      <Text>{Math.floor(clock)}′ {String(Math.floor((clock % 1) * 60)).padStart(2, '0')}″ · {({not_started: 'Aguardando início', first_half: 'Primeiro tempo', halftime: 'Intervalo', second_half: 'Segundo tempo', extra_time: 'Prorrogação', penalties: 'Pênaltis', finished: 'Fim de jogo'} as Record<string, string>)[state.status] ?? state.status}{state.paused ? ' · Pausado' : ''}</Text>
      {!!overlay && <Text accessibilityRole="alert" style={{ fontSize: 20, fontWeight: 'bold' }}>{overlay}</Text>}
      <Text>Posse: {state.home_possession.toFixed(0)}% × {state.away_possession.toFixed(0)}% · Ataques: {state.home_attacks} × {state.away_attacks}</Text>
      <Text>Chances: {state.home_chances} × {state.away_chances} · Chutes: {state.home_shots} × {state.away_shots} · No alvo: {state.home_shots_on_target} × {state.away_shots_on_target}</Text>
      <Text>Faltas: {state.home_fouls} × {state.away_fouls} · Amarelos: {state.home_yellow_cards} × {state.away_yellow_cards} · Vermelhos: {state.home_red_cards} × {state.away_red_cards}</Text>
      <Text>Pressão recente: {Object.values(state.match_momentum).join(' × ')}</Text>
      <Text>Narração</Text>{state.events.map(e => <Text key={e.sequence}>{e.narration}</Text>)}
      <View style={{ flexDirection: 'row', gap: 8 }}>{[1, 2, 4].map(speed => <Button key={speed} title={`${speed}×`} disabled={!enabled || (state.human_vs_human && speed !== 1)} onPress={() => send('set_speed', undefined, speed)} />)}</View>
      <Button title={state.paused ? 'Continuar' : 'Pausa tática (15 s)'} disabled={!enabled} onPress={() => send(state.paused ? 'resume' : 'pause_request')} />
      <Button title="Ir para o intervalo" disabled={!enabled || state.current_minute >= 45 || (state.human_vs_human && state.connected_users > 1)} onPress={() => send('skip_to_halftime')} />
      <Button title="Ir para o final" disabled={!enabled || (state.human_vs_human && state.connected_users > 1)} onPress={() => send('skip_to_end')} />
      {team && <><Text>Tática do seu clube · {team.formation} · {team.style} · {team.marking} · {team.attack_focus}</Text>
        <Choices values={['4-4-2', '4-3-3', '5-3-2', '3-5-2']} value={formation} onChange={setFormation} disabled={!enabled} />
        <Choices values={['balanced', 'all_out_attack', 'counter_attack']} value={style} onChange={setStyle} disabled={!enabled} />
        <Choices values={['light', 'heavy', 'very_heavy']} value={marking} onChange={setMarking} disabled={!enabled} />
        <Choices values={['normal', 'center', 'wings']} value={focus} onChange={setFocus} disabled={!enabled} />
        <Button title="Aplicar mudanças táticas" disabled={!enabled} onPress={() => send('combined_change', { formation, play_style: style, marking, attack_focus: focus })} />
        <Text>Titulares · escolha quem sai · {team.substitutions_used}/5 substituições</Text>{team.lineup.map(p => <Button key={p.id} disabled={!enabled || (p.dismissed && !p.injured)} title={`${outgoing === p.id ? '✓ ' : ''}${p.name} · ${p.assigned_position} · Energia ${Math.round(p.energy)} · Condição ${Math.round(p.physical_condition)} · ${p.yellow_cards} amarelo(s)${p.injured ? ' · Lesionado' : ''}${p.dismissed && !p.injured ? ' · Expulso' : ''}`} onPress={() => setOutgoing(p.id)} />)}
        <Text>Banco · escolha quem entra</Text>{team.reserves.map(p => <Button key={p.id} disabled={!enabled || p.injured} title={`${incoming === p.id ? '✓ ' : ''}${p.name} · ${p.position} · Energia ${Math.round(p.energy)} · Condição ${Math.round(p.physical_condition)}`} onPress={() => setIncoming(p.id)} />)}
        <Button title="Confirmar substituição" disabled={!enabled || !outgoing || !incoming || team.substitutions_used >= 5} onPress={() => { send('substitution', { out_player_id: outgoing, in_player_id: incoming }); setOutgoing(''); setIncoming(''); }} />
      </>}
      {!!notice && <Text>{notice}</Text>}
    </>}
    <Button title="Voltar ao calendário" onPress={() => navigation.navigate('Calendar')} />
  </GamePage>;
}
