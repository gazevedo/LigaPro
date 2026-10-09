import { CommonActions } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Modal, Pressable, Text, View } from 'react-native';
import { RootStackParamList } from '../navigation/types';
import { PlayerDetailsScreen } from '../screens/PlayerDetailsScreen';
import { palette } from './GameUI';
export function PlayerPopup({ id, onClose, navigation }: { id: string | null; onClose: () => void; navigation: Pick<NativeStackNavigationProp<RootStackParamList>, 'dispatch'> }) {
  if (!id) return null;
  const detailNavigation = { ...navigation, navigate: (name: string, params?: object) => { onClose(); navigation.dispatch(CommonActions.navigate(name, params)); } } as NativeStackNavigationProp<RootStackParamList, 'PlayerDetails'>;
  return <Modal visible transparent animationType="fade" onRequestClose={onClose}>
    <View style={{ flex: 1, backgroundColor: '#14243a88', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <View style={{ width: '100%', maxWidth: 650, height: '90%', backgroundColor: '#fff', borderRadius: 24, overflow: 'hidden' }}>
        <Pressable accessibilityRole="button" accessibilityLabel="Fechar detalhes do jogador" onPress={onClose} style={{ alignSelf: 'flex-end', padding: 16 }}><Text style={{ color: palette.primary, fontWeight: '700' }}>Fechar ✕</Text></Pressable>
        <PlayerDetailsScreen navigation={detailNavigation} route={{ key: `player-${id}`, name: 'PlayerDetails', params: { id } }} />
      </View>
    </View>
  </Modal>;
}
