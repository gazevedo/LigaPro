import { ActionButton as Button, GamePage } from '../components/GameUI';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;
export function HomeScreen({ navigation }: Props) {
  return <GamePage>
    <Button title="Novo Jogo" disabled onPress={() => undefined} />
    <Button title="Carregar Jogo" disabled onPress={() => undefined} />
    <Button title="Configurações" onPress={() => navigation.navigate('Settings')} />
  </GamePage>;
}
