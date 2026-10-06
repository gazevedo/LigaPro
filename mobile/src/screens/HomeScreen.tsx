import { ActionButton as Button } from '../components/GameUI';
import { StyleSheet, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;
export function HomeScreen({ navigation }: Props) {
  return <View style={styles.container}>
    <Button title="Novo Jogo" disabled onPress={() => undefined} />
    <Button title="Carregar Jogo" disabled onPress={() => undefined} />
    <Button title="Perfil" onPress={() => navigation.navigate('Profile')} />
    <Button title="Configurações" onPress={() => navigation.navigate('Settings')} />
  </View>;
}
const styles = StyleSheet.create({ container: { flex: 1, padding: 24, gap: 16 } });
