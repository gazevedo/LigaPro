import { useScreenRefresh } from '../components/useScreenRefresh';
import { useSponsorsStore } from '../stores/screenStores';
import { Text, View } from 'react-native';
import { financeService } from '../services/financeService';
import { ActionButton as Button, GamePage, money, useAction } from '../components/GameUI';
export function SponsorsScreen() {
  const { data, loading, error, ensure, load, refresh } = useSponsorsStore(), action = useAction();
  useScreenRefresh(ensure, refresh);
  return <GamePage loading={loading || action.busy} error={action.error || error}><Text>Contratos</Text>{data?.contracts.map(c => <View key={c.id}><Text>{c.name} · {({ active: 'Ativo', terminated: 'Encerrado', expired: 'Expirado' } as Record<string, string>)[c.status] ?? c.status} · {money(c.monthly_value ?? c.value)}/mês · até {new Date(c.ends_at).toLocaleDateString('pt-BR')}</Text>{c.can_terminate && <Button title="Encerrar patrocínio herdado" onPress={() => void action.run(async () => { await financeService.terminateSponsor(c.id); await load(); })} />}</View>)}<Text>Ofertas</Text>{data?.offers.map(o => <View key={o.id}><Text>{o.name} · requisito: ranking {o.required_ranking} · {o.duration_months ?? Math.round(o.duration_days * 12 / 30)} meses · {money(o.monthly_value ?? o.value)}/mês · bônus {money(o.bonus ?? 0)}</Text><Button title="Aceitar patrocínio" disabled={data.contracts.some(c => c.status === 'active' && new Date(c.ends_at) > new Date())} onPress={() => void action.run(async () => { await financeService.sponsor(o.id); await load(); })} /></View>)}</GamePage>;
}
