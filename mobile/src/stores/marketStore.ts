import { domainStore } from './domainStore';
import { marketService } from '../services/marketService';
export const useMarketStore = domainStore(marketService.mine);
