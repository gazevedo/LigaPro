import { useEffect, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { ActionButton, GamePage, palette, useAction } from '../components/GameUI';
import { loadMoreMessages, readMessage, useInboxStore } from '../stores/inboxStore';

export function InboxScreen() {
  const { data, loading, error, load } = useInboxStore();
  const [opened, setOpened] = useState<string | null>(null);
  const action = useAction();
  useEffect(() => { if (!useInboxStore.getState().loading) void load(); }, [load]);
  return <GamePage loading={loading || action.busy} error={action.error || error}>
    <Text style={{ fontSize: 28, fontWeight: '800', color: palette.ink }}>Mensagens e notícias</Text>
    <Text style={{ color: palette.muted }}>{data ? `${data.unread_count} ${data.unread_count === 1 ? 'não lida' : 'não lidas'}` : 'Carregando seu correio…'}</Text>
    {data?.items.map(item => <Pressable key={item.id} accessibilityRole="button"
      accessibilityLabel={`${item.read ? 'Lida' : 'Não lida'}: ${item.title}`}
      accessibilityState={{ expanded: opened === item.id, disabled: action.busy || loading }}
      disabled={action.busy || loading} onPress={() => void action.run(async () => {
        setOpened(value => value === item.id ? null : item.id);
        if (!item.read) await readMessage(item.id);
      })} style={({ pressed }) => ({ backgroundColor: pressed ? '#eef4fb' : '#fff',
        padding: 20, borderRadius: 18, borderWidth: 1, borderColor: item.read ? palette.border : '#9cb3d0', gap: 10 })}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        {!item.read && <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: palette.primary }} />}
        <Text style={{ flex: 1, fontSize: 16, color: palette.ink, fontWeight: item.read ? '500' : '800' }}>{item.title}</Text>
      </View>
      <Text style={{ color: palette.muted, fontSize: 13 }}>{new Date(item.created_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })} · {item.read ? 'Lida' : 'Não lida'}</Text>
      {opened === item.id && item.body !== item.title && <Text style={{ color: palette.ink, lineHeight: 22 }}>{item.body}</Text>}
    </Pressable>)}
    {data && !data.items.length && <Text style={{ color: palette.muted }}>Você não tem mensagens.</Text>}
    {data && data.items.length < data.total && <ActionButton secondary title="Carregar mais mensagens" disabled={action.busy || loading} onPress={() => void action.run(loadMoreMessages)} />}
    {!data && error && <ActionButton secondary title="Tentar novamente" disabled={loading} onPress={() => void load()} />}
  </GamePage>;
}
