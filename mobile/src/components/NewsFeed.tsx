import { NotificationBubble } from './GameUI';
import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';
import { NewsItem, historyService } from '../services/historyService';
export function NewsFeed() {
  const [items, setItems] = useState<NewsItem[]>([]); const [error, setError] = useState('');
  useEffect(() => { let mounted = true; void historyService.news().then(rows => { if (mounted) setItems(rows); }).catch(() => { if (mounted) setError('Não foi possível carregar as notícias.'); }); return () => { mounted = false; }; }, []);
  return <View><Text>Notícias recentes</Text><NotificationBubble message={error} />{items.slice(0, 8).map(item => <View key={item.id}><Text>{item.title}</Text><Text>{item.body} · {new Date(item.created_at).toLocaleDateString('pt-BR')}</Text></View>)}</View>;
}
