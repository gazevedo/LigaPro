import { domainStore } from './domainStore';
import { tacticsService } from '../services/tacticsService';
export const useTacticsStore = domainStore(tacticsService.get);
