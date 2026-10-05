import { render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { TrainingScreen } from '../screens/TrainingScreen';
import { YouthAcademyScreen } from '../screens/YouthAcademyScreen';
import { developmentService } from '../services/developmentService';
import { useAuthStore } from '../stores/authStore';
jest.mock('../services/developmentService', () => ({ developmentService: {
  training: jest.fn(), youth: jest.fn(), train: jest.fn(), promote: jest.fn(),
} }));
const player = { id: 'p1', name: 'Pedro Silva', age: 21, position: 'MID', strength: 50,
  overall: 50, training_level: 99, country_id: 'BR', value: 100000,
  owner_club_id: 'c1', current_club_id: 'c1' };
let accountNumber = 0;
beforeEach(() => {
  jest.clearAllMocks();
  useAuthStore.setState({ user: { id: String(++accountNumber), name: 'Manager', email: 'm@example.com', created_at: '', updated_at: '', last_login_at: null, auth_provider: 'local', avatar_url: null, email_verified: false, active: true } });
});
test('training uses server strength and reloads after each valid click', async () => {
  jest.mocked(developmentService.training).mockResolvedValueOnce([player])
    .mockResolvedValueOnce([{ ...player, strength: 51, overall: 51, training_level: 0 }]);
  jest.mocked(developmentService.train).mockResolvedValue({ ...player, strength: 51 });
  await render(<TrainingScreen />);
  await screen.findByText('Força: 50 · Treino: 99/100');
  await fireEvent.press(screen.getByText('Treinar Pedro Silva'));
  await screen.findByText('Força: 51 · Treino: 0/100');
  expect(developmentService.train).toHaveBeenCalledWith('p1');
});
test('training displays rejection without changing the player', async () => {
  jest.mocked(developmentService.training).mockResolvedValue([player]);
  jest.mocked(developmentService.train).mockRejectedValue(new Error('Jogador aposentado.'));
  await render(<TrainingScreen />);
  await fireEvent.press(await screen.findByText('Treinar Pedro Silva'));
  await screen.findByText('Jogador aposentado.');
  expect(screen.getByText('Força: 50 · Treino: 99/100')).toBeTruthy();
});
test('youth permits promotion at eighteen and reloads the academy', async () => {
  const underage = { ...player, id: 'young', name: 'Lucas Alves', age: 17 };
  jest.mocked(developmentService.youth).mockResolvedValueOnce([underage, { ...player, age: 18 }])
    .mockResolvedValueOnce([underage]);
  jest.mocked(developmentService.promote).mockResolvedValue(player);
  await render(<YouthAcademyScreen />);
  expect(await screen.findByRole('button', { name: 'Promover Lucas Alves' })).toBeDisabled();
  await fireEvent.press(screen.getByText('Promover Pedro Silva'));
  await waitFor(() => expect(developmentService.promote).toHaveBeenCalledWith('p1'));
  await waitFor(() => expect(screen.queryByText('Promover Pedro Silva')).toBeNull());
});
