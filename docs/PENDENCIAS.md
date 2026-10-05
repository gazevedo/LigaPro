# Pendências — Script 2

- [ ] Criar/identificar o OAuth Client ID do tipo Web no Google Cloud e preencher `GOOGLE_WEB_CLIENT_ID` no backend e `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` no mobile com o mesmo ID público.
- [ ] Configurar os clientes OAuth Android/iOS: Android usa `com.ligapro.app` e o SHA-1 do certificado do development build; iOS usa `com.ligapro.app`, `EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID` e `GOOGLE_IOS_URL_SCHEME` (o scheme reverso do Client ID iOS).
- [ ] Gerar development builds (`npx expo run:android` / `npx expo run:ios`) e testar login Google em dispositivo. Expo Go não inclui o módulo nativo Google Sign-In.
- [ ] Validar persistência segura e restauração de sessão após fechar/reabrir o app Android/iOS.

Não usar client secret no aplicativo. A web mantém tokens apenas em memória; a persistência segura está implementada para Android/iOS com SecureStore.
