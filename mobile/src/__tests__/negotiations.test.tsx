import { render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { TransferOffersScreen } from '../screens/TransferOffersScreen';
import { marketService } from '../services/marketService';
import { useMarketStore } from '../stores/marketStore';
jest.mock('../services/marketService', () => ({ marketService: { mine: jest.fn(), action: jest.fn(), counter: jest.fn(), cancelOffer: jest.fn() } }));
const offer = { id: 'offer1', listing_id: 'listing1', seller_club_id: 'seller', buyer_club_id: 'buyer', amount: 100000, status: 'pending', negotiation_version: 2, salary_offer: 45000, contract_months: 24 };
beforeEach(() => { jest.clearAllMocks(); useMarketStore.getState().reset(); });
test('seller can counter without settling the transfer', async () => {
  jest.mocked(marketService.mine).mockResolvedValue({ listings: [], incoming: [offer], outgoing: [], loans: [] });
  await render(<TransferOffersScreen />);
  await fireEvent.changeText(await screen.findByLabelText('Contraproposta (R$)'), '2500');
  await fireEvent.press(screen.getByText('Enviar contraproposta'));
  await waitFor(() => expect(marketService.counter).toHaveBeenCalledWith('offer1', 250000));
  expect(marketService.action).not.toHaveBeenCalled();
});
test('buyer sees confirmation only after seller and player accept', async () => {
  jest.mocked(marketService.mine).mockResolvedValue({ listings: [], incoming: [], outgoing: [{ ...offer, status: 'player_accepted', player_decision: { accepted: true, reason: 'Contrato aceito pelo jogador.' } }], loans: [] });
  await render(<TransferOffersScreen />);
  await fireEvent.press(await screen.findByText('Confirmar transferência'));
  await waitFor(() => expect(marketService.action).toHaveBeenCalledWith('offer1', 'confirm'));
});
