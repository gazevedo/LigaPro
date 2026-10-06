import { ReactNode, useCallback, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, TextInputProps, View } from 'react-native';
export const palette = { ink: '#14243a', muted: '#64748b', primary: '#087f67', background: '#f2f5f9', border: '#dce4ee' };
export const money = (amount: number) => (amount / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
export function NotificationBubble({ message, tone = 'error' }: { message?: string | null; tone?: 'error' | 'info' }) {
  return message ? <Bubble key={message} message={message} tone={tone} /> : null;
}
function Bubble({ message, tone }: { message: string; tone: 'error' | 'info' }) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;
  return <View accessibilityRole="alert" accessibilityLiveRegion="polite" style={{ backgroundColor: tone === 'error' ? '#fff1f2' : '#e8f7f1', borderColor: tone === 'error' ? '#fecdd3' : '#99dbc5', borderWidth: 1, borderRadius: 18, padding: 16, flexDirection: 'row', gap: 12, boxShadow: '0 6px 18px #14243a12' }}><Text style={{ flex: 1, color: palette.ink }}>{message}</Text><Pressable accessibilityRole="button" accessibilityLabel="Fechar notificação" onPress={() => setDismissed(true)} hitSlop={8}><Text style={{ color: palette.muted }}>✕</Text></Pressable></View>;
}
export function ActionButton({ title, onPress, disabled = false, secondary = false }: { title: string; onPress: () => void; disabled?: boolean; secondary?: boolean }) {
  return <Pressable accessibilityRole="button" accessibilityState={{ disabled }} disabled={disabled} onPress={onPress} style={({ pressed }) => ({ paddingVertical: 14, paddingHorizontal: 20, borderRadius: 14, alignItems: 'center', backgroundColor: secondary ? '#e8eef5' : palette.primary, opacity: disabled ? 0.45 : pressed ? 0.75 : 1 })}><Text style={{ fontWeight: '700', color: secondary ? palette.ink : '#fff' }}>{title}</Text></Pressable>;
}
export function Card({ children }: { children: ReactNode }) { return <View style={{ backgroundColor: '#fff', borderRadius: 22, padding: 22, gap: 16, borderWidth: 1, borderColor: palette.border }}>{children}</View>; }
export function GamePage({ children, loading, error }: { children: ReactNode; loading?: boolean; error?: string | null }) {
  return <ScrollView style={{ flex: 1, backgroundColor: palette.background }} keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: 24, gap: 18, width: '100%', maxWidth: 1000, alignSelf: 'center', paddingBottom: 48 }}>{loading && <ActivityIndicator color={palette.primary} />}<NotificationBubble message={error} />{children}</ScrollView>;
}
export function Field({ label, value, onChange, numeric = false, ...props }: { label: string; value: string; onChange: (value: string) => void; numeric?: boolean } & Omit<TextInputProps, 'value' | 'onChange' | 'onChangeText'>) {
  return <View style={{ gap: 8 }}><Text style={{ fontWeight: '600', color: palette.ink }}>{label}</Text><TextInput accessibilityLabel={label} value={value} onChangeText={onChange} keyboardType={numeric ? 'numeric' : 'default'} placeholderTextColor={palette.muted} {...props} style={{ borderWidth: 1, borderColor: palette.border, backgroundColor: '#fff', color: palette.ink, padding: 14, borderRadius: 12, fontSize: 16 }} /></View>;
}
export function Choices({ values, value, onChange, disabled = false }: { values: string[]; value: string; onChange: (value: string) => void; disabled?: boolean }) {
  return <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{values.map(item => <ActionButton key={item} disabled={disabled} secondary={value !== item} title={`${value === item ? '✓ ' : ''}${item}`} onPress={() => onChange(item)} />)}</View>;
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
