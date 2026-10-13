import { Image, Pressable, Text, View } from 'react-native';
import { StadiumSector } from '../types/game';
import { palette } from './GameUI';
const positions: Record<string, { left: `${number}%`; top: `${number}%`; label: string }> = {
  lower_north: { left: '58%', top: '22%', label: 'Norte inf.' }, upper_north: { left: '35%', top: '7%', label: 'Norte sup.' },
  lower_east: { left: '75%', top: '40%', label: 'Leste inf.' }, upper_east: { left: '88%', top: '60%', label: 'Leste sup.' },
  lower_south: { left: '60%', top: '75%', label: 'Sul inf.' }, upper_south: { left: '33%', top: '86%', label: 'Sul sup.' },
  lower_west: { left: '25%', top: '40%', label: 'Oeste inf.' }, upper_west: { left: '12%', top: '60%', label: 'Oeste sup.' },
  vip: { left: '44%', top: '67%', label: 'Premium' }, skybox: { left: '60%', top: '94%', label: 'Skybox' },
};
export function StadiumModel({ sectors, open }: { sectors: StadiumSector[]; open: (sector: StadiumSector) => void }) {
  return <View style={{ width: '100%', aspectRatio: 1.5 }}>
    <Image source={require('../../assets/stadium/sector-map.png')} resizeMode="contain" accessibilityLabel="Mapa do estádio com arquibancadas inferiores, superiores, premium e skyboxes" style={{ width: '100%', height: '100%' }} />
    {sectors.map(sector => {
      const position = positions[sector.id];
      if (!position) return null;
      return <Pressable key={sector.id} accessibilityRole="button" accessibilityLabel={`Setor ${sector.name}`} accessibilityState={{ disabled: !sector.available }} disabled={!sector.available} onPress={() => open(sector)} hitSlop={6} style={{ position: 'absolute', left: position.left, top: position.top, transform: [{ translateX: -27 }, { translateY: -12 }], minWidth: 54, paddingHorizontal: 4, paddingVertical: 5, alignItems: 'center', borderRadius: 7, borderWidth: 1, borderColor: sector.available ? '#fff' : palette.border, backgroundColor: sector.available ? '#fffffff2' : '#e2e8f0e6' }}><Text style={{ color: sector.available ? palette.ink : palette.muted, fontSize: 9, fontWeight: '800' }}>{position.label}</Text></Pressable>;
    })}
  </View>;
}
export function FacilityIcon({ tile = 0, dimmed = false }: { tile?: number; dimmed?: boolean }) {
  const size = 52;
  return <View style={{ width: size, height: size, overflow: 'hidden', opacity: dimmed ? .4 : 1 }}><Image accessible={false} source={require('../../assets/stadium/facilities-atlas.png')} style={{ position: 'absolute', width: size * 4, height: size * 4, left: -(tile % 4) * size, top: -Math.floor(tile / 4) * size }} /></View>;
}
