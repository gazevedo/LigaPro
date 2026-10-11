import { domainStore, setDomainClubId } from './domainStore';
import { clubService } from '../services/clubService';
export const useClubStore = domainStore(clubService.status, 'club-status');

useClubStore.subscribe(state => setDomainClubId(state.data?.club?.id));
