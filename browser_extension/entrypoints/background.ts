import { browser } from 'wxt/browser';
import { defineBackground } from 'wxt/utils/define-background';
import { allowedPopup } from '../protocol';
import { probe } from '../protocol/probe';

export default defineBackground(() => {
  browser.runtime.onMessage.addListener((message, sender) => {
    if (!allowedPopup(sender, browser.runtime.id)) return Promise.resolve({ state: 'protocol_error' });
    if (!message || (message.kind !== 'probe' && message.kind !== 'pair') ||
      (message.kind === 'probe' && Object.keys(message).length !== 1) ||
      (message.kind === 'pair' && (Object.keys(message).length !== 2 || typeof message.code !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(message.code))))
      return Promise.resolve({ state: 'protocol_error' });
    return probe((host, payload) => browser.runtime.sendNativeMessage(host, payload), browser.runtime.getManifest().version, 7000, message.code)
      .then(state => ({ state }));
  });
});
