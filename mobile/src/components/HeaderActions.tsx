import { Pressable, Image, View } from 'react-native';
import { MailboxButton } from './MailboxButton';
export function HeaderActions({ focused, openInbox, openSettings }: { focused: () => boolean; openInbox: () => void; openSettings: () => void }) {
  return <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, height: 44, paddingRight: 4 }}>
    <Pressable accessibilityRole="button" accessibilityLabel="Configurações" hitSlop={8} onPress={openSettings} style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: '#eef4fb', justifyContent: 'center', alignItems: 'center' }}><Image source={require('../../assets/dashboard/configuracao.png')} style={{ width: 24, height: 24 }} resizeMode="contain" /></Pressable>
    <MailboxButton focused={focused} open={openInbox} />
  </View>;
}
