import { domainStore } from './domainStore';
import { stadiumService } from '../services/stadiumService';
export const useStadiumStore = domainStore(stadiumService.get);
