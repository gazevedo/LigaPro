import { act, fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { SquadScreen } from '../screens/SquadScreen';
import { useSquadStore } from '../stores/squadStore';
import { useNotificationStore } from '../stores/notificationStore';
import { squadService } from '../services/squadService';
import { Player } from '../types/game';

jest.mock('../components/useScreenRefresh', () => ({ useScreenRefresh: jest.fn() }));
jest.mock('../components/PlayerPopup', () => ({ PlayerPopup: () => null }));
jest.mock('../services/squadService', () => ({ squadService: { get: jest.fn(), shirtNumber: jest.fn() } }));
const first: Player = { id: 'one', name: 'Pedro', position: 'ATT', age: 22, overall: 60, value: 10000, country_id: 'BR', owner_club_id: 'club', current_club_id: 'club', shirt_number: 8 };
const second: Player = { ...first, id: 'two', name: 'Paulo', shirt_number: 9 };
const props = { navigation: { navigate: jest.fn() } } as unknown as NativeStackScreenProps<RootStackParamList, 'Squad'>;
const press = (name: string) => fireEvent.press(screen.getByRole('button', { name }), { stopPropagation: jest.fn() });
beforeEach(() => {
  jest.clearAllMocks(); useSquadStore.getState().reset(); useNotificationStore.getState().clear();
  useSquadStore.setState({ data: { players: [first, second], lineup: { formation: '4-4-2', starters: [], reserves: [] }, formations: {} } });
});

test('shirt column precedes position, contract has a text heading and duplicate choice stays red', async () => {
  await render(<SquadScreen {...props} />);
  expect(screen.getByText('Camisa')).toBeTruthy();
  expect(screen.getByText('Contrato')).toBeTruthy();
  await press('Editar camisa de Pedro');
  await fireEvent.changeText(screen.getByLabelText('Número da camisa'), '9');
  expect(screen.getByLabelText('Número da camisa')).toHaveStyle({ color: '#dc2626' });
  await press('Salvar número');
  expect(squadService.shirtNumber).not.toHaveBeenCalled();
  expect(screen.getByText('Este número de camisa já está em uso no plantel.')).toBeTruthy();
});

test('legacy duplicate shirts stay red until a unique number is saved', async () => {
  useSquadStore.setState(state => ({ data: { ...state.data!, players: [first, { ...second, shirt_number: 8 }] } }));
  jest.mocked(squadService.shirtNumber).mockResolvedValue({ ...first, shirt_number: 10 });
  await render(<SquadScreen {...props} />);
  expect(screen.getAllByText('8')).toHaveLength(2);
  for (const number of screen.getAllByText('8')) expect(number).toHaveStyle({ color: '#dc2626' });
  await press('Editar camisa de Pedro');
  await fireEvent.changeText(screen.getByLabelText('Número da camisa'), '10');
  await press('Salvar número');
  await waitFor(() => expect(squadService.shirtNumber).toHaveBeenCalledWith('one', 10));
  expect(screen.getByText('10')).toHaveStyle({ color: '#14243a' });
  expect(screen.getByText('8')).toHaveStyle({ color: '#14243a' });
});

test('edits remain available during saving and writes preserve the last choice', async () => {
  let finish: (player: Player) => void = () => undefined;
  jest.mocked(squadService.shirtNumber).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })).mockResolvedValueOnce({ ...first, shirt_number: 12 });
  await render(<SquadScreen {...props} />);
  await press('Editar camisa de Pedro');
  await fireEvent.changeText(screen.getByLabelText('Número da camisa'), '11');
  await press('Salvar número');
  await waitFor(() => expect(squadService.shirtNumber).toHaveBeenCalledTimes(1));
  await press('Editar camisa de Pedro');
  await fireEvent.changeText(screen.getByLabelText('Número da camisa'), '12');
  await press('Salvar número');
  expect(screen.getByText('12')).toBeTruthy();
  expect(squadService.shirtNumber).toHaveBeenCalledTimes(1);
  await act(() => finish({ ...first, shirt_number: 11 }));
  await waitFor(() => expect(squadService.shirtNumber).toHaveBeenLastCalledWith('one', 12));
  expect(screen.getByText('12')).toBeTruthy();
  expect(useSquadStore.getState().data?.players[0].shirt_number).toBe(12);
});

test('failed save restores confirmed shirt and shows shared notification', async () => {
  jest.mocked(squadService.shirtNumber).mockRejectedValue(new Error('Falha ao salvar.'));
  await render(<SquadScreen {...props} />);
  await press('Editar camisa de Pedro');
  await fireEvent.changeText(screen.getByLabelText('Número da camisa'), '11');
  await press('Salvar número');
  await waitFor(() => expect(useNotificationStore.getState().message).toBe('Falha ao salvar.'));
  expect(screen.getByText('8')).toBeTruthy();
  expect(screen.queryByText('11')).toBeNull();
});
