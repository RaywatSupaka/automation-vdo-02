import { defineConfig } from 'wxt';
import compat from '../backend/smartflow/bridge_config.json';

export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  manifest: {
    key: compat.public_key,
    name: 'SmartFlow Next — Development',
    description: 'Pair SmartFlow Next with its local program. Runs explicit simulated Story jobs; real provider dispatch is disabled.',
    permissions: ['nativeMessaging', 'storage', 'alarms'],
    minimum_chrome_version: '120',
    // No content script or host access until the provider adapter boundary is implemented.
  },
});
