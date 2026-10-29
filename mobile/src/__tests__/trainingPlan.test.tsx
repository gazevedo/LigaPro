import { act, fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import { TrainingPlanEditor } from '../components/TrainingPlanEditor';
import { TrainingPlan, trainingPlanService } from '../services/developmentService';
jest.mock('../services/developmentService', () => ({ trainingPlanService: { get: jest.fn(), save: jest.fn() } }));
const plan: TrainingPlan = { enabled: false, days: 7, skill: 'passing', intensity: 'normal', individual: {} };
beforeEach(() => { jest.resetAllMocks(); jest.mocked(trainingPlanService.get).mockResolvedValue(plan); });
test('plan edits are immediate, serialize requests and keep the latest choice', async () => {
  let finish!: (value: TrainingPlan) => void;
  jest.mocked(trainingPlanService.save).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })).mockImplementation(async value => value);
  await render(<TrainingPlanEditor players={[]} />);
  await fireEvent.press(await screen.findByText('Ativar plano automático'));
  expect(screen.getByText('Pausar plano automático')).toBeTruthy();
  await fireEvent.press(screen.getByRole('combobox', { name: 'Intensidade' }));
  await fireEvent.press(screen.getByText('Intenso · progresso e desgaste 3×'));
  expect(trainingPlanService.save).toHaveBeenCalledTimes(1);
  await act(async () => { finish({ ...plan, enabled: true }); });
  await waitFor(() => expect(trainingPlanService.save).toHaveBeenCalledTimes(2));
  expect(trainingPlanService.save).toHaveBeenLastCalledWith(expect.objectContaining({ enabled: true, intensity: 'intense' }));
});
test('save failure restores the confirmed plan and shows a dismissible message', async () => {
  jest.mocked(trainingPlanService.save).mockRejectedValue(new Error('Offline'));
  await render(<TrainingPlanEditor players={[]} />);
  await fireEvent.press(await screen.findByText('Ativar plano automático'));
  await screen.findByText(/A última configuração confirmada foi restaurada/);
  expect(screen.getByText('Ativar plano automático')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Fechar notificação' })).toBeTruthy();
});
