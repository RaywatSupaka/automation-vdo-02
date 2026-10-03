import type { StoredAsset } from './fields';

type DraftFile = File | StoredAsset;

/** Exact duplicate of a picked File. Restored StoredAssets have no lastModified, so they never match. */
function samePick(item: DraftFile, file: File) {
  return item instanceof File && item.name === file.name && item.size === file.size && item.lastModified === file.lastModified;
}

/**
 * Multi-file fields accumulate picks and skip exact duplicates; single-file fields replace.
 * Returns `existing` itself when nothing changes, so callers can skip a redundant autosave.
 * Count limits (maxFiles) stay with step validation so extra picks are reported, never dropped silently.
 */
export function mergeFilePicks(existing: DraftFile[], picked: readonly File[], multiple: boolean): DraftFile[] {
  if (!picked.length) return existing;
  if (!multiple) return existing.length === 1 && picked.length === 1 && samePick(existing[0], picked[0]) ? existing : [...picked];
  const merged = [...existing];
  for (const file of picked) if (!merged.some(item => samePick(item, file))) merged.push(file);
  return merged.length === existing.length ? existing : merged;
}

/** The file input fields this helper reads and resets; a real HTMLInputElement satisfies it. */
export type PickInput = { files: ArrayLike<File> | null; value: string };

/**
 * A file input's onChange handler: merge the pick, clear the input so a removed file can be picked again,
 * and commit only a real change, so a duplicate pick queues no autosave and keeps the step's progress.
 */
export function applyFilePick(input: PickInput, existing: DraftFile[], multiple: boolean,
  commit: (next: DraftFile[]) => void): boolean {
  const next = mergeFilePicks(existing, Array.from(input.files ?? []), multiple);
  input.value = '';
  if (next === existing) return false;
  commit(next);
  return true;
}
