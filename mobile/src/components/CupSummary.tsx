import { ActionButton as Button, NotificationBubble } from './GameUI';
import { useEffect } from 'react';
import { Text, View } from 'react-native';
import { cupService } from '../services/cupService';
import { domainStore } from '../stores/domainStore';
const useCupStore = domainStore(cupService.get);
export function CupSummary({ report }: { report?: (id: string) => void }) {
  const store = useCupStore(), load = store.load;
  useEffect(() => { void load(); }, [load]);
  return <>
    <Text>Copa Nacional · {store.data?.entry ? `${store.data.entry.phase} · ${store.data.entry.status === 'eliminated' ? 'Eliminado' : store.data.entry.status === 'champion' ? 'Campeão' : 'Em disputa'}` : store.data?.competition ? 'Sem participação nesta edição' : 'Aguardando chaveamento'}</Text>
    {store.error && <NotificationBubble message={store.error} />}
    {report && store.data?.matches.map(match => <View key={match.id}><Text>
      {match.phase} · {new Date(match.date).toLocaleDateString('pt-BR')}{match.status === 'completed' ? ` · ${match.home_goals} x ${match.away_goals}` : ' · Agendado'}</Text>
      {match.status === 'completed' && <Button title={`Relatório · ${match.phase}`} onPress={() => report(match.id)} />}
    </View>)}
  </>;
}
