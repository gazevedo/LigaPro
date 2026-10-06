import { useEffect } from 'react';
import { View } from 'react-native';
import { useNotificationStore } from '../stores/notificationStore';
import { NotificationBubble } from './GameUI';
export function NotificationHost() {
  const { message, clear } = useNotificationStore();
  useEffect(() => { if (!message) return; const timer = setTimeout(clear, 6000); return () => clearTimeout(timer); }, [message, clear]);
  return <View pointerEvents="box-none" style={{ position: 'absolute', bottom: 32, left: 24, right: 24, maxWidth: 560, alignSelf: 'center' }}><NotificationBubble message={message} tone="info" /></View>;
}
