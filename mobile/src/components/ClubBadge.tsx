import { Text, View } from 'react-native';
import { Badge } from '../types/game';
export function ClubBadge({ badge, name = 'Liga Pro', size = 88 }: { badge?: Badge; name?: string; size?: number }) {
  const initials = name.trim().split(/\s+/).slice(0, 2).map(word => word[0]).join('').toUpperCase() || 'LP';
  const accent = badge?.accent || '#dbeafe';
  const pattern = badge?.pattern || 'stripe';
  return <View accessibilityLabel={`Escudo ${badge?.name || ''} ${name}`} style={{ width: size, height: size * 1.15, overflow: 'hidden', backgroundColor: badge?.color || '#2563eb', borderWidth: 3, borderColor: accent, borderTopLeftRadius: size * 0.22, borderTopRightRadius: size * 0.22, borderBottomLeftRadius: size * 0.48, borderBottomRightRadius: size * 0.48, alignItems: 'center', justifyContent: 'center' }}>
    {pattern !== 'plain' && <View style={{ position: 'absolute', top: 0, bottom: 0, width: size * 0.2, backgroundColor: accent, opacity: 0.3 }} />}
    {pattern === 'cross' && <View style={{ position: 'absolute', left: 0, right: 0, height: size * 0.2, backgroundColor: accent, opacity: 0.3 }} />}
    <Text style={{ color: accent, fontSize: size * 0.18 }}>★</Text><Text style={{ color: '#fff', fontWeight: '900', fontSize: size * 0.28 }}>{initials}</Text><Text style={{ color: accent, fontSize: size * 0.12, letterSpacing: 2 }}>FC</Text>
  </View>;
}
