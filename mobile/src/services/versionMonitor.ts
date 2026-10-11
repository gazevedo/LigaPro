import * as Updates from 'expo-updates';

export async function checkForAppUpdate(isMounted: () => boolean) {
  if (!Updates.isEnabled) return;
  const update = await Updates.checkForUpdateAsync();
  if (!isMounted() || !update.isAvailable) return;
  const downloaded = await Updates.fetchUpdateAsync();
  if (isMounted() && downloaded.isNew) await Updates.reloadAsync();
}
