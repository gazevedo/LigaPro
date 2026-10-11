import * as SplashScreen from 'expo-splash-screen';

// Keep the native system splash until the saved session has a destination.
void SplashScreen.preventAutoHideAsync().catch(() => undefined);
export async function hideStartupSplash() {
  try { await SplashScreen.hideAsync(); }
  catch { /* Expo Go may not expose the native launch screen. */ }
}
