import { domainStore } from './domainStore';
import { clubService } from '../services/clubService';
export const useClubStore = domainStore(clubService.status);
