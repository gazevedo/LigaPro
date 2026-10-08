import { HeaderActions } from '../components/HeaderActions';
import { InboxScreen } from '../screens/InboxScreen';
import { MatchLiveScreen } from '../screens/MatchLiveScreen';
import { CompetitionsScreen } from '../screens/CompetitionsScreen';
import { MatchReportScreen } from '../screens/MatchReportScreen';
import { TacticsScreen } from '../screens/TacticsScreen';
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
import { ActivityIndicator, Image, Text, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useAppStore } from '../stores/appStore';
import { ActionButton, GameBackground, GamePage, palette } from '../components/GameUI';
import { NotificationHost } from '../components/NotificationHost';
import { useClubStore } from '../stores/clubStore';
import { CreateClubScreen } from '../screens/CreateClubScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { AuthNavigator } from './AuthNavigator';
import { useAuthStore } from '../stores/authStore';
import { RootStackParamList } from './types';
const Stack = createNativeStackNavigator<RootStackParamList>();
export function AppNavigator() {
  const { initialized, loading, apiAvailable, error, initialize } = useAppStore();
  const auth = useAuthStore();
  const game = useClubStore();
  const loadClub = game.load;
  useEffect(() => { if (auth.user?.id) void loadClub(); }, [auth.user?.id, loadClub]);
  useEffect(() => {
    void initialize().then(() => useAuthStore.getState().restoreSession());
  }, [initialize]);
  return <SafeAreaProvider>
    {!initialized || !apiAvailable || !auth.initialized ? <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, gap: 16, backgroundColor: '#fff' }}>
      <Image accessibilityLabel="Logotipo LigaPro" source={require('../../assets/brand/logo-ligapro.png')} resizeMode="contain" style={{ width: '100%', maxWidth: 308, height: 154 }} />
      {loading || auth.loading || !initialized ? <ActivityIndicator accessibilityLabel="Carregando aplicativo" style={{ position: 'absolute', top: '50%', marginTop: 93 }} /> : error || auth.error ? <>
        <Text>{error ? 'Servidor em manutenção, tente mais tarde.' : auth.error}</Text>
        <ActionButton title="Tentar novamente" onPress={() => { void initialize().then(() => useAuthStore.getState().restoreSession()); }} />
      </> : <ActivityIndicator accessibilityLabel="Restaurando sessão" style={{ position: 'absolute', top: '50%', marginTop: 93 }} />}
    </View> : <NavigationContainer>
      {auth.authenticated ? <GameBackground>{(!game.data ? <GamePage loading={game.loading} error={game.error}><ActionButton title="Tentar novamente" disabled={game.loading} onPress={() => void game.load()} /><ActionButton secondary title="Sair" onPress={() => void auth.logout()} /></GamePage> : !game.data.club ? <CreateClubScreen /> : <Stack.Navigator screenOptions={{ headerStyle: { backgroundColor: '#fff' }, headerTintColor: palette.ink, headerShadowVisible: false, contentStyle: { backgroundColor: 'transparent' } }}>
        <Stack.Screen name="Dashboard" component={DashboardScreen} options={({ navigation }) => ({ title: 'LigaPro', headerTitleAlign: 'left', headerTitle: () => <Image accessibilityLabel="Logotipo LigaPro" source={require('../../assets/brand/logo-ligapro.png')} resizeMode="contain" style={{ width: 120, height: 44 }} />, headerRight: () => <HeaderActions focused={navigation.isFocused} openInbox={() => navigation.navigate('Inbox')} openSettings={() => navigation.navigate('Settings')} /> })} />
        <Stack.Screen name="Inbox" component={InboxScreen} options={{ title: 'Correio' }} />
        <Stack.Screen name="Club" component={ClubScreen} options={{ title: 'Clube' }} />
        <Stack.Screen name="Competitions" component={CompetitionsScreen} options={{ title: 'Campeonatos' }} />
        <Stack.Screen name="MatchLive" component={MatchLiveScreen} options={{ title: 'Partida ao vivo' }} />
      <Stack.Screen name="MatchReport" component={MatchReportScreen} options={{ title: 'Relatório da partida' }} />
        <Stack.Screen name="Tactics" component={TacticsScreen} options={{ title: 'Táticas' }} />
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
      </Stack.Navigator>)}</GameBackground> : <AuthNavigator />}
    </NavigationContainer>}
    <NotificationHost />
  </SafeAreaProvider>;
}
