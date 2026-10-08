import { Image, Text, View } from 'react-native';

const icons = {
  history: require('../../assets/dashboard/historico.png'),
  club: require('../../assets/dashboard/clube.png'),
  statistics: require('../../assets/dashboard/estatisticas.png'),
  tactics: require('../../assets/dashboard/tatica.png'),
  squad: require('../../assets/dashboard/plantel.png'),
  stadium: require('../../assets/dashboard/estadio.png'),
  finance: require('../../assets/dashboard/financeiro.png'),
  calendar: require('../../assets/dashboard/calendario.png'),
  market: require('../../assets/dashboard/mercado.png'),
  training: require('../../assets/dashboard/treinamento.png'),
  youth: require('../../assets/dashboard/categoria_de_base.png'),
  profile: require('../../assets/dashboard/perfil.png'),
  settings: require('../../assets/dashboard/configuracao.png'),
} as const;
export type DashboardIconName = keyof typeof icons | 'competitions';

export function DashboardIcon({ name, size = 72 }: { name: DashboardIconName; size?: number }) {
  if (name === 'competitions') return <View pointerEvents="none" style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}><Text style={{ fontSize: size * 0.7 }}>🏆</Text></View>;
  return <View pointerEvents="none" style={{ width: size, height: size }}>
    <Image source={icons[name]} accessible={false} resizeMode="contain"
      style={{ width: size, height: size }} />
  </View>;
}
