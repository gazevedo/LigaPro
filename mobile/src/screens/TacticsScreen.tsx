import { useEffect, useState } from 'react';
import { Text } from 'react-native';
import { ActionButton as Button, Card, Choices, NotificationBubble, GamePage, useAction } from '../components/GameUI';
import { tacticsService, Tactics } from '../services/tacticsService';
import { useTacticsStore } from '../stores/tacticsStore';
import { useSquadStore } from '../stores/squadStore';
import { LineupEditor } from '../components/LineupEditor';

const styles = { balanced: 'Equilibrado', all_out_attack: 'Ataque total', counter_attack: 'Contra-ataque' };
const markings = { light: 'Leve', heavy: 'Pesada', very_heavy: 'Muito pesada' };
const focuses = { normal: 'Normal', center: 'Centro', wings: 'Laterais' };
function Selector<T extends string>({ labels, value, change }: { labels: Record<T, string>; value: T; change: (value: T) => void }) {
  return <Choices values={Object.values<string>(labels)} value={labels[value]} onChange={label => change((Object.keys(labels) as T[]).find(key => labels[key] === label)!)} />;
}
export function TacticsScreen() {
  const store = useTacticsStore(), squad = useSquadStore(), action = useAction();
  const [draftOverride, setDraft] = useState<Tactics | null>(null), [message, setMessage] = useState('');
  const load = store.load, loadSquad = squad.load;
  useEffect(() => { void load(); void loadSquad(); }, [load, loadSquad]);

  const draft = draftOverride ?? (store.data ? { formation: store.data.formation, play_style: store.data.play_style, marking: store.data.marking, attack_focus: store.data.attack_focus } : null);
  return <GamePage loading={store.loading || squad.loading || action.busy} error={action.error || store.error || squad.error}>
    {draft && <Card><Text style={{ fontSize: 22, fontWeight: '800' }}>Estratégia do clube</Text>
      <Text>Formação</Text><Choices values={Object.keys(squad.data?.formations ?? {})} value={draft.formation} onChange={formation => setDraft({ ...draft, formation })} />
      <Text>Estilo de jogo</Text><Selector labels={styles} value={draft.play_style} change={play_style => setDraft({ ...draft, play_style })} />
      <Text>Equilibrado mantém os setores. Ataque total cria mais, mas expõe a defesa. Contra-ataque aproveita as transições.</Text>
      <Text>Marcação</Text><Selector labels={markings} value={draft.marking} change={marking => setDraft({ ...draft, marking })} />
      <Text>Marcação mais pesada contém mais ataques, mas aumenta faltas e cartões e dificulta a saída de bola.</Text>
      <Text>Foco dos ataques</Text><Selector labels={focuses} value={draft.attack_focus} change={attack_focus => setDraft({ ...draft, attack_focus })} />
      <Text>Centro e laterais direcionam aproximadamente 70% dos ataques. A formação adapta os titulares atuais.</Text>
      <Button disabled={action.busy} title="Salvar tática do clube" onPress={() => void action.run(async () => { await tacticsService.save(draft); await load(); await loadSquad(); setDraft(null); setMessage('Tática salva.'); })} />
    </Card>}{draft && squad.data && <LineupEditor key={JSON.stringify(squad.data.lineup)} squad={squad.data} formation={draft.formation} />}<NotificationBubble message={message} tone="info" />
  </GamePage>;
}
