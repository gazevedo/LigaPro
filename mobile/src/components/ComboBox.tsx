import { useState } from 'react';
import { Modal, Pressable, ScrollView, Text, View } from 'react-native';
import { palette } from './GameUI';
export function ComboBox({ label, value, options, onChange, disabled = false }: { label: string; value: string; options: { value: string; label: string }[]; onChange: (value: string) => void; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  return <View style={{ gap: 8 }}>
    <Text style={{ color: palette.ink, fontWeight: '600' }}>{label}</Text>
    <Pressable accessibilityRole="combobox" accessibilityLabel={label} accessibilityState={{ expanded: open, disabled }} disabled={disabled} onPress={() => setOpen(true)} style={{ padding: 14, borderWidth: 1, borderColor: palette.border, borderRadius: 12, backgroundColor: '#fff', flexDirection: 'row', opacity: disabled ? .5 : 1 }}><Text style={{ flex: 1, color: palette.ink }}>{options.find(option => option.value === value)?.label ?? 'Selecione'}</Text><Text>⌄</Text></Pressable>
    <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#14243a88', padding: 24 }}>
        <View style={{ width: '100%', maxWidth: 450, maxHeight: '80%', backgroundColor: '#fff', borderRadius: 20, padding: 20, gap: 12 }}>
          <Text style={{ fontSize: 18, fontWeight: '700', color: palette.ink }}>{label}</Text>
          <ScrollView keyboardShouldPersistTaps="handled">{options.map(option => <Pressable key={option.value} accessibilityRole="button" accessibilityState={{ selected: option.value === value }} onPress={() => { setOpen(false); onChange(option.value); }} style={{ padding: 16, backgroundColor: option.value === value ? '#daf4e7' : '#fff', borderRadius: 10 }}><Text style={{ color: palette.ink }}>{option.label}</Text></Pressable>)}</ScrollView>
          <Pressable accessibilityRole="button" onPress={() => setOpen(false)} style={{ padding: 12, alignItems: 'center' }}><Text style={{ color: palette.primary, fontWeight: '700' }}>Cancelar</Text></Pressable>
        </View>
      </View>
    </Modal>
  </View>;
}
