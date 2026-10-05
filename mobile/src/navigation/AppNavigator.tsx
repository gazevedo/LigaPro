import { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useAppStore } from '../stores/appStore';
import { SplashScreen } from '../screens/SplashScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { AuthNavigator } from './AuthNavigator';
import { ProfileScreen } from '../screens/ProfileScreen';
import { useAuthStore } from '../stores/authStore';
import { RootStackParamList } from './types';
const Stack = createNativeStackNavigator<RootStackParamList>();
export function AppNavigator() {
  const { initialized, apiAvailable, initialize } = useAppStore();
  const auth = useAuthStore();
  useEffect(() => {
    void initialize().then(() => useAuthStore.getState().restoreSession());
  }, [initialize]);
  return <SafeAreaProvider>
    {!initialized || !apiAvailable || !auth.initialized ? <SplashScreen /> : <NavigationContainer>
      {auth.authenticated ? <Stack.Navigator>
        <Stack.Screen name="Home" component={HomeScreen} options={{ title: 'LigaPro' }} />
        <Stack.Screen name="Settings" component={SettingsScreen}
          options={{ title: 'Configurações' }} />
        <Stack.Screen name="Profile" component={ProfileScreen} options={{ title: 'Perfil' }} />
      </Stack.Navigator> : <AuthNavigator />}
    </NavigationContainer>}
  </SafeAreaProvider>;
}
