import { TrainingScreen } from '../screens/TrainingScreen';
import { YouthAcademyScreen } from '../screens/YouthAcademyScreen';
import { TransferOffersScreen } from '../screens/TransferOffersScreen';
import { PlayerDetailsScreen } from '../screens/PlayerDetailsScreen';
import { MarketScreen } from '../screens/MarketScreen';
import { CalendarScreen } from '../screens/CalendarScreen';
import { SponsorsScreen } from '../screens/SponsorsScreen';
import { TicketingScreen } from '../screens/TicketingScreen';
import { BankScreen } from '../screens/BankScreen';
import { FinanceScreen } from '../screens/FinanceScreen';
import { StadiumScreen } from '../screens/StadiumScreen';
import { SquadScreen } from '../screens/SquadScreen';
import { ClubScreen } from '../screens/ClubScreen';
import { DashboardScreen } from '../screens/DashboardScreen';
import { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useAppStore } from '../stores/appStore';
import { SplashScreen } from '../screens/SplashScreen';
import { Button, Text, View } from 'react-native';
import { useClubStore } from '../stores/clubStore';
import { CreateClubScreen } from '../screens/CreateClubScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { AuthNavigator } from './AuthNavigator';
import { ProfileScreen } from '../screens/ProfileScreen';
import { useAuthStore } from '../stores/authStore';
import { RootStackParamList } from './types';
const Stack = createNativeStackNavigator<RootStackParamList>();
export function AppNavigator() {
  const { initialized, apiAvailable, initialize } = useAppStore();
  const auth = useAuthStore();
  const game = useClubStore();
  const loadClub = game.load;
  useEffect(() => { if (auth.user?.id) void loadClub(); }, [auth.user?.id, loadClub]);
  useEffect(() => {
    void initialize().then(() => useAuthStore.getState().restoreSession());
  }, [initialize]);
  return <SafeAreaProvider>
    {!initialized || !apiAvailable || !auth.initialized ? <SplashScreen /> : <NavigationContainer>
      {auth.authenticated ? (!game.data ? <View style={{ padding: 24 }}><Text>{game.error || 'Carregando clube…'}</Text><Button title="Tentar novamente" onPress={() => void game.load()} /><Button title="Sair" onPress={() => void auth.logout()} /></View> : !game.data.club ? <CreateClubScreen /> : <Stack.Navigator>
        <Stack.Screen name="Dashboard" component={DashboardScreen} options={{ title: 'LigaPro' }} />
        <Stack.Screen name="Club" component={ClubScreen} options={{ title: 'Clube' }} />
        <Stack.Screen name="Squad" component={SquadScreen} options={{ title: 'Plantel' }} />
        <Stack.Screen name="Stadium" component={StadiumScreen} options={{ title: 'Estádio' }} />
        <Stack.Screen name="Finance" component={FinanceScreen} options={{ title: 'Financeiro' }} />
        <Stack.Screen name="Bank" component={BankScreen} options={{ title: 'Banco' }} />
        <Stack.Screen name="Ticketing" component={TicketingScreen} options={{ title: 'Bilheteria' }} />
        <Stack.Screen name="Sponsors" component={SponsorsScreen} options={{ title: 'Patrocinadores' }} />
        <Stack.Screen name="Calendar" component={CalendarScreen} options={{ title: 'Calendário' }} />
        <Stack.Screen name="Training" component={TrainingScreen} options={{ title: 'Treinamento' }} />
        <Stack.Screen name="YouthAcademy" component={YouthAcademyScreen} options={{ title: 'Categorias de Base' }} />
        <Stack.Screen name="Market" component={MarketScreen} options={{ title: 'Mercado' }} />
        <Stack.Screen name="PlayerDetails" component={PlayerDetailsScreen} options={{ title: 'Jogador' }} />
        <Stack.Screen name="TransferOffers" component={TransferOffersScreen} options={{ title: 'Propostas' }} />
        <Stack.Screen name="Settings" component={SettingsScreen}
          options={{ title: 'Configurações' }} />
        <Stack.Screen name="Profile" component={ProfileScreen} options={{ title: 'Perfil' }} />
      </Stack.Navigator>) : <AuthNavigator />}
    </NavigationContainer>}
  </SafeAreaProvider>;
}
