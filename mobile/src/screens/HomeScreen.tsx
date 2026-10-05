import { Button, StyleSheet, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;
export function HomeScreen({ navigation }: Props) {
  return <View style={styles.container}>
    <Button title="Novo Jogo" disabled />
    <Button title="Carregar Jogo" disabled />
    <Button title="Configurações" onPress={() => navigation.navigate('Settings')} />
  </View>;
}
const styles = StyleSheet.create({ container: { flex: 1, padding: 24, gap: 16 } });
