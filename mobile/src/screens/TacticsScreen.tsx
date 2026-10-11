import { useScreenRefresh } from '../components/useScreenRefresh';
import { useRef, useState } from 'react';
import { Card, GamePage } from '../components/GameUI';
import { ComboBox } from '../components/ComboBox';
import { tacticsService, Tactics } from '../services/tacticsService';
import { useTacticsStore } from '../stores/tacticsStore';
import { useSquadStore } from '../stores/squadStore';
import { LineupEditor } from '../components/LineupEditor';
const styles = { balanced: 'Equilibrado', all_out_attack: 'Ataque total', counter_attack: 'Contra-ataque' };
const markings = { light: 'Leve', heavy: 'Pesada', very_heavy: 'Muito pesada' };
const focuses = { normal: 'Normal', center: 'Centro', wings: 'Laterais' };
export function TacticsScreen() {
  const store = useTacticsStore(), squad = useSquadStore();
  const [pending, setPending] = useState<Tactics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const desired = useRef<Tactics | null>(null);
  const revision = useRef(0);
  const saving = useRef(false);
  useScreenRefresh(() => Promise.all([store.ensure(), squad.ensure()]));
  const draft = pending ?? store.data;
  async function flush() {
    if (saving.current) return;
    saving.current = true;
    try {
      while (desired.current) {
        const target = desired.current;
        const ticket = revision.current;
        try {
          await tacticsService.save(target);
          if (ticket !== revision.current) continue;
          await store.load(); await squad.load();
          if (ticket !== revision.current) continue;
          desired.current = null;
          setPending(null);
        } catch (reason) {
          if (ticket !== revision.current) continue;
          desired.current = null;
          setPending(null);
          setError(reason instanceof Error ? reason.message : 'Não foi possível salvar a tática.');
        }
      }
    } finally { saving.current = false; }
  }
  function change(patch: Partial<Tactics>) {
    const current = desired.current ?? store.data;
    if (!current) return;
    desired.current = { formation: current.formation, play_style: current.play_style, marking: current.marking, attack_focus: current.attack_focus, ...patch };
    revision.current++;
    setPending(desired.current);
    setError(null);
    void flush();
  }
  const options = (labels: Record<string, string>) => Object.entries(labels).map(([value, label]) => ({ value, label }));
  return <GamePage error={error || store.error || squad.error}>
    {draft && squad.data && <>
    <Card>
      <ComboBox inline label="Formação" value={draft.formation} options={Object.keys(squad.data?.formations ?? {}).map(value => ({ value, label: value }))} onChange={formation => change({ formation })} />
      <ComboBox inline label="Estilo de jogo" value={draft.play_style} options={options(styles)} onChange={play_style => change({ play_style: play_style as Tactics['play_style'] })} />
      <ComboBox inline label="Marcação" value={draft.marking} options={options(markings)} onChange={marking => change({ marking: marking as Tactics['marking'] })} />
      <ComboBox inline label="Foco dos ataques" value={draft.attack_focus} options={options(focuses)} onChange={attack_focus => change({ attack_focus: attack_focus as Tactics['attack_focus'] })} />
    </Card>
    <LineupEditor key={draft.formation} squad={squad.data} formation={draft.formation} />
    </>}
  </GamePage>;
}
