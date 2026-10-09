import { Pressable, Text, View } from 'react-native';
import { palette } from './GameUI';
export function ScreenTabs({ values, value, onChange }: { values: string[]; value: string; onChange: (value: string) => void }) {
  return <View accessibilityRole="tablist" style={{ flexDirection: 'row', backgroundColor: '#fff', borderBottomWidth: 1, borderColor: palette.border }}>
    {values.map(label => <Pressable key={label} accessibilityRole="tab" accessibilityState={{ selected: value === label }} onPress={() => onChange(label)} style={{ flex: 1, minHeight: 50, justifyContent: 'center', alignItems: 'center', borderBottomWidth: 3, borderBottomColor: value === label ? palette.primary : 'transparent', paddingHorizontal: 4 }}><Text style={{ color: value === label ? palette.primary : palette.muted, fontWeight: '700', textAlign: 'center' }}>{label}</Text></Pressable>)}
  </View>;
}
