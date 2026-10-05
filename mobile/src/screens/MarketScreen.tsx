import { useEffect, useState } from 'react';
import { Button, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { Player } from '../types/game';
import { marketService } from '../services/marketService';
import { useMarketStore } from '../stores/marketStore';
import { Choices, Field, GamePage, money, useAction } from '../components/GameUI';
export function MarketScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'Market'>) {
  const [tab, setTab] = useState('Buscar'), [players, setPlayers] = useState<Player[]>([]), [filters, setFilters] = useState<Record<string, string>>({});
  const store = useMarketStore(), action = useAction();
  async function search(selected = tab) { const query = Object.fromEntries(Object.entries(filters).filter(([, value]) => value)); if (selected === 'À venda') query.type = 'sale'; if (selected === 'Empréstimos') query.type = 'loan'; setPlayers(await marketService.search(query)); }
  useEffect(() => { void action.run(async () => { await search(); await store.load(); }); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return <GamePage loading={action.busy || store.loading} error={action.error || store.error}><Choices values={['Buscar', 'À venda', 'Empréstimos', 'Minhas negociações', 'Minhas ofertas']} value={tab} disabled={action.busy || store.loading} onChange={value => { setTab(value); void action.run(async () => { if (value.startsWith('Minhas')) await store.load(); else await search(value); }); }} />
    {tab.startsWith('Minhas') ? <><Button title="Gerenciar propostas" onPress={() => navigation.navigate('TransferOffers')} />{(tab === 'Minhas negociações' ? store.data?.incoming : store.data?.outgoing)?.map(o => <Text key={o.id}>Proposta {o.id} · {money(o.amount)} · {o.status}</Text>)}{tab === 'Minhas negociações' && <>{store.data?.listings.map(l => <View key={l.id}><Text>{l.type} · {l.player_id} · {money(l.price)} · {l.status}</Text>{l.status === 'active' && <Button title="Retirar anúncio" onPress={() => void action.run(async () => { await marketService.cancelListing(l.id); await store.load(); })} />}</View>)}{store.data?.loans.map(l => <Text key={l.id}>Empréstimo {l.player_id} · {l.status} · até {new Date(l.ends_at).toLocaleDateString('pt-BR')}</Text>)}</>}</> : <>
    {Object.entries({ name: 'Nome', position: 'Posição (GOL/DEF/MED/ATA)', age_min: 'Idade mínima', age_max: 'Idade máxima', overall_min: 'Overall mínimo', overall_max: 'Overall máximo', value_min: 'Valor mínimo (centavos)', value_max: 'Valor máximo (centavos)', country_id: 'País (BR/PT/AR)', type: 'Tipo (sale/loan)' }).map(([key, label]) => <Field key={key} label={label} value={filters[key] ?? ''} onChange={value => setFilters(current => ({ ...current, [key]: value }))} />)}<Button title="Pesquisar jogadores" disabled={action.busy} onPress={() => void action.run(() => search())} />{players.map(p => <View key={p.id}><Text>{p.name} · {p.position} · {p.age} anos · overall {p.overall} · {money(p.value)} · {p.country_id}{p.listing ? ` · ${p.listing.type}: ${money(p.listing.price)}` : ''}</Text><Button title={`Ver ${p.name}`} onPress={() => navigation.navigate('PlayerDetails', { id: p.id })} /></View>)}{!players.length && <Text>Nenhum jogador encontrado.</Text>}</>}
  </GamePage>;
}
