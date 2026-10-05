import { domainStore } from './domainStore';
import { squadService } from '../services/squadService';
export const useSquadStore = domainStore(squadService.get);
