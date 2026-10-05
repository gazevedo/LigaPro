import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { LoginScreen } from '../screens/LoginScreen';
import { RegisterScreen } from '../screens/RegisterScreen';
import { AuthStackParamList } from './types';
const Stack = createNativeStackNavigator<AuthStackParamList>();
export function AuthNavigator() {
  return <Stack.Navigator>
    <Stack.Screen name="Login" component={LoginScreen} options={{ title: 'Entrar' }} />
    <Stack.Screen name="Register" component={RegisterScreen} options={{ title: 'Criar conta' }} />
  </Stack.Navigator>;
}
