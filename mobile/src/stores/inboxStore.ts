import { domainStore } from './domainStore';
import { historyService } from '../services/historyService';
import { useAuthStore } from './authStore';
import { useClubStore } from './clubStore';

let readVersion = 0;
async function inboxPage(offset = 0) {
  // Do not restore unread flags from a GET started before a successful read.
  for (;;) {
    const ticket = readVersion;
    const page = await historyService.inbox(offset);
    if (ticket === readVersion) return page;
  }
}
export const useInboxStore = domainStore(() => inboxPage());

function owner() { return `${useAuthStore.getState().user?.id}:${useClubStore.getState().data?.club?.id}`; }

export async function readMessage(id: string) {
  if (useInboxStore.getState().data?.items.find(item => item.id === id)?.read) return;
  const expectedOwner = owner();
  await historyService.markRead(id);
  if (owner() !== expectedOwner) return;
  readVersion++;
  useInboxStore.setState(({ data }) => {
    if (!data || !data.items.some(item => item.id === id && !item.read)) return {};
    return { data: { ...data, unread_count: Math.max(0, data.unread_count - 1),
      items: data.items.map(item => item.id === id ? { ...item, read: true } : item) } };
  });
}

export async function loadMoreMessages() {
  const current = useInboxStore.getState().data;
  if (!current || current.items.length >= current.total) return;
  const expectedOwner = owner();
  const next = await inboxPage(current.items.length);
  if (owner() !== expectedOwner) return;
  useInboxStore.setState(({ data }) => {
    if (!data) return {};
    const ids = new Set(data.items.map(item => item.id));
    return { data: { ...next, items: [...data.items, ...next.items.filter(item => !ids.has(item.id))] } };
  });
}
