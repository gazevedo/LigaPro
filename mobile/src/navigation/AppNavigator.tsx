import { HeaderActions } from '../components/HeaderActions';
import { InboxScreen } from '../screens/InboxScreen';
import { MatchLiveScreen } from '../screens/MatchLiveScreen';
import { CompetitionsScreen } from '../screens/CompetitionsScreen';
import { MatchReportScreen } from '../screens/MatchReportScreen';
import { TacticsScreen } from '../screens/TacticsScreen';
import { TrainingScreen } from '../screens/TrainingScreen';
import { YouthAcademyScreen } from '../screens/YouthAcademyScreen';
import { TransferOffersScreen } from '../screens/TransferOffersScreen';
import { PlayerNegotiationScreen } from '../screens/PlayerNegotiationScreen';
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
import { useEffect, useRef } from 'react';
import { BackHandler, Image, Platform, View } from 'react-native';
import { DefaultTheme, NavigationContainer, useNavigationContainerRef } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useAppStore } from '../stores/appStore';
import { GameBackground, NotificationBubble, palette } from '../components/GameUI';
import { SwipeBack } from '../components/SwipeBack';
import { ConnectionRetry } from '../components/ConnectionRetry';
import { NotificationHost } from '../components/NotificationHost';
import { useClubStore } from '../stores/clubStore';
import { CreateClubScreen } from '../screens/CreateClubScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { AuthNavigator } from './AuthNavigator';
import { useAuthStore } from '../stores/authStore';
import { RootStackParamList } from './types';
import { registerBrowserBack } from './browserBack';
import { startGameDataRefresh } from '../services/prefetchService';
import { hideStartupSplash } from '../services/startupSplash';
const Stack = createNativeStackNavigator<RootStackParamList>();
const navigationTheme = { ...DefaultTheme, colors: { ...DefaultTheme.colors, background: 'transparent' } };
export function AppNavigator() {
  const navigationRef = useNavigationContainerRef<RootStackParamList>();
  const browserBack = useRef<ReturnType<typeof registerBrowserBack> | null>(null);
  const { apiAvailable, error, initialize } = useAppStore();
  const auth = useAuthStore();
  const game = useClubStore();
  const waitingForClub = auth.authenticated && !game.data;
  const startupError = error || (waitingForClub ? game.error : null);
  const startupReady = (auth.initialized && (!auth.authenticated || !!game.data)) || !!startupError;
  useEffect(() => { if (startupReady) void hideStartupSplash(); }, [startupReady]);
  const loadClub = game.ensure;
  const clubId = game.data?.club?.id;
  useEffect(() => {
    if (!auth.authenticated || !clubId) return;
    return startGameDataRefresh(clubId, () => useAuthStore.getState().authenticated && useClubStore.getState().data?.club?.id === clubId);
  }, [auth.authenticated, auth.user?.id, clubId]);
  useEffect(() => {
    if (Platform.OS !== 'web' || typeof window === 'undefined') return;
    const handler = registerBrowserBack(window,
      () => navigationRef.isReady() && navigationRef.canGoBack(),
      () => navigationRef.goBack());
    browserBack.current = handler;
    return () => { handler.dispose(); browserBack.current = null; };
  }, [navigationRef]);
  useEffect(() => { if (auth.user?.id) void loadClub(); }, [auth.user?.id, loadClub]);
  useEffect(() => {
    void useAuthStore.getState().restoreSession();
    void initialize();
  }, [initialize]);
  useEffect(() => {
    const subscription = BackHandler.addEventListener('hardwareBackPress', () => {
      if (!auth.authenticated) return false;
      if (navigationRef.isReady() && navigationRef.canGoBack()) navigationRef.goBack();
      return true;
    });
    return () => subscription.remove();
  }, [auth.authenticated, navigationRef]);
  return <SafeAreaProvider>
    <SwipeBack canGoBack={() => navigationRef.isReady() && navigationRef.canGoBack()} goBack={() => navigationRef.goBack()}><NavigationContainer ref={navigationRef} theme={navigationTheme} onReady={() => browserBack.current?.sync(navigationRef.getRootState())} onStateChange={state => browserBack.current?.sync(state)}>
      {auth.authenticated && game.data ? <GameBackground>{(game.data && !game.data.club ? <CreateClubScreen /> : <Stack.Navigator screenOptions={{ headerTitleAlign: 'left', headerBackButtonDisplayMode: 'minimal', headerStyle: { backgroundColor: '#fff' }, headerTintColor: palette.ink, headerShadowVisible: false, contentStyle: { backgroundColor: 'transparent' } }}>
        <Stack.Screen name="Dashboard" component={DashboardScreen} options={({ navigation }) => ({ title: 'LigaPro', headerTitleAlign: 'left', headerTitle: () => <Image accessibilityLabel="Logotipo LigaPro" source={require('../../assets/brand/logo-ligapro.png')} resizeMode="contain" style={{ width: 120, height: 44 }} />, headerRight: () => <HeaderActions focused={navigation.isFocused} openInbox={() => navigation.navigate('Inbox')} /> })} />
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
        <Stack.Screen name="PlayerNegotiation" component={PlayerNegotiationScreen} options={{ title: 'Negociação e contrato' }} />
        <Stack.Screen name="PlayerDetails" component={PlayerDetailsScreen} options={{ title: 'Jogador' }} />
        <Stack.Screen name="TransferOffers" component={TransferOffersScreen} options={{ title: 'Propostas' }} />
        <Stack.Screen name="Settings" component={SettingsScreen}
          options={{ title: 'Configurações' }} />
      </Stack.Navigator>)}</GameBackground> : auth.initialized && !auth.authenticated ? <AuthNavigator /> : null}
    </NavigationContainer></SwipeBack>
    {startupError && <View style={{ padding: 12, gap: 8 }}>
      <NotificationBubble message={startupError} />
      <ConnectionRetry key={startupError} onRetry={() => {
        if (apiAvailable && waitingForClub) { void loadClub(); return; }
        void initialize().then(() => {
          if (useAppStore.getState().apiAvailable) return useAuthStore.getState().restoreSession();
        });
      }} />
    </View>}
    <NotificationHost />
  </SafeAreaProvider>;
}
