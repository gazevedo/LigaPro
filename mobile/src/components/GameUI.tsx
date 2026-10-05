import { ReactNode, useCallback, useRef, useState } from 'react';
import { ActivityIndicator, Button, ScrollView, Text, TextInput, View } from 'react-native';
export const money = (amount: number) => (amount / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
export function GamePage({ children, loading, error }: { children: ReactNode; loading?: boolean; error?: string | null }) {
  return <ScrollView contentContainerStyle={{ padding: 20, gap: 14 }}>{loading && <ActivityIndicator />}{error && <Text accessibilityRole="alert" style={{ color: '#b91c1c' }}>{error}</Text>}{children}</ScrollView>;
}
export function Field({ label, value, onChange, numeric = false }: { label: string; value: string; onChange: (value: string) => void; numeric?: boolean }) {
  return <View><Text>{label}</Text><TextInput accessibilityLabel={label} value={value} onChangeText={onChange} keyboardType={numeric ? 'numeric' : 'default'} style={{ borderWidth: 1, padding: 10, borderRadius: 6 }} /></View>;
}
export function Choices({ values, value, onChange, disabled = false }: { values: string[]; value: string; onChange: (value: string) => void; disabled?: boolean }) {
  return <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{values.map(item => <Button key={item} disabled={disabled} title={`${value === item ? '✓ ' : ''}${item}`} onPress={() => onChange(item)} />)}</View>;
}
export function useAction() {
  const [busy, setBusy] = useState(false), [error, setError] = useState<string | null>(null);
  const active = useRef(false);
  const run = useCallback(async (action: () => Promise<unknown>) => {
    if (active.current) return;
    active.current = true;
    setBusy(true); setError(null);
    try { await action(); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Operação falhou.'); }
    finally { active.current = false; setBusy(false); }
  }, []);
  return { busy, error, run };
}
export function cents(value: string) { if (!/^\d+(?:[,.]\d{1,2})?$/.test(value.trim())) throw new Error('Informe um valor monetário válido.'); const number = Number(value.replace(',', '.')); if (!Number.isFinite(number) || number < 0) throw new Error('Valor inválido.'); return Math.round(number * 100); }
