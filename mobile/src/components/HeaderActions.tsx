import { Pressable, Text, View } from 'react-native';
import { palette } from './GameUI';
import { MailboxButton } from './MailboxButton';
export function HeaderActions({ focused, openInbox, openSettings }: { focused: () => boolean; openInbox: () => void; openSettings: () => void }) {
  return <View style={{ flexDirection: 'row', alignItems: 'center', height: 44, paddingRight: 4 }}>
    <Pressable accessibilityRole="button" accessibilityLabel="Configurações" onPress={openSettings} style={{ width: 44, height: 44, alignItems: 'center', justifyContent: 'center' }}><Text style={{ fontSize: 26, color: palette.ink }}>⚙</Text></Pressable>
    <MailboxButton focused={focused} open={openInbox} />
  </View>;
}
