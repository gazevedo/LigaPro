import { useScreenRefresh } from '../components/useScreenRefresh';
import { useRef, useState } from 'react';
import { Modal, Text, View } from 'react-native';
import { useStadiumStore } from '../stores/stadiumStore';
import { useClubStore } from '../stores/clubStore';
import { useAuthStore } from '../stores/authStore';
import { useNotificationStore } from '../stores/notificationStore';
import { stadiumService } from '../services/stadiumService';
import { Stadium, StadiumSector } from '../types/game';
import { FacilityIcon, StadiumModel } from '../components/StadiumModel';
import { ScreenTabs } from '../components/ScreenTabs';
import { ActionButton as Button, Card, Field, GamePage, NotificationBubble, cents, money, palette } from '../components/GameUI';
type Mutation = { id: number; facility?: string; evolve?: boolean; sector?: string; price?: number };
function apply(stadium: Stadium, mutation: Mutation): Stadium {
  if (mutation.sector) return { ...stadium, sectors: stadium.sectors?.map(sector => sector.id === mutation.sector ? { ...sector, price: mutation.price! } : sector) };
  if (mutation.evolve) {
    const next = stadium.levels?.find(level => level.level === (stadium.arena_level ?? 1) + 1);
    return next ? { ...stadium, arena_level: next.level, arena_name: next.name, capacity: next.capacity, facilities: next.level >= 3 ? { ...stadium.facilities, upper_stands: Math.max(1, stadium.facilities.upper_stands ?? 0) } : stadium.facilities } : stadium;
  }
  const facility = mutation.facility!;
  const current = stadium.facilities[facility] ?? 0, level = current + 1;
  return { ...stadium, capacity: stadium.capacity + (['stands', 'upper_stands'].includes(facility) ? 1000 : 0), facilities: { ...stadium.facilities, [facility]: level }, upgrade_costs: { ...stadium.upgrade_costs, [facility]: (stadium.upgrade_costs[facility] ?? 0) / Math.max(1, current) * Math.max(1, level) }, facility_catalog: stadium.facility_catalog ? { ...stadium.facility_catalog, [facility]: { ...stadium.facility_catalog[facility], level_name: stadium.facility_level_names?.[Math.min(5, level)] ?? '' } } : undefined };
}
export function StadiumScreen() {
  const store = useStadiumStore();
  const [validation, setValidation] = useState<string | null>(null);
  const [tab, setTab] = useState('Setores'), [editor, setEditor] = useState<StadiumSector | null>(null), [price, setPrice] = useState('');
  const [pending, setPending] = useState<Mutation[]>([]), [confirmed, setConfirmed] = useState<Stadium | null>(null);
  const operations = useRef<Mutation[]>([]), sequence = useRef(0), committed = useRef<Stadium | null>(null);
  useScreenRefresh(store.refresh, store.refresh);
  const base = pending.length ? confirmed ?? store.data : store.data;
  const data = base ? pending.reduce(apply, base) : null;
  function enqueue(change: Omit<Mutation, 'id'>, send: () => Promise<Stadium>) {
    if (!data) return;
    const user = useAuthStore.getState().user?.id, club = useClubStore.getState().data?.club?.id;
    const active = () => user === useAuthStore.getState().user?.id && club === useClubStore.getState().data?.club?.id;
    if (!operations.current.length) { committed.current = store.data; setConfirmed(store.data); }
    const operation = { ...change, id: ++sequence.current };
    operations.current.push(operation); setPending([...operations.current]);
    void send().then(result => {
      if (!active()) return;
      committed.current = result; setConfirmed(result);
      useStadiumStore.setState({ data: result });
    }).catch(reason => {
      if (!active()) return;
      useStadiumStore.setState({ data: committed.current });
      useNotificationStore.getState().show(reason instanceof Error ? reason.message : 'Não foi possível salvar a alteração do estádio.');
    }).finally(() => {
      if (!active()) return;
      operations.current = operations.current.filter(item => item.id !== operation.id);
      setPending([...operations.current]);
    });
  }
  function savePrice() {
    if (!editor) return;
    try {
      const amount = cents(price), sector = editor.id;
      if (amount > 100000) throw new Error('O ingresso pode custar até R$ 1.000,00.');
      enqueue({ sector, price: amount }, () => stadiumService.price(sector, amount));
      setEditor(null);
    } catch (reason) { setValidation(reason instanceof Error ? reason.message : 'Confira o preço informado.'); }
  }
  function open(sector: StadiumSector) { setValidation(null); setEditor(sector); setPrice((sector.price / 100).toFixed(2)); }
  const current = data?.arena_level ?? 1, next = data?.levels?.find(level => level.level === current + 1);
  const facilities = Object.entries(data?.facilities ?? {}).sort(([a], [b]) => (data?.names[a] ?? a).localeCompare(data?.names[b] ?? b, 'pt-BR'));
  const bonus = data?.effects;
  return <GamePage loading={store.loading} error={store.error}>
    <Card><Text style={{ fontSize: 24, fontWeight: '800', color: palette.ink }}>{data?.arena_name ?? 'Estádio'} · Nível {current}</Text><Text style={{ color: palette.muted }}>Capacidade: {data?.capacity.toLocaleString('pt-BR')} lugares</Text></Card>
    <ScreenTabs values={['Setores', 'Instalações', 'Evolução']} value={tab} onChange={setTab} />
    {tab === 'Setores' && <>
      <Card><Text style={{ color: palette.ink, fontWeight: '700' }}>Toque em um setor para definir seu ingresso.</Text><StadiumModel sectors={data?.sectors ?? []} open={open} /><Text style={{ color: palette.muted, fontSize: 12 }}>Setores indicados em cinza estão planejados e serão liberados com a evolução do estádio.</Text></Card>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>{data?.sectors?.map(sector => <View key={sector.id} style={{ flexBasis: '45%', flexGrow: 1, minWidth: 0 }}><View style={{ backgroundColor: '#fff', borderWidth: 1, borderColor: palette.border, borderRadius: 16, padding: 12, gap: 10 }}><Text style={{ color: palette.ink, fontWeight: '700' }}>{sector.name}</Text><Text style={{ color: palette.muted }}>{sector.capacity.toLocaleString('pt-BR')} lugares</Text><Text style={{ color: palette.primary, fontWeight: '800' }}>{money(sector.price)}</Text><Button title="Definir preço" accessibilityLabel={`Preço do setor ${sector.name}`} secondary disabled={!sector.available} onPress={() => open(sector)} /></View></View>)}</View>
    </>}
    {tab === 'Instalações' && <>
      {bonus && <Card><Text style={{ fontWeight: '800', color: palette.ink }}>Atributos do clube</Text><Text>Progresso por treino: {1 + Math.min(2, Math.max(0, (data?.facilities.training ?? 1) - 1)) + bonus.training_extra} pontos</Text><Text>Recuperação física base: {20 + 2 * (data?.facilities.medical ?? 1) + bonus.recovery_bonus} pontos/dia</Text><Text>Recuperação de energia base: {45 + bonus.energy_bonus} pontos/dia</Text><Text>Recuperação de moral: até {bonus.morale_recovery_per_day.toLocaleString('pt-BR')} pontos/dia</Text><Text>Demanda adicional: {(bonus.attendance_bonus * 100).toLocaleString('pt-BR')}%</Text><Text>Serviços por torcedor presente: {money(bonus.services_income_per_attendee)}</Text></Card>}
      {facilities.map(([key, level]) => {
        const catalog = data?.facility_catalog?.[key], locked = current < (catalog?.minimum_arena_level ?? 1), maximum = level >= (catalog?.maximum_level ?? 5);
        return <Card key={key}><View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}><FacilityIcon tile={catalog?.icon} dimmed={!level} /><View style={{ flex: 1, minWidth: 0 }}><Text style={{ fontWeight: '800', color: palette.ink }}>{data?.names[key]}</Text><Text style={{ color: palette.muted }}>{level ? `Nível ${level} · ${catalog?.level_name ?? ''}` : 'Não construído'}</Text></View></View><Text style={{ color: palette.muted }}>{catalog?.benefit}</Text>{locked && <Text>Disponível no nível {catalog?.minimum_arena_level} do estádio.</Text>}<Button title={maximum ? 'Nível máximo' : `${level ? 'Melhorar' : 'Construir'} ${data?.names[key]} — ${money(data?.upgrade_costs[key] ?? 0)}`} disabled={locked || maximum} onPress={() => enqueue({ facility: key }, () => stadiumService.upgrade(key))} /></Card>;
      })}
    </>}
    {tab === 'Evolução' && <>
      {data?.levels?.map(level => <Card key={level.level}><Text style={{ fontWeight: '800', color: palette.ink }}>Nível {level.level} · {level.name}{level.level === current ? ' · Atual' : level.level < current ? ' · Concluído' : ''}</Text><Text>{level.capacity.toLocaleString('pt-BR')} lugares</Text><Text style={{ color: palette.muted }}>{level.description}</Text>{level.level > current && <Text>{money(level.cost)}</Text>}{level.level === next?.level && <Button title={`Evoluir para ${level.name}`} onPress={() => enqueue({ evolve: true }, stadiumService.evolve)} />}</Card>)}
    </>}
    <Modal visible={editor !== null} transparent animationType="fade" onRequestClose={() => setEditor(null)}><View style={{ flex: 1, justifyContent: 'center', padding: 24, backgroundColor: '#14243a88' }}><View style={{ width: '100%', maxWidth: 420, alignSelf: 'center', padding: 24, gap: 16, borderRadius: 22, backgroundColor: '#fff' }}><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>{editor?.name}</Text><Text>{editor?.capacity.toLocaleString('pt-BR')} lugares</Text><Field label="Ingresso do setor (R$)" value={price} onChange={value => { setPrice(value); setValidation(null); }} numeric /><NotificationBubble message={validation} /><Button title="Salvar preço do setor" onPress={savePrice} /><Button title="Cancelar" secondary onPress={() => setEditor(null)} /></View></View></Modal>
  </GamePage>;
}
