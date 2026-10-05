import { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useAppStore } from '../stores/appStore';
import { SplashScreen } from '../screens/SplashScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { RootStackParamList } from './types';
const Stack = createNativeStackNavigator<RootStackParamList>();
export function AppNavigator() {
  const { initialized, apiAvailable, initialize } = useAppStore();
  useEffect(() => { void initialize(); }, [initialize]);
  return <SafeAreaProvider>
    {!initialized || !apiAvailable ? <SplashScreen /> : <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Home" component={HomeScreen} options={{ title: 'LigaPro' }} />
        <Stack.Screen name="Settings" component={SettingsScreen}
          options={{ title: 'Configurações' }} />
      </Stack.Navigator>
    </NavigationContainer>}
  </SafeAreaProvider>;
}
