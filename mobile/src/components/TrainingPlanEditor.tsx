import { useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { useAuthStore } from '../stores/authStore';
import { useClubStore } from '../stores/clubStore';
import { Player, PlayerSkill } from '../types/game';
import { TrainingPlan, trainingPlanService } from '../services/developmentService';
import { ActionButton, Card, NotificationBubble } from './GameUI';
import { ComboBox } from './ComboBox';
export const trainingSkills = { goalkeeping: 'Defesa do goleiro', speed: 'Velocidade', technique: 'Técnica', passing: 'Passe', tackling: 'Desarme', playmaking: 'Criação', finishing: 'Finalização' };
const skills = Object.entries(trainingSkills).map(([value, label]) => ({ value, label }));
export function TrainingPlanEditor({ players }: { players: Player[] }) {
  const owner = useRef({ user: useAuthStore.getState().user?.id, club: useClubStore.getState().data?.club?.id });
  const active = () => owner.current.user === useAuthStore.getState().user?.id && owner.current.club === useClubStore.getState().data?.club?.id;
  const [plan, setPlan] = useState<TrainingPlan | null>(null), [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const desired = useRef<TrainingPlan | null>(null), confirmed = useRef<TrainingPlan | null>(null), working = useRef(false);
  useEffect(() => {
    let mounted = true;
    void trainingPlanService.get().then(value => { if (mounted) { confirmed.current = value; setPlan(value); } }).catch(() => { if (mounted) setError('Não foi possível carregar o plano de treino.'); });
    return () => { mounted = false; };
  }, []);
  async function flush() {
    if (working.current) return;
    working.current = true; setSaving(true);
    try {
      while (desired.current) {
        if (!active()) { desired.current = null; return; }
        const target = desired.current;
        try {
          const saved = await trainingPlanService.save(target);
          if (!active()) { desired.current = null; return; }
          confirmed.current = saved;
          if (desired.current !== target) continue;
          desired.current = null; setPlan(saved);
        } catch {
          if (desired.current !== target) continue;
          desired.current = null; setPlan(confirmed.current);
          setError('Não foi possível salvar o plano. A última configuração confirmada foi restaurada.');
        }
      }
    } finally { working.current = false; setSaving(false); }
  }
  function change(patch: Partial<TrainingPlan>) {
    if (!plan) return;
    const next = { ...(desired.current ?? plan), ...patch };
    desired.current = next; setPlan(next); setError(''); void flush();
  }
  return <Card><Text style={{ fontSize: 20, fontWeight: '700' }}>Plano automático</Text><NotificationBubble message={error} />
    {!plan && <ActionButton secondary title="Recarregar plano" onPress={() => { void trainingPlanService.get().then(value => { confirmed.current = value; setPlan(value); setError(''); }).catch(() => setError('Não foi possível carregar o plano de treino.')); }} />}
    {plan && <>
      <Text>Uma sessão a cada 6 horas, inclusive offline. Alterar o plano inicia um novo período. Lesionados e jogadores com condição abaixo de 70 ou energia abaixo de 50 descansam.</Text>
      <ActionButton title={plan.enabled ? 'Pausar plano automático' : 'Ativar plano automático'} onPress={() => change({ enabled: !plan.enabled })} />
      <ComboBox label="Duração do plano" value={String(plan.days)} options={[1,3,7,14,30].map(value => ({ value: String(value), label: `${value} dia(s)` }))} onChange={value => change({ days: Number(value) })} />
      <ComboBox label="Treino coletivo" value={plan.skill} options={skills} onChange={value => change({ skill: value as PlayerSkill })} />
      <ComboBox label="Intensidade" value={plan.intensity} options={[{ value: 'light', label: 'Leve · progresso e desgaste 1×' }, { value: 'normal', label: 'Normal · progresso e desgaste 2×' }, { value: 'intense', label: 'Intenso · progresso e desgaste 3×' }, { value: 'rest', label: 'Descanso · recuperação natural' }]} onChange={value => change({ intensity: value as TrainingPlan['intensity'] })} />
      <Text>{saving ? 'Salvando plano…' : plan.enabled ? 'Plano ativo' : 'Plano pausado ou concluído'} · {plan.sessions_completed ?? 0} sessões realizadas</Text>
      {plan.enabled && plan.next_session_at && <Text>Próxima sessão: {new Date(plan.next_session_at).toLocaleString('pt-BR')} · Até {new Date(plan.ends_at!).toLocaleString('pt-BR')}</Text>}
      <Text style={{ fontWeight: '700' }}>Ajustes individuais</Text>
      {players.map(player => <View key={player.id}><ComboBox label={player.name} value={plan.individual[player.id] ?? 'collective'} options={[{ value: 'collective', label: 'Seguir treino coletivo' }, { value: 'rest', label: 'Descansar' }, ...skills]} onChange={value => { const individual = { ...(desired.current ?? plan).individual }; if (value === 'collective') delete individual[player.id]; else individual[player.id] = value as PlayerSkill | 'rest'; change({ individual }); }} /></View>)}
    </>}
  </Card>;
}
