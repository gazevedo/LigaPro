const { expo } = require('./app.json');
const version = require('./version.json');
// Expo copies public files into dist for every export, including direct CLI exports.
require('node:fs').writeFileSync(require('node:path').join(require('node:path').dirname(require.resolve('./version.json')), 'public/app-version.json'), JSON.stringify(version) + '\n');
module.exports = () => ({ ...expo,
  version: `${version.major}.${version.minor}.${version.patch}`,
  ios: { ...expo.ios, bundleIdentifier: 'com.ligapro.app' },
  ...(process.env.EXPO_UPDATES_URL ? {
    updates: { url: process.env.EXPO_UPDATES_URL, checkAutomatically: 'NEVER' },
    runtimeVersion: { policy: 'fingerprint' },
  } : {}),
  plugins: ['expo-secure-store',
    ['expo-splash-screen', {
      image: './assets/brand/logo-ligapro.png',
      backgroundColor: '#dceef8',
      imageWidth: 220,
      resizeMode: 'contain',
    }],
    ...(process.env.GOOGLE_IOS_URL_SCHEME ? [
      ['@react-native-google-signin/google-signin', { iosUrlScheme: process.env.GOOGLE_IOS_URL_SCHEME }],
    ] : []),
  ],
});
