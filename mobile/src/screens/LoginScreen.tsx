import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { AuthForm } from '../components/AuthForm';
import { AuthStackParamList } from '../navigation/types';
type Props = NativeStackScreenProps<AuthStackParamList, 'Login'>;
export function LoginScreen({ navigation }: Props) {
  return <AuthForm background={require('../../assets/dashboard/login-stadium.png')} onCreateAccount={() => navigation.navigate('Register')} />;
}
