import { useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { apiRequest } from '../services/apiClient';
import { ActionButton, NotificationBubble, palette } from './GameUI';

const supported = () => typeof window !== 'undefined' && window.isSecureContext && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
export function MatchNotifications({ controls = true }: { controls?: boolean }) {
  const [enabled, setEnabled] = useState(false), [message, setMessage] = useState<string | null>(null);
  const requested = useRef(false), queue = useRef(Promise.resolve()), revision = useRef(0);
  useEffect(() => {
    if (!supported()) return;
    let active = true;
    void navigator.serviceWorker.register('/service-worker.js').then(() => navigator.serviceWorker.ready).then(async registration => {
      const subscription = await registration.pushManager.getSubscription();
      if (active) { requested.current = !!subscription; setEnabled(!!subscription); }
      if (active && subscription && Notification.permission === 'granted') await apiRequest('/push/subscription', { method: 'PUT', body: JSON.stringify(subscription.toJSON()) });
    }).catch(() => undefined);
    return () => { active = false; };
  }, []);
  function toggle() {
    setMessage(null);
    const target = !requested.current, ticket = ++revision.current;
    requested.current = target; setEnabled(target);
    const permission = target && supported() ? Notification.requestPermission() : Promise.resolve('granted');
    queue.current = queue.current.then(async () => {
      if (!supported()) throw new Error('Use o app instalado em um navegador compatível com notificações.');
      // Permission must be requested directly from the user's tap, before network calls.
      if (target && await permission !== 'granted') throw new Error('Permita as notificações nas configurações do navegador para receber os avisos.');
      const registration = await navigator.serviceWorker.ready;
      if (!target) {
        const subscription = await registration.pushManager.getSubscription();
        if (subscription) {
          await apiRequest('/push/subscription', { method: 'DELETE', body: JSON.stringify(subscription.toJSON()) });
          await subscription.unsubscribe();
        }

      } else {
        const config = await apiRequest<{ public_key: string | null }>('/push/config');
        if (!config.public_key) throw new Error('Os avisos de partidas ainda não foram ativados no servidor.');
        const key = config.public_key.replace(/-/g, '+').replace(/_/g, '/');
        const decoded = atob(key.padEnd(Math.ceil(key.length / 4) * 4, '='));
        const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: Uint8Array.from(decoded, char => char.charCodeAt(0)) });
        await apiRequest('/push/subscription', { method: 'PUT', body: JSON.stringify(subscription.toJSON()) });

      }
    }).catch(reason => { if (ticket === revision.current) { requested.current = !target; setEnabled(!target); setMessage(reason instanceof Error ? reason.message : 'Não foi possível configurar os avisos.'); } });
  }
  if (!supported() || !controls) return null;
  return <View style={{ gap: 8 }}>
    <ActionButton secondary title={enabled ? 'Desativar avisos de partidas' : 'Ativar avisos de partidas'} onPress={() => { void toggle(); }} />
    <Text style={{ color: palette.muted, fontSize: 12, textAlign: 'center' }}>Receba uma notificação 5 minutos antes de cada partida do seu clube.</Text>
    <NotificationBubble message={message} />
  </View>;
}
