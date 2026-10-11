import { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { palette } from './GameUI';
export interface ComboBoxProps { label: string; value: string; options: { value: string; label: string }[]; onChange: (value: string) => void; disabled?: boolean; inline?: boolean }
export function ComboBox({ label, value, options, onChange, disabled = false, inline = false }: ComboBoxProps) {
  const [open, setOpen] = useState(false);
  return <View style={{ gap: 8, flexDirection: inline ? 'row' : 'column', alignItems: inline ? 'flex-start' : undefined }}>
    <Text style={{ color: palette.ink, fontWeight: '600', paddingTop: inline ? 14 : 0 }}>{label}</Text>
    <View style={{ flex: inline ? 1 : undefined, minWidth: 0 }}>
      <Pressable accessibilityRole="combobox" accessibilityLabel={label} accessibilityState={{ expanded: open, disabled }} disabled={disabled} onPress={() => setOpen(!open)} style={{ padding: 14, borderWidth: 1, borderColor: palette.border, borderRadius: 12, backgroundColor: '#fff', flexDirection: 'row', opacity: disabled ? .5 : 1 }}><Text style={{ flex: 1, color: palette.ink }}>{options.find(option => option.value === value)?.label ?? 'Selecione'}</Text><Text>{open ? '⌃' : '⌄'}</Text></Pressable>
      {open && !disabled && <ScrollView keyboardShouldPersistTaps="handled" style={{ maxHeight: 240, borderWidth: 1, borderColor: palette.border, borderRadius: 12, backgroundColor: '#fff' }}>{options.map(option => <Pressable key={option.value} accessibilityRole="button" accessibilityState={{ selected: option.value === value }} onPress={() => { setOpen(false); onChange(option.value); }} style={{ padding: 14, backgroundColor: option.value === value ? '#daf4e7' : '#fff' }}><Text style={{ color: palette.ink }}>{option.label}</Text></Pressable>)}</ScrollView>}
    </View>
  </View>;
}
