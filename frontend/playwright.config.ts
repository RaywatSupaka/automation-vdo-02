import { defineConfig } from '@playwright/test';
import path from 'node:path';
import os from 'node:os';
import fs from 'node:fs';

const python = process.platform === 'win32' ? '../.venv/Scripts/python.exe' : '../.venv/bin/python';
export const testToken = 'e2e-fixture-session-not-a-real-secret';
export default defineConfig({
  testDir: './e2e', timeout: 20000, workers: 1, reporter: [['list']],
  use: { baseURL: 'http://127.0.0.1:8788', trace: 'retain-on-failure', screenshot: 'only-on-failure',
    viewport: { width: 1440, height: 1000 } },
  webServer: {
    command: `"${python}" -m smartflow.cli serve --port 8788`,
    url: 'http://127.0.0.1:8788/', reuseExistingServer: false, timeout: 20000,
    env: { SMARTFLOW_API_TOKEN: testToken, SMARTFLOW_MODE: 'test',
      SMARTFLOW_DATA_DIR: fs.mkdtempSync(path.join(os.tmpdir(), 'smartflow-e2e-')) },
  },
});
