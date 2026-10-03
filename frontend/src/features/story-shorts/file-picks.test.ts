import { describe, expect, it } from 'vitest';
import { applyFilePick, mergeFilePicks, type PickInput } from './file-picks';
import type { StoredAsset } from './fields';

const file = (name: string, content = 'x', lastModified = 1) => new File([content], name, { lastModified });

describe('file picks', () => {
  it('accumulates picks across several selections for multi-file fields', () => {
    const first = file('rain.mp3'), second = file('wind.mp3'), third = file('fire.mp3');
    const afterFirst = mergeFilePicks([], [first], true);
    const afterSecond = mergeFilePicks(afterFirst, [second, third], true);
    expect(afterSecond).toEqual([first, second, third]);
    expect(afterFirst).toEqual([first]); // Merges never mutate the previous draft value.
  });
  it('skips an exact duplicate pick and returns the same list so no autosave is queued', () => {
    const existing = [file('rain.mp3')];
    const repeat = file('rain.mp3');
    expect(mergeFilePicks(existing, [repeat], true)).toBe(existing);
    const withNew = mergeFilePicks(existing, [repeat, file('wind.mp3'), file('wind.mp3')], true);
    expect(withNew.map(item => item.name)).toEqual(['rain.mp3', 'wind.mp3']);
  });
  it('keeps files that only share a name with an existing pick', () => {
    const existing = [file('take.mp4', 'x', 1)];
    const merged = mergeFilePicks(existing, [file('take.mp4', 'xx', 1), file('take.mp4', 'x', 2)], true);
    expect(merged).toHaveLength(3);
  });
  it('never treats a restored asset as an exact duplicate of a new File', () => {
    const stored: StoredAsset = { id: 'asset-1', name: 'rain.mp3', size: 1 };
    expect(mergeFilePicks([stored], [file('rain.mp3')], true)).toHaveLength(2);
  });
  it('allows re-picking a file after it was removed', () => {
    const rain = file('rain.mp3'), wind = file('wind.mp3');
    const removed = [rain, wind].filter(item => item !== rain);
    expect(mergeFilePicks(removed, [file('rain.mp3')], true).map(item => item.name)).toEqual(['wind.mp3', 'rain.mp3']);
  });
  it('replaces single-file fields and ignores an empty pick', () => {
    const logo = file('logo.png'), next = file('logo-2.png');
    expect(mergeFilePicks([logo], [next], false)).toEqual([next]);
    const existing = [logo];
    expect(mergeFilePicks(existing, [], false)).toBe(existing);
    expect(mergeFilePicks(existing, [], true)).toBe(existing);
    expect(mergeFilePicks(existing, [file('logo.png')], false)).toBe(existing);
    const stored: StoredAsset = { id: 'asset-2', name: 'logo.png', size: 1 };
    expect(mergeFilePicks([stored], [logo], false)).toEqual([logo]);
  });
  it('does not cap at maxFiles so step validation can report the extra pick', () => {
    const three = [file('1.mp4'), file('2.mp4'), file('3.mp4')];
    expect(mergeFilePicks(three, [file('4.mp4')], true)).toHaveLength(4);
  });
});

describe('file input change', () => {
  const input = (...files: File[]): PickInput => ({ files, value: 'C:\fakepath\picked' });
  function recorder() {
    const commits: unknown[][] = [];
    return { commits, commit: (next: unknown[]) => { commits.push(next); } };
  }
  it('commits the merged list and clears the input', () => {
    const rain = file('rain.mp3'), wind = file('wind.mp3'), target = input(wind), { commits, commit } = recorder();
    expect(applyFilePick(target, [rain], true, commit)).toBe(true);
    expect(commits).toEqual([[rain, wind]]);
    expect(target.value).toBe('');
  });
  it('does not commit a duplicate pick but still clears the input', () => {
    const existing = [file('rain.mp3')], target = input(file('rain.mp3')), { commits, commit } = recorder();
    expect(applyFilePick(target, existing, true, commit)).toBe(false);
    expect(commits).toEqual([]); // No autosave and no reset of the step's completion state.
    expect(target.value).toBe('');
  });
  it('lets the same file be picked again after it was removed', () => {
    const rain = file('rain.mp3'), target = input(rain), { commits, commit } = recorder();
    applyFilePick(target, [], true, commit);
    const afterRemove = (commits[0] as File[]).filter(item => item !== rain);
    expect(target.value).toBe(''); // A real input fires change again for the same file only after this.
    expect(applyFilePick(Object.assign(target, { files: [rain] }), afterRemove, true, commit)).toBe(true);
    expect(commits[1]).toEqual([rain]);
  });
  it('ignores a cancelled picker and replaces single-file fields', () => {
    const logo = file('logo.png'), next = file('logo-2.png'), { commits, commit } = recorder();
    expect(applyFilePick({ files: null, value: '' }, [logo], false, commit)).toBe(false);
    expect(applyFilePick(input(next), [logo], false, commit)).toBe(true);
    expect(commits).toEqual([[next]]);
  });
});
