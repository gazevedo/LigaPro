import { useEffect, useState } from 'react';
import { Button, Text, View } from 'react-native';
import { useCalendarStore } from '../stores/calendarStore';
import { Choices, Field, GamePage, useAction } from '../components/GameUI';
export function CalendarScreen() {
  const store = useCalendarStore(), action = useAction();
  const [view, setView] = useState('Lista'), [type, setType] = useState('Todos'), [start, setStart] = useState(''), [end, setEnd] = useState(''), [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
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
  const events = store.data ?? [], days = view === 'Mês' ? Array.from({ length: new Date(Number(month.slice(0, 4)), Number(month.slice(5)), 0).getDate() || 0 }, (_, i) => i + 1) : [];
  return <GamePage loading={store.loading || action.busy} error={action.error || store.error}><Choices values={['Lista', 'Mês']} value={view} onChange={setView} /><Choices values={['Todos', 'match', 'training', 'competition', 'transfer', 'financial', 'stadium', 'other']} value={type} onChange={setType} />{view === 'Lista' ? <><Field label="Início (AAAA-MM-DD)" value={start} onChange={setStart} /><Field label="Fim (AAAA-MM-DD)" value={end} onChange={setEnd} /></> : <Field label="Mês (AAAA-MM)" value={month} onChange={setMonth} />}<Button title="Aplicar filtros" onPress={() => void action.run(apply)} />
    {view === 'Mês' ? <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>{days.map(day => <View key={day} style={{ width: '14.28%', borderWidth: 1, padding: 4 }}><Text>{day}</Text>{events.filter(e => e.date.slice(0, 10) === `${month}-${String(day).padStart(2, '0')}`).map(e => <Text key={e.id}>{e.title}</Text>)}</View>)}</View> : events.map(e => <Text key={e.id}>{new Date(e.date).toLocaleString('pt-BR')} · {e.type} · {e.title}</Text>)}{!events.length && <Text>Nenhum evento neste período.</Text>}</GamePage>;
}
