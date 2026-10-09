import { Text } from 'react-native';
export function PlayerStars({ count = 0 }: { count?: number }) {
  const stars = Math.max(0, Math.min(5, Math.floor(count)));
  return <Text numberOfLines={1} accessibilityLabel={`${stars} estrelas`} style={{ color: '#bd8506', fontSize: 11, letterSpacing: 0 }}>{'★'.repeat(stars)}{'☆'.repeat(5 - stars)}</Text>;
}
