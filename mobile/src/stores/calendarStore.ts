import { domainStore } from './domainStore';
import { calendarService } from '../services/calendarService';
export const useCalendarStore = domainStore(calendarService.get);
