import { View } from 'react-native';
import { MailboxButton } from './MailboxButton';
export function HeaderActions({ focused, openInbox }: { focused: () => boolean; openInbox: () => void }) {
  return <View style={{ flexDirection: 'row', alignItems: 'center', height: 44, paddingRight: 4 }}>
    <MailboxButton focused={focused} open={openInbox} />
  </View>;
}
