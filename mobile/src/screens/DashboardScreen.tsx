import { Button, Text } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useClubStore } from '../stores/clubStore';
import { GamePage } from '../components/GameUI';
export function DashboardScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'Dashboard'>) {
  const club = useClubStore(state => state.data?.club);
  return <GamePage><Text style={{ fontSize: 24 }}>{club?.name}</Text>
    <Button title="Clube" onPress={() => club && navigation.navigate('Club', { id: club.id })} />
    <Button title="Táticas" onPress={() => navigation.navigate('Tactics')} />
    <Button title="Plantel" onPress={() => navigation.navigate('Squad')} />
    <Button title="Estádio" onPress={() => navigation.navigate('Stadium')} />
    <Button title="Financeiro" onPress={() => navigation.navigate('Finance')} />
    <Button title="Calendário" onPress={() => navigation.navigate('Calendar')} />
    <Button title="Mercado" onPress={() => navigation.navigate('Market')} />
    <Button title="Treinamento" onPress={() => navigation.navigate('Training')} />
    <Button title="Categorias de Base" onPress={() => navigation.navigate('YouthAcademy')} />
    <Button title="Perfil" onPress={() => navigation.navigate('Profile')} />
    <Button title="Configurações" onPress={() => navigation.navigate('Settings')} />
  </GamePage>;
}
