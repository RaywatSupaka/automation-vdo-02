import { expect, it } from 'vitest';
import { expectedVersions } from './BrowserPairing';

it('shows both versions from the browser API instead of a fixed UI version', () => {
  expect(expectedVersions({ extension_version: '0.2.0', helper_version: '0.2.1' }))
    .toBe('Extension 0.2.0 · helper 0.2.1');
});
