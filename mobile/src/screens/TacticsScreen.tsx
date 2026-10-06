import { useEffect, useState } from 'react';
import { Text } from 'react-native';
import { ActionButton as Button, Choices, Field, GamePage, useAction } from '../components/GameUI';
import { tacticsService, Tactics, PlannedMatch } from '../services/tacticsService';
import { useTacticsStore } from '../stores/tacticsStore';
import { useSquadStore } from '../stores/squadStore';
import { useClubStore } from '../stores/clubStore';

const styles = { balanced: 'Equilibrado', all_out_attack: 'Ataque total', counter_attack: 'Contra-ataque' };
const markings = { light: 'Leve', heavy: 'Pesada', very_heavy: 'Muito pesada' };
const focuses = { normal: 'Normal', center: 'Centro', wings: 'Laterais' };
function Selector<T extends string>({ labels, value, change }: { labels: Record<T, string>; value: T; change: (value: T) => void }) {
  return <Choices values={Object.values<string>(labels)} value={labels[value]} onChange={label => change((Object.keys(labels) as T[]).find(key => labels[key] === label)!)} />;
}
export function TacticsScreen() {
  const store = useTacticsStore(), squad = useSquadStore(), action = useAction();
  const clubId = useClubStore(state => state.data?.club?.id);
  const [draftOverride, setDraft] = useState<Tactics | null>(null), [matches, setMatches] = useState<PlannedMatch[]>([]);
  const [matchId, setMatchId] = useState(''), [minute, setMinute] = useState('60');
  const [outId, setOutId] = useState(''), [inId, setInId] = useState(''), [message, setMessage] = useState('');
  const load = store.load, loadSquad = squad.load;
  useEffect(() => { void load(); void loadSquad(); }, [load, loadSquad]);

  useEffect(() => { let active = true; void tacticsService.matches().then(data => { if (active) setMatches(data); }).catch(() => { if (active) setMessage('Não foi possível carregar as partidas.'); }); return () => { active = false; }; }, [clubId]);
  const draft = draftOverride ?? (store.data ? { formation: store.data.formation, play_style: store.data.play_style, marking: store.data.marking, attack_focus: store.data.attack_focus } : null);
  const scheduled = matches.filter(match => match.status === 'scheduled');
  const selected = scheduled.find(match => match.id === matchId);
  async function plan(type: 'tactics_change' | 'substitution') {
    if (!draft || !selected) throw new Error('Selecione uma partida.');
    if (!/^\d+$/.test(minute) || Number(minute) > 85) throw new Error('Informe um minuto de 0 a 85.');
    if (type === 'substitution' && (!outId || !inId)) throw new Error('Selecione quem sai e quem entra.');
    const commands = await tacticsService.command(selected.id, { minute: Number(minute), type, payload: type === 'tactics_change' ? { ...draft } : { out_player_id: outId, in_player_id: inId } });
    setMatches(items => items.map(item => item.id === selected.id ? { ...item, commands: commands as PlannedMatch['commands'] } : item));
    setOutId(''); setInId(''); setMessage('Comando programado.');
  }
  const starters = new Set(squad.data?.lineup.starters ?? []), reserves = new Set(squad.data?.lineup.reserves ?? []);
  for (const command of [...(selected?.commands ?? [])].filter(c => c.team_id === clubId).sort((a, b) => a.minute - b.minute)) {
    if (command.type === 'substitution' && command.minute <= Number(minute)) { starters.delete(command.payload.out_player_id); starters.add(command.payload.in_player_id); reserves.delete(command.payload.in_player_id); }
  }
  return <GamePage loading={store.loading || squad.loading || action.busy} error={action.error || store.error || squad.error}>
    {draft && <>
      <Text>Formação</Text><Choices values={Object.keys(squad.data?.formations ?? {})} value={draft.formation} onChange={formation => setDraft({ ...draft, formation })} />
      <Text>Estilo de jogo</Text><Selector labels={styles} value={draft.play_style} change={play_style => setDraft({ ...draft, play_style })} />
      <Text>Equilibrado mantém os setores. Ataque total cria mais, mas expõe a defesa. Contra-ataque aproveita as transições.</Text>
      <Text>Marcação</Text><Selector labels={markings} value={draft.marking} change={marking => setDraft({ ...draft, marking })} />
      <Text>Marcação mais pesada contém mais ataques, mas aumenta faltas e cartões e dificulta a saída de bola.</Text>
      <Text>Foco dos ataques</Text><Selector labels={focuses} value={draft.attack_focus} change={attack_focus => setDraft({ ...draft, attack_focus })} />
      <Text>Centro e laterais direcionam aproximadamente 70% dos ataques. A formação adapta os titulares atuais.</Text>
      <Button disabled={action.busy} title="Salvar tática do clube" onPress={() => void action.run(async () => { await tacticsService.save(draft); await load(); await loadSquad(); setDraft(null); setMessage('Tática salva.'); })} />
      <Text>Plano de partida</Text><Text>Os comandos serão executados durante a simulação, mesmo offline, no próximo bloco de cinco minutos. Eles afetam somente os blocos seguintes.</Text>
      {scheduled.map(match => <Button key={match.id} title={`${matchId === match.id ? '✓ ' : ''}Rodada ${match.round} · ${new Date(match.date).toLocaleString('pt-BR')}`} onPress={() => { setMatchId(match.id); setOutId(''); setInId(''); }} />)}
      {!scheduled.length && <Text>Nenhuma partida programada.</Text>}
      {selected && <>
        <Field label="Minuto do comando (0–85)" numeric value={minute} onChange={setMinute} />
        <Button title="Programar mudança com a tática acima" disabled={action.busy} onPress={() => void action.run(() => plan('tactics_change'))} />
        <Text>Sai</Text>{squad.data?.players.filter(p => starters.has(p.id)).map(p => <Button key={p.id} title={`${outId === p.id ? '✓ ' : ''}${p.name} · ${p.position}`} onPress={() => setOutId(p.id)} />)}
        <Text>Entra</Text>{squad.data?.players.filter(p => reserves.has(p.id)).map(p => <Button key={p.id} title={`${inId === p.id ? '✓ ' : ''}${p.name} · ${p.position}`} onPress={() => setInId(p.id)} />)}
        <Button title="Programar substituição" disabled={action.busy} onPress={() => void action.run(() => plan('substitution'))} />
        <Text>Comandos programados</Text>{selected.commands?.filter(c => c.team_id === clubId).map((c, i) => <Text key={i}>{c.minute} min · {c.type === 'substitution' ? 'Substituição' : 'Mudança tática'} · {Object.entries(c.payload).map(([key, value]) => key.endsWith('player_id') ? squad.data?.players.find(p => p.id === value)?.name ?? value : ({ ...styles, ...markings, ...focuses } as Record<string, string>)[value] ?? value).join(' / ')}</Text>)}
      </>}
    </>}{message && <Text>{message}</Text>}
  </GamePage>;
}
