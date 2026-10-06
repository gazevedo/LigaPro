import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';
import { calendarService, Friendly } from '../services/calendarService';
import { useClubStore } from '../stores/clubStore';
import { useCalendarStore } from '../stores/calendarStore';
import { ActionButton as Button, Choices, Field, GamePage, useAction } from '../components/GameUI';
export function CalendarScreen() {
  const store = useCalendarStore(), action = useAction();
  const [view, setView] = useState('Lista'), [type, setType] = useState('Todos'), [start, setStart] = useState(''), [end, setEnd] = useState(''), [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [opponent, setOpponent] = useState(''), [friendlyDate, setFriendlyDate] = useState(''), [friendlies, setFriendlies] = useState<Friendly[]>([]);
  const clubId = useClubStore(state => state.data?.club?.id);
  const load = store.load;
  useEffect(() => { void load(); }, [load]);
  async function apply() {
    const filters: Record<string, string> = {};
    if (type !== 'Todos') filters.type = type;
    if (start) filters.start = new Date(`${start}T00:00:00Z`).toISOString();
    if (end) filters.end = new Date(`${end}T23:59:59.999Z`).toISOString();
    if (view === 'Mês') {
      if (!/^\d{4}-\d{2}$/.test(month)) throw new Error('Use AAAA-MM.');
      const date = new Date(`${month}-01T00:00:00Z`); filters.start = date.toISOString(); date.setUTCMonth(date.getUTCMonth() + 1); filters.end = new Date(date.getTime() - 1).toISOString();
    }
    await store.load(filters);
  }
  useEffect(() => { void calendarService.friendlies().then(setFriendlies).catch(() => {}); }, []);
  const events = store.data ?? [], days = view === 'Mês' ? Array.from({ length: new Date(Number(month.slice(0, 4)), Number(month.slice(5)), 0).getDate() || 0 }, (_, i) => i + 1) : [];
  return <GamePage loading={store.loading || action.busy} error={action.error || store.error}><Choices values={['Lista', 'Mês']} value={view} onChange={setView} /><Choices values={['Todos', 'match', 'training', 'competition', 'transfer', 'financial', 'stadium', 'other', 'league_match', 'cup_match', 'friendly', 'transfer_window_open', 'transfer_window_close', 'season_start', 'season_end', 'youth_generation', 'financial_close']} value={type} onChange={setType} />{view === 'Lista' ? <><Field label="Início (AAAA-MM-DD)" value={start} onChange={setStart} /><Field label="Fim (AAAA-MM-DD)" value={end} onChange={setEnd} /></> : <Field label="Mês (AAAA-MM)" value={month} onChange={setMonth} />}<Button title="Aplicar filtros" onPress={() => void action.run(apply)} />
    {view === 'Mês' ? <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>{days.map(day => <View key={day} style={{ width: '14.28%', borderWidth: 1, padding: 4 }}><Text>{day}</Text>{events.filter(e => e.date.slice(0, 10) === `${month}-${String(day).padStart(2, '0')}`).map(e => <Text key={e.id}>{e.title}</Text>)}</View>)}</View> : events.map(e => <Text key={e.id}>{new Date(e.date).toLocaleString('pt-BR')} · {e.kind ?? e.type} · {e.title}</Text>)}{!events.length && <Text>Nenhum evento neste período.</Text>}<Text>Agendar amistoso</Text><Field label="Clube adversário (ID)" value={opponent} onChange={setOpponent} /><Field label="Data e horário (ISO com fuso)" value={friendlyDate} onChange={setFriendlyDate} /><Button title="Convidar para amistoso" disabled={action.busy} onPress={() => void action.run(async () => { await calendarService.friendly(opponent, new Date(friendlyDate).toISOString()); setFriendlies(await calendarService.friendlies()); await load(); })} />{friendlies.map(match => <View key={match.id}><Text>Amistoso · {new Date(match.date).toLocaleString('pt-BR')} · {match.status}</Text>{match.status === 'pending' && match.away_club_id === clubId && <Button title="Aceitar amistoso" disabled={action.busy} onPress={() => void action.run(async () => { await calendarService.acceptFriendly(match.id); setFriendlies(await calendarService.friendlies()); await load(); })} />}</View>)}</GamePage>;
}
