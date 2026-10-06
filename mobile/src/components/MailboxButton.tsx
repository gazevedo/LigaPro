import { useEffect } from 'react';
import { AppState, Pressable, Text, View } from 'react-native';
import { useInboxStore } from '../stores/inboxStore';

export function MailboxButton({ open, focused }: { open: () => void; focused?: () => boolean }) {
  const count = useInboxStore(state => state.data?.unread_count || 0);
  const load = useInboxStore(state => state.load);
  useEffect(() => {
    function refresh() {
      if (focused && !focused()) return;
      if (AppState.currentState === 'background' || AppState.currentState === 'inactive') return;
      if (!useInboxStore.getState().loading) void load();
    }
    refresh();
    const timer = setInterval(refresh, 60000);
    const subscription = AppState.addEventListener('change', state => { if (state === 'active') refresh(); });
    return () => { clearInterval(timer); subscription.remove(); };
  }, [load, focused]);
  const description = count === 1 ? 'mensagem não lida' : 'mensagens não lidas';
  return <Pressable accessibilityRole="button" accessibilityLabel={`Correio, ${count} ${description}`}
    onPress={open} hitSlop={8} style={({ pressed }) => ({ width: 44, height: 44, marginRight: 8,
      borderRadius: 14, backgroundColor: '#eef4fb', alignItems: 'center', justifyContent: 'center', opacity: pressed ? 0.7 : 1 })}>
    <Text style={{ fontSize: 28, color: '#082957' }}>✉︎</Text>
    {count > 0 && <View style={{ position: 'absolute', right: -6, top: -4, minWidth: 22, height: 22,
      paddingHorizontal: 5, borderRadius: 11, backgroundColor: '#dc2626', alignItems: 'center', justifyContent: 'center' }}>
      <Text style={{ color: '#fff', fontSize: 12, fontWeight: '800' }}>{count > 99 ? '99+' : count}</Text>
    </View>}
  </Pressable>;
}
