import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';
import { Sponsors } from '../types/game';
import { financeService } from '../services/financeService';
import { ActionButton as Button, GamePage, money, useAction } from '../components/GameUI';
export function SponsorsScreen() {
  const [data, setData] = useState<Sponsors | null>(null), action = useAction();
  async function load() { setData(await financeService.sponsors()); }
  useEffect(() => { void action.run(load); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return <GamePage loading={action.busy} error={action.error}><Button title="Atualizar patrocinadores" onPress={() => void action.run(load)} /><Text>Contratos</Text>{data?.contracts.map(c => <Text key={c.id}>{c.name} · {c.status} · {money(c.monthly_value ?? c.value)}/mês · até {new Date(c.ends_at).toLocaleDateString('pt-BR')}</Text>)}<Text>Ofertas</Text>{data?.offers.map(o => <View key={o.id}><Text>{o.name} · requisito: ranking {o.required_ranking} · {o.duration_months ?? Math.round(o.duration_days * 12 / 30)} meses · {money(o.monthly_value ?? o.value)}/mês · bônus {money(o.bonus ?? 0)}</Text><Button title="Aceitar patrocínio" disabled={action.busy || data.contracts.some(c => c.status === 'active' && new Date(c.ends_at) > new Date())} onPress={() => void action.run(async () => { await financeService.sponsor(o.id); await load(); })} /></View>)}</GamePage>;
}
