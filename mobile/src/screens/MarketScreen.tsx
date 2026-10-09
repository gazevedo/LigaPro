import { useMemo, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { ComboBox } from '../components/ComboBox';
import { PlayerPopup } from '../components/PlayerPopup';
import { useCatalogStore, useMarketPlayersStore } from '../stores/screenStores';
import { useScreenRefresh } from '../components/useScreenRefresh';
import { marketService } from '../services/marketService';
import { useMarketStore } from '../stores/marketStore';
import { ActionButton as Button, Card, Field, GamePage, money, palette, useAction } from '../components/GameUI';
export function MarketScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'Market'>) {
  const [tab, setTab] = useState('Buscar'), [filters, setFilters] = useState<Record<string, string>>({}), [applied, setApplied] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const catalogue = useCatalogStore(), results = useMarketPlayersStore();
  const countries = catalogue.data?.countries ?? [], players = results.data ?? [];
  const store = useMarketStore(), action = useAction();
  const query = useMemo(() => marketQuery(tab, applied), [tab, applied]);
  useScreenRefresh(catalogue.ensure);
  useScreenRefresh(() => tab.startsWith('Minhas') ? store.ensure() : results.ensure(query),
    () => tab.startsWith('Minhas') ? store.refresh() : results.refresh(query), !action.busy, JSON.stringify([tab, query]));
  return <GamePage loading={action.busy || (tab.startsWith('Minhas') ? store.loading : results.loading)} error={action.error || (tab.startsWith('Minhas') ? store.error : results.error) || catalogue.error}><ComboBox label="Mercado" options={['Buscar', 'À venda', 'Empréstimos', 'Jogadores livres', 'Minhas negociações', 'Minhas ofertas'].map(value => ({ value, label: value }))} value={tab} disabled={action.busy} onChange={setTab} />
    {tab.startsWith('Minhas') ? <><Button title="Gerenciar propostas" onPress={() => navigation.navigate('TransferOffers')} />{(tab === 'Minhas negociações' ? store.data?.incoming : store.data?.outgoing)?.map(o => <Text key={o.id}>Proposta {o.id} · {money(o.amount)} · {o.status}</Text>)}{tab === 'Minhas negociações' && <>{store.data?.listings.map(l => <View key={l.id}><Text>{l.type} · {l.player_id} · {money(l.price)} · {l.status}</Text>{l.status === 'active' && <Button title="Retirar anúncio" onPress={() => void action.run(async () => { await marketService.cancelListing(l.id); await store.load(); })} />}</View>)}{store.data?.loans.map(l => <Text key={l.id}>Empréstimo {l.player_id} · {l.status} · até {new Date(l.ends_at).toLocaleDateString('pt-BR')}</Text>)}</>}</> : <>
    <Card><Field label="Nome" value={filters.name ?? ''} onChange={value => setFilters(current => ({ ...current, name: value }))} />
      <ComboBox label="Posição" value={filters.position ?? ''} options={[{ value: '', label: 'Todas' }, ...Object.entries({ GK: 'Goleiro', FB: 'Lateral', CB: 'Zagueiro', MID: 'Meio-campo', ATT: 'Atacante' }).map(([value, label]) => ({ value, label }))]} onChange={value => setFilters(current => ({ ...current, position: value }))} />
      <ComboBox label="País" value={filters.country_id ?? ''} options={[{ value: '', label: 'Todos' }, ...countries.map(country => ({ value: country.id, label: country.name }))]} onChange={value => setFilters(current => ({ ...current, country_id: value }))} />
      {[{ key: 'age_min', label: 'Idade mínima', values: [16,18,20,25,30,35] }, { key: 'age_max', label: 'Idade máxima', values: [18,20,25,30,35,40,45] }, { key: 'overall_min', label: 'Força mínima', values: [0,20,40,60,80,90] }, { key: 'overall_max', label: 'Força máxima', values: [20,40,60,80,90,100] }].map(filter => <ComboBox key={filter.key} label={filter.label} value={filters[filter.key] ?? ''} options={[{ value: '', label: 'Sem limite' }, ...filter.values.map(value => ({ value: String(value), label: String(value) }))]} onChange={value => setFilters(current => ({ ...current, [filter.key]: value }))} />)}
      {[{ key: 'value_min', label: 'Valor mínimo' }, { key: 'value_max', label: 'Valor máximo' }].map(filter => <ComboBox key={filter.key} label={filter.label} value={filters[filter.key] ?? ''} options={[{ value: '', label: 'Sem limite' }, ...[100000,500000,1000000,5000000,10000000,50000000].map(value => ({ value: String(value), label: money(value) }))]} onChange={value => setFilters(current => ({ ...current, [filter.key]: value }))} />)}
      <ComboBox label="Ordenar por" value={filters.sort ?? 'value_asc'} options={[{ value: 'value_asc', label: 'Valor: menor primeiro' }, { value: 'value_desc', label: 'Valor: maior primeiro' }, { value: 'strength_desc', label: 'Força: maior primeiro' }, { value: 'strength_asc', label: 'Força: menor primeiro' }]} onChange={value => setFilters(current => ({ ...current, sort: value }))} />
      <Button title="Buscar" disabled={action.busy} onPress={() => { setApplied({ ...filters }); void results.load(marketQuery(tab, filters)); }} />
    </Card>
    {players.map(player => <Pressable key={player.id} accessibilityRole="button" accessibilityLabel={`Detalhes de ${player.name}`} onPress={() => setSelected(player.id)}><Card><Text style={{ color: palette.ink, fontWeight: '700' }}>{player.name}</Text><Text>{player.position} · {player.age} anos · Força {player.strength ?? player.overall} · {money(player.market_value ?? player.value)}</Text></Card></Pressable>)}
    {!players.length && <Text>Nenhum jogador encontrado.</Text>}</>}
    <PlayerPopup id={selected} onClose={() => setSelected(null)} navigation={navigation} />
  </GamePage>;
}

function marketQuery(tab: string, filters: Record<string, string>) {
  const value: Record<string, string> = { sort: 'value_asc', ...Object.fromEntries(Object.entries(filters).filter(([, item]) => item)) };
  if (tab === 'À venda') value.type = 'sale';
  if (tab === 'Empréstimos') value.type = 'loan';
  if (tab === 'Jogadores livres') { value.status = 'free_agent'; delete value.type; }
  return value;
}
