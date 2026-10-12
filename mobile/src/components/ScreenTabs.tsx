import { Pressable, ScrollView, Text, View } from 'react-native';
import { palette } from './GameUI';
export function ScreenTabs({ values, value, onChange, scrollable = false }: { values: string[]; value: string; onChange: (value: string) => void; scrollable?: boolean }) {
  const tabs = <View accessibilityRole="tablist" style={{ flexDirection: 'row', backgroundColor: '#fff', borderBottomWidth: 1, borderColor: palette.border }}>
    {values.map(label => <Pressable key={label} accessibilityRole="tab" accessibilityState={{ selected: value === label }} onPress={() => onChange(label)} style={{ flex: scrollable ? undefined : 1, minWidth: scrollable ? 88 : undefined, minHeight: 50, justifyContent: 'center', alignItems: 'center', borderBottomWidth: 3, borderBottomColor: value === label ? palette.primary : 'transparent', paddingHorizontal: scrollable ? 16 : 4 }}><Text style={{ color: value === label ? palette.primary : palette.muted, fontWeight: '700', textAlign: 'center' }}>{label}</Text></Pressable>)}
  </View>;
  return scrollable ? <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0, backgroundColor: '#fff' }} contentContainerStyle={{ paddingRight: 12 }}>{tabs}</ScrollView> : tabs;
}
