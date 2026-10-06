import { act, fireEvent, render, screen } from '@testing-library/react-native';
import { UpcomingMatches } from '../components/UpcomingMatches';
import { liveMatchService } from '../services/liveMatchService';

jest.mock('../services/liveMatchService', () => ({ liveMatchService: { upcoming: jest.fn() } }));
const upcoming = jest.mocked(liveMatchService.upcoming);
const first = { id: 'first', date: '2026-10-08T15:41:20Z', round: 1, status: 'scheduled' };
const second = { id: 'second', date: '2026-10-09T08:06:36Z', round: 2, status: 'scheduled' };
beforeEach(() => { upcoming.mockReset(); });

test('shows only the next scheduled match date without a watch button', async () => {
  upcoming.mockResolvedValue([second, first]);
  await render(<UpcomingMatches open={jest.fn()} />);
  await screen.findByText('Próxima partida');
  expect(screen.getByText(`Rodada 1 · ${new Date(first.date).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}`)).toBeTruthy();
  expect(screen.queryByText(/Rodada 2/)).toBeNull();
  expect(screen.queryByRole('button')).toBeNull();
});

test('prioritizes a live match and opens it using Assistir', async () => {
  upcoming.mockResolvedValue([first, { ...second, status: 'live' }]);
  const open = jest.fn();
  await render(<UpcomingMatches open={open} />);
  await screen.findByText('Partida em andamento');
  await fireEvent.press(screen.getByRole('button', { name: 'Assistir' }));
  expect(open).toHaveBeenCalledWith('second');
});

test('updates automatically when the server marks the match live and clears the timer on unmount', async () => {
  jest.useFakeTimers();
  try {
    upcoming.mockResolvedValueOnce([first]).mockResolvedValue([{ ...first, status: 'live' }]);
    const view = await render(<UpcomingMatches open={jest.fn()} />);
    expect(screen.queryByRole('button', { name: 'Assistir' })).toBeNull();
    await act(async () => { await jest.advanceTimersByTimeAsync(30000); });
    expect(screen.getByRole('button', { name: 'Assistir' })).toBeTruthy();
    await view.unmount();
    await act(async () => { await jest.advanceTimersByTimeAsync(60000); });
    expect(upcoming).toHaveBeenCalledTimes(2);
  } finally { jest.useRealTimers(); }
});

test('a past scheduled time does not enable watching before the server starts the match', async () => {
  upcoming.mockResolvedValue([{ ...first, date: '2000-01-01T00:00:00Z' }]);
  await render(<UpcomingMatches open={jest.fn()} />);
  await screen.findByText('Próxima partida');
  expect(screen.queryByRole('button')).toBeNull();
});
