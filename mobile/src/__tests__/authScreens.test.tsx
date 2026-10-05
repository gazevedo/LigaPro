import { render, fireEvent, screen } from '@testing-library/react-native';
import { AuthForm } from '../components/AuthForm';
import { ProfileScreen } from '../screens/ProfileScreen';
import { useAuthStore } from '../stores/authStore';
const login = jest.fn(async () => undefined);
const register = jest.fn(async () => undefined);
const google = jest.fn(async () => undefined);
const logout = jest.fn(async () => undefined);
beforeEach(() => {
  jest.clearAllMocks(); useAuthStore.setState({ loading: false, error: null, user: null,
    login, register, loginWithGoogle: google, logout });
});
test('login normalizes email and submits credentials', async () => {
  await render(<AuthForm />);
  await fireEvent.changeText(screen.getByLabelText('E-mail'), ' USER@example.com ');
  await fireEvent.changeText(screen.getByLabelText('Senha'), 'password123');
  await fireEvent.press(screen.getByText('Entrar'));
  expect(login).toHaveBeenCalledWith('user@example.com', 'password123');
});
test('registration rejects mismatched confirmation', async () => {
  await render(<AuthForm register />);
  await fireEvent.changeText(screen.getByLabelText('Nome'), 'User');
  await fireEvent.changeText(screen.getByLabelText('E-mail'), 'user@example.com');
  await fireEvent.changeText(screen.getByLabelText('Senha'), 'password123');
  await fireEvent.changeText(screen.getByLabelText('Confirmar senha'), 'different');
  await fireEvent.press(screen.getByText('Criar conta'));
  expect(screen.getByText('As senhas não conferem.')).toBeTruthy();
  expect(register).not.toHaveBeenCalled();
});
test('registration submits matching passwords', async () => {
  await render(<AuthForm register />);
  await fireEvent.changeText(screen.getByLabelText('Nome'), 'User');
  await fireEvent.changeText(screen.getByLabelText('E-mail'), 'user@example.com');
  await fireEvent.changeText(screen.getByLabelText('Senha'), 'password123');
  await fireEvent.changeText(screen.getByLabelText('Confirmar senha'), 'password123');
  await fireEvent.press(screen.getByText('Criar conta'));
  expect(register).toHaveBeenCalledWith('User', 'user@example.com', 'password123');
});
test('login exposes Google and account creation actions', async () => {
  const navigate = jest.fn(); await render(<AuthForm onCreateAccount={navigate} />);
  await fireEvent.press(screen.getByText('Continuar com Google')); expect(google).toHaveBeenCalledTimes(1);
  await fireEvent.press(screen.getByText('Criar conta')); expect(navigate).toHaveBeenCalledTimes(1);
  expect(screen.getByText('Esqueci minha senha')).toBeTruthy();
});
test('profile signs out without editing identity', async () => {
  await render(<ProfileScreen />); await fireEvent.press(screen.getByText('Sair'));
  expect(logout).toHaveBeenCalledTimes(1);
});
