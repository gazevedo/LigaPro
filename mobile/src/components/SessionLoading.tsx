import { ActivityIndicator, Image, Text, View } from 'react-native';
import { GameBackground, palette } from './GameUI';

export function SessionLoading({ loading = true }: { loading?: boolean }) {
  return <GameBackground><View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, gap: 20 }}>
    <Image accessibilityLabel="Logotipo LigaPro" source={require('../../assets/brand/logo-ligapro.png')} resizeMode="contain" style={{ width: 250, height: 110 }} />
    {loading && <>
      <ActivityIndicator accessibilityLabel="Restaurando sessão" color={palette.primary} size="large" />
      <Text accessibilityLiveRegion="polite" style={{ color: palette.ink, fontSize: 16 }}>Entrando…</Text>
    </>}
  </View></GameBackground>;
}
