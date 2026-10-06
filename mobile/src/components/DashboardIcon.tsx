import { Image, View } from 'react-native';

const positions = {
  history: 0,
  club: 1,
  statistics: 2,
  tactics: 3,
  squad: 4,
  stadium: 5,
  finance: 6,
  calendar: 7,
  market: 8,
  training: 9,
  youth: 10,
  profile: 11,
  settings: 12,
} as const;
export type DashboardIconName = keyof typeof positions;
const sheet = require('../../assets/dashboard/icons.png');

export function DashboardIcon({ name, size = 72 }: { name: DashboardIconName; size?: number }) {
  const position = positions[name];
  return <View pointerEvents="none" style={{ width: size, height: size, overflow: 'hidden' }}>
    <Image source={sheet} accessible={false} resizeMode="stretch" style={{
      position: 'absolute',
      width: size * 4,
      height: size * 4,
      left: -(position % 4) * size,
      top: -Math.floor(position / 4) * size,
    }} />
  </View>;
}
