// Copy the build and substitute ONLY the native host constant, before Chrome starts.
// No production output, installed extension, credential or user profile is modified.
import { cp, mkdtemp, readdir, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
export async function isolatedExtension(root, host) {
  if (!/^com\.smartflow\.next\.smoke_[a-f0-9]{32}$/.test(host)) throw Error('Isolated host required');
  const destination = await mkdtemp(path.join(tmpdir(), 'smartflow-owned-extension-'));
  await cp(path.join(root, 'browser_extension/.output/chrome-mv3'), destination, { recursive: true });
  let replacements = 0;
  async function visit(directory) {
    for (const item of await readdir(directory, { withFileTypes: true })) {
      const target = path.join(directory, item.name);
      if (item.isDirectory()) await visit(target);
      else if (item.name.endsWith('.js')) {
        const source = await readFile(target, 'utf8');
        const count = source.split('com.smartflow.next.dev').length - 1;
        if (count) { replacements += count; await writeFile(target, source.replaceAll('com.smartflow.next.dev', host)); }
      }
    }
  }
  await visit(destination);
  if (!replacements) throw Error('Built native host constant not found; do not run against real host');
  return destination;
}
