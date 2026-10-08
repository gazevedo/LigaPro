import { Pressable, Image, View } from 'react-native';
import { MailboxButton } from './MailboxButton';
export function HeaderActions({ focused, openInbox, openSettings }: { focused: () => boolean; openInbox: () => void; openSettings: () => void }) {
  return <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
    <Pressable accessibilityRole="button" accessibilityLabel="Configurações" hitSlop={8} onPress={openSettings} style={{ width: 32, height: 36, justifyContent: 'center', alignItems: 'center' }}><Image source={require('../../assets/dashboard/configuracao.png')} style={{ width: 26, height: 26 }} resizeMode="contain" /></Pressable>
    <MailboxButton focused={focused} open={openInbox} />
  </View>;
}
