import { useScreenRefresh } from '../components/useScreenRefresh';
import { useState } from 'react';
import { Card, GamePage, useAction } from '../components/GameUI';
import { ComboBox } from '../components/ComboBox';
import { tacticsService, Tactics } from '../services/tacticsService';
import { useTacticsStore } from '../stores/tacticsStore';
import { useSquadStore } from '../stores/squadStore';
import { LineupEditor } from '../components/LineupEditor';
const styles = { balanced: 'Equilibrado', all_out_attack: 'Ataque total', counter_attack: 'Contra-ataque' };
const markings = { light: 'Leve', heavy: 'Pesada', very_heavy: 'Muito pesada' };
const focuses = { normal: 'Normal', center: 'Centro', wings: 'Laterais' };
export function TacticsScreen() {
  const store = useTacticsStore(), squad = useSquadStore(), action = useAction();
  const [pending, setPending] = useState<Partial<Tactics> | null>(null);
  const load = store.load, loadSquad = squad.load;
  useScreenRefresh(() => Promise.all([store.ensure(), squad.ensure()]));
  const draft = store.data ? { ...store.data, ...pending } : null;
  const busy = store.loading || squad.loading || action.busy;
  function change(patch: Partial<Tactics>) {
    if (!draft || busy) return;
    setPending(patch);
    void action.run(async () => {
      try {
        await tacticsService.save({ formation: draft.formation, play_style: draft.play_style, marking: draft.marking, attack_focus: draft.attack_focus, ...patch });
        await load(); await loadSquad();
      } finally { setPending(null); }
    });
  }
  const options = (labels: Record<string, string>) => Object.entries(labels).map(([value, label]) => ({ value, label }));
  return <GamePage error={action.error || store.error || squad.error}>
    {draft && squad.data && <>
    <Card>
      <ComboBox inline label="Formação" value={draft.formation} options={Object.keys(squad.data?.formations ?? {}).map(value => ({ value, label: value }))} disabled={busy} onChange={formation => change({ formation })} />
      <ComboBox inline label="Estilo de jogo" value={draft.play_style} options={options(styles)} disabled={busy} onChange={play_style => change({ play_style: play_style as Tactics['play_style'] })} />
      <ComboBox inline label="Marcação" value={draft.marking} options={options(markings)} disabled={busy} onChange={marking => change({ marking: marking as Tactics['marking'] })} />
      <ComboBox inline label="Foco dos ataques" value={draft.attack_focus} options={options(focuses)} disabled={busy} onChange={attack_focus => change({ attack_focus: attack_focus as Tactics['attack_focus'] })} />
    </Card>
    <LineupEditor key={JSON.stringify([squad.data.lineup, draft.formation])} squad={squad.data} formation={draft.formation} disabled={busy} />
    </>}
  </GamePage>;
}
