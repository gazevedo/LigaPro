import { createElement, useId } from 'react';
import { Text, View } from 'react-native';
import type { ComboBoxProps } from './ComboBox';
import { palette } from './GameUI';

export function ComboBox({ label, value, options, onChange, disabled = false, inline = false }: ComboBoxProps) {
  const id = useId();
  return <View style={{ gap: 8, flexDirection: inline ? 'row' : 'column', alignItems: inline ? 'center' : undefined }}>
    <Text nativeID={`${id}-label`} style={{ color: palette.ink, fontWeight: '600', flex: inline ? 1 : undefined, minWidth: 0 }}>{inline ? `${label}:` : label}</Text>
    {createElement('select', {
      id, value, disabled, 'aria-labelledby': `${id}-label`,
      onChange: (event: React.ChangeEvent<HTMLSelectElement>) => onChange(event.target.value),
      style: { flex: inline ? '1 1 0%' : undefined, minWidth: 0, boxSizing: 'border-box', width: inline ? undefined : '100%', padding: 6, border: `1px solid ${palette.border}`, borderRadius: 2, backgroundColor: '#fff', color: palette.ink, fontFamily: 'system-ui, sans-serif', fontSize: 14, opacity: disabled ? .5 : 1 },
    }, options.map(option => createElement('option', { key: option.value, value: option.value }, option.label)))}
  </View>;
}
