import { browser } from 'wxt/browser';
import { defineBackground } from 'wxt/utils/define-background';
import { allowedPopup } from '../protocol';
import { probe } from '../protocol/probe';

export default defineBackground(() => {
  browser.runtime.onMessage.addListener((message, sender) => {
    if (!allowedPopup(sender, browser.runtime.id)) return Promise.resolve({ state: 'protocol_error' });
    if (!message || Object.keys(message).length !== 1 || message.kind !== 'probe')
      return Promise.resolve({ state: 'protocol_error' });
    return probe((host, payload) => browser.runtime.sendNativeMessage(host, payload), browser.runtime.getManifest().version)
      .then(state => ({ state }));
  });
});
