import { Platform } from 'react-native';
export async function getGoogleIdToken(): Promise<string> {
  if (Platform.OS === 'web') throw new Error('Login Google requer o development build Android/iOS.');
  const webClientId = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID;
  if (!webClientId) throw new Error('Login Google ainda não configurado.');
  const { GoogleSignin, isSuccessResponse } = await import('@react-native-google-signin/google-signin');
  GoogleSignin.configure({ webClientId, iosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID });
  await GoogleSignin.hasPlayServices();
  const result = await GoogleSignin.signIn();
  if (!isSuccessResponse(result) || !result.data.idToken) {
    throw new Error('Login Google cancelado ou sem credencial.');
  }
  return result.data.idToken;
}
