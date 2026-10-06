import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { AuthForm } from '../components/AuthForm';
import { AuthStackParamList } from '../navigation/types';
export function RegisterScreen({ navigation }: NativeStackScreenProps<AuthStackParamList, 'Register'>) { return <AuthForm register onLogin={() => navigation.navigate('Login')} />; }
