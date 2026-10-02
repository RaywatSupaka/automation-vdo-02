import { defineConfig } from 'wxt';
import compat from '../backend/smartflow/bridge_config.json';

export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  manifest: {
    key: compat.public_key,
    name: 'SmartFlow Next — Development',
    description: 'Pair SmartFlow Next with its local program. Provider dispatch is not enabled yet.',
    permissions: ['nativeMessaging'],
    // No content script or host access until the provider adapter boundary is implemented.
  },
});
