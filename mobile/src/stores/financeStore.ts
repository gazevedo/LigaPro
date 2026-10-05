import { domainStore } from './domainStore';
import { financeService } from '../services/financeService';
export const useFinanceStore = domainStore(financeService.get);
