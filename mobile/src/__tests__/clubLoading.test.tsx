import { act, fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import { Button, Text } from 'react-native';
import { GamePage } from '../components/GameUI';
import { CreateClubScreen } from '../screens/CreateClubScreen';
import { clubService } from '../services/clubService';

jest.mock('../services/clubService', () => ({ clubService: { catalog: jest.fn(), create: jest.fn() } }));
const catalog = { countries: [{ id: 'BR', name: 'Brasil' }], badges: [{ id: 'blue', name: 'Azul', symbol: '🛡', color: '#2563eb' }] };
beforeEach(() => {
  jest.resetAllMocks();
  jest.mocked(clubService.catalog).mockResolvedValue(catalog);
});

test('page loader allows content interaction and disappears when loading finishes', async () => {
  const onPress = jest.fn();
  const view = await render(<GamePage loading><Button title="Editar" onPress={onPress} /></GamePage>);
  expect(screen.getByLabelText('Carregando')).toBeTruthy();
  await fireEvent.press(screen.getByText('Editar'));
  expect(onPress).toHaveBeenCalledTimes(1);
  await view.rerender(<GamePage><Text>Conteúdo</Text></GamePage>);
  expect(screen.queryByLabelText('Carregando')).toBeNull();
});

test('club creation requires explicit country and badge selections', async () => {
  await render(<CreateClubScreen />);
  await screen.findByText('Azul');
  await fireEvent.changeText(screen.getByLabelText('Nome do clube'), 'Meu clube');
  const button = () => screen.getByRole('button', { name: 'Criar clube' });
  expect(button()).toBeDisabled();
  await fireEvent.press(button());
  expect(clubService.create).not.toHaveBeenCalled();
  await fireEvent.press(screen.getByRole('button', { name: 'Escolher país' }));
  await fireEvent.press(screen.getByText('Brasil'));
  expect(button()).toBeDisabled();
  await fireEvent.press(screen.getByRole('button', { name: 'Azul' }));
  expect(button()).toBeEnabled();
  await fireEvent.changeText(screen.getByLabelText('Nome do estádio'), 'AB');
  expect(button()).toBeDisabled();
});

test('catalog failure retries automatically and preserves typed fields', async () => {
  let fail!: (error: Error) => void;
  jest.mocked(clubService.catalog).mockImplementationOnce(() => new Promise((_resolve, reject) => { fail = reject; }));
  await render(<CreateClubScreen />);
  await fireEvent.changeText(screen.getByLabelText('Nome do clube'), 'Meu clube');
  await act(async () => { fail(new Error('Offline')); });
  await screen.findByText('Azul');
  expect(clubService.catalog).toHaveBeenCalledTimes(2);
  expect(screen.getByLabelText('Nome do clube').props.value).toBe('Meu clube');
  expect(screen.getByRole('button', { name: 'Criar clube' })).toBeDisabled();
});

test('empty badges retry, exhausted failures allow manual recovery', async () => {
  jest.mocked(clubService.catalog).mockResolvedValue({ ...catalog, badges: [] });
  await render(<CreateClubScreen />);
  await waitFor(() => expect(clubService.catalog).toHaveBeenCalledTimes(3));
  await screen.findByText('Não foi possível carregar todas as opções do clube. Tente novamente.');
  expect(screen.getByRole('button', { name: 'Criar clube' })).toBeDisabled();
  jest.mocked(clubService.catalog).mockResolvedValue(catalog);
  await fireEvent.press(screen.getByText('Recarregar opções'));
  await screen.findByText('Azul');
  expect(clubService.catalog).toHaveBeenCalledTimes(4);
});
