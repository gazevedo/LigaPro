import { create } from 'zustand';
export const useNotificationStore = create<{ message: string | null; show: (message: string) => void; clear: () => void }>(set => ({ message: null, show: message => set({ message }), clear: () => set({ message: null }) }));
