const { expo } = require('./app.json');
module.exports = () => ({ ...expo,
  ios: { ...expo.ios, bundleIdentifier: 'com.ligapro.app' },
  plugins: ['expo-secure-store',
    ...(process.env.GOOGLE_IOS_URL_SCHEME ? [
      ['@react-native-google-signin/google-signin', { iosUrlScheme: process.env.GOOGLE_IOS_URL_SCHEME }],
    ] : []),
  ],
});
