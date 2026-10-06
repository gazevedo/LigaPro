import { act, fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import { MailboxButton } from '../components/MailboxButton';
import { InboxScreen } from '../screens/InboxScreen';
import { historyService, Inbox } from '../services/historyService';
import { readMessage, useInboxStore } from '../stores/inboxStore';
import { useAuthStore } from '../stores/authStore';
import { useClubStore } from '../stores/clubStore';

jest.mock('../services/historyService', () => ({ historyService: { inbox: jest.fn(), markRead: jest.fn() } }));
const message = { id: 'one', type: 'financial', title: 'Receita registrada', body: 'Seu clube recebeu uma premiação.', created_at: '2026-10-06T15:00:00Z', read: false };
const inbox: Inbox = { items: [message, { ...message, id: 'two', title: 'Nova contratação' }], total: 2, unread_count: 2 };
beforeEach(() => {
  jest.clearAllMocks();
  useInboxStore.getState().reset();
  jest.mocked(historyService.inbox).mockResolvedValue(structuredClone(inbox));
  jest.mocked(historyService.markRead).mockResolvedValue({ id: 'one', read: true });
});

test('opening a message reduces the badge and reading it again does not count twice', async () => {
  const open = jest.fn();
  await render(<><MailboxButton open={open} /><InboxScreen /></>);
  await screen.findByRole('button', { name: 'Correio, 2 mensagens não lidas' });
  await waitFor(() => expect(useInboxStore.getState().loading).toBe(false));
  await fireEvent.press(screen.getByRole('button', { name: 'Correio, 2 mensagens não lidas' }));
  expect(open).toHaveBeenCalledTimes(1);
  await fireEvent.press(screen.getByRole('button', { name: 'Não lida: Receita registrada' }));
  await screen.findByText(message.body);
  await screen.findByRole('button', { name: 'Correio, 1 mensagem não lida' });
  await fireEvent.press(screen.getByRole('button', { name: 'Lida: Receita registrada' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Lida: Receita registrada' }));
  expect(historyService.markRead).toHaveBeenCalledTimes(1);
});

test('failed reads preserve the unread count', async () => {
  jest.mocked(historyService.markRead).mockRejectedValueOnce(new Error('Não foi possível salvar a leitura.'));
  await render(<InboxScreen />);
  await screen.findByRole('button', { name: 'Não lida: Receita registrada' });
  await fireEvent.press(screen.getByRole('button', { name: 'Não lida: Receita registrada' }));
  await screen.findByText('Não foi possível salvar a leitura.');
  expect(useInboxStore.getState().data?.unread_count).toBe(2);
});

test('loads older messages without duplicating rows', async () => {
  jest.mocked(historyService.inbox).mockResolvedValueOnce({ ...inbox, total: 3 })
    .mockResolvedValueOnce({ items: [{ ...message, id: 'three', title: 'Mensagem antiga' }], total: 3, unread_count: 3 });
  await render(<InboxScreen />);
  await fireEvent.press(await screen.findByRole('button', { name: 'Carregar mais mensagens' }));
  await screen.findByText('Mensagem antiga');
  expect(historyService.inbox).toHaveBeenLastCalledWith(2);
  expect(useInboxStore.getState().data?.items).toHaveLength(3);
});

test('late read responses do not populate another account cache', async () => {
  useAuthStore.setState({ user: { id: 'reader-a' } as never });
  useClubStore.setState({ data: { club: { id: 'club-a' } as never } });
  useInboxStore.setState({ data: inbox });
  let finish!: (value: { id: string; read: boolean }) => void;
  jest.mocked(historyService.markRead).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  const reading = readMessage('one');
  useAuthStore.setState({ user: { id: 'reader-b' } as never });
  finish({ id: 'one', read: true }); await reading;
  expect(useInboxStore.getState().data).toBeNull();
});

test('a GET started before a read cannot restore an unread badge', async () => {
  useInboxStore.setState({ data: structuredClone(inbox) });
  let finish!: (value: Inbox) => void;
  jest.mocked(historyService.inbox).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }))
    .mockResolvedValueOnce({ ...inbox, unread_count: 1, items: inbox.items.map(item => item.id === 'one' ? { ...item, read: true } : item) });
  await act(async () => {
    const loading = useInboxStore.getState().load();
    await readMessage('one');
    finish(structuredClone(inbox));
    await loading;
  });
  expect(useInboxStore.getState().data?.unread_count).toBe(1);
  expect(useInboxStore.getState().data?.items[0].read).toBe(true);
});

test('refreshes the badge for new messages only while the dashboard is focused', async () => {
  jest.useFakeTimers();
  try {
    let focused = true;
    jest.mocked(historyService.inbox).mockResolvedValueOnce(inbox).mockResolvedValue({ ...inbox, unread_count: 3, total: 3 });
    const view = await render(<MailboxButton open={jest.fn()} focused={() => focused} />);
    expect(screen.getByRole('button', { name: 'Correio, 2 mensagens não lidas' })).toBeTruthy();
    await act(async () => { await jest.advanceTimersByTimeAsync(60000); });
    expect(screen.getByRole('button', { name: 'Correio, 3 mensagens não lidas' })).toBeTruthy();
    focused = false;
    await act(async () => { await jest.advanceTimersByTimeAsync(60000); });
    expect(historyService.inbox).toHaveBeenCalledTimes(2);
    await view.unmount();
  } finally { jest.useRealTimers(); }
});
