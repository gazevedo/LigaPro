import { useEffect, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { useCalendarStore } from '../stores/calendarStore';
import { ActionButton, Card, GamePage, palette } from '../components/GameUI';
const dayKey = (date: Date) => `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
export function CalendarScreen() {
  const store = useCalendarStore();
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [selected, setSelected] = useState(() => new Date().getDate());
  const load = store.load;
  useEffect(() => { void load({ start: month.toISOString(), end: new Date(month.getFullYear(), month.getMonth() + 1, 1).toISOString() }); }, [load, month]);
  const events = store.data ?? [], today = dayKey(new Date());
  const cells = Array.from({ length: month.getDay() + new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate() }, (_, index) => index < month.getDay() ? null : index - month.getDay() + 1);
  function move(offset: number) { setMonth(new Date(month.getFullYear(), month.getMonth() + offset, 1)); setSelected(1); }
  const date = (day: number) => new Date(month.getFullYear(), month.getMonth(), day);
  const selectedEvents = events.filter(event => dayKey(new Date(event.date)) === dayKey(date(selected)));
  return <GamePage loading={store.loading} error={store.error}><Text style={{ fontSize: 26, fontWeight: '800', color: palette.ink }}>Agenda do clube</Text>
    <Card><View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}><ActionButton title="‹" accessibilityLabel="Mês anterior" secondary onPress={() => move(-1)} /><Text style={{ color: palette.ink, fontWeight: '800', fontSize: 18 }}>{month.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })}</Text><ActionButton title="›" accessibilityLabel="Próximo mês" secondary onPress={() => move(1)} /></View>
      <View style={{ flexDirection: 'row' }}>{['D', 'S', 'T', 'Q', 'Q', 'S', 'S'].map((label, i) => <Text key={i} style={{ width: '14.28%', textAlign: 'center', color: palette.muted, fontWeight: '700' }}>{label}</Text>)}</View>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>{cells.map((day, index) => {
        const hasEvents = day !== null && events.some(event => dayKey(new Date(event.date)) === dayKey(date(day)));
        return <View key={index} style={{ width: '14.28%', height: 48 }}>{day !== null && <Pressable accessibilityRole="button" accessibilityLabel={`Dia ${day}${hasEvents ? ', com eventos' : ''}`} accessibilityState={{ selected: day === selected }} onPress={() => setSelected(day)} style={{ flex: 1, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: day === selected ? '#c9ecdd' : dayKey(date(day)) === today ? '#fff2be' : '#fff' }}><Text style={{ color: palette.ink, fontWeight: '700' }}>{day}</Text>{hasEvents && <View style={{ width: 5, height: 5, borderRadius: 3, backgroundColor: palette.primary, marginTop: 4 }} />}</Pressable>}</View>;
      })}</View>
    </Card><Text style={{ fontSize: 20, fontWeight: '800', color: palette.ink }}>{date(selected).toLocaleDateString('pt-BR', { day: 'numeric', month: 'long' })}</Text>
    {selectedEvents.map(event => <Card key={event.id}><Text style={{ fontWeight: '700', color: palette.ink }}>{event.title}</Text><Text style={{ color: palette.muted }}>{new Date(event.date).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</Text></Card>)}
    {!selectedEvents.length && <Card><Text style={{ color: palette.muted }}>Nenhum evento neste dia.</Text></Card>}
  </GamePage>;
}
