import { defineConfig } from 'wxt';

export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  manifest: {
    name: 'SmartFlow Next — Development',
    description: 'New SmartFlow bridge foundation. Pairing and provider dispatch are not enabled yet.',
    permissions: ['nativeMessaging'],
    // No content script or host access until the provider adapter boundary is implemented.
  },
});
