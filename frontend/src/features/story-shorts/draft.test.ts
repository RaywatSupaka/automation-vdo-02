import { describe, expect, it } from 'vitest';
import { createStoryDraft, validateStoryStep } from './draft';

it('limits single-file and music/SFX picks to the backend counts', () => {
  const image = () => new File(['x'], 'reference.png');
  expect(validateStoryStep({ ...createStoryDraft(), topic: 'ready', mainImage: [image(), image()] }, 0)).toContain('1 ไฟล์');
  const audio = Array.from({ length: 101 }, (_, index) => new File(['x'], `${index}.mp3`));
  expect(validateStoryStep({ ...createStoryDraft(), musicEnabled: true, musicFiles: audio }, 3)).toContain('100 ไฟล์');
  expect(validateStoryStep({ ...createStoryDraft(), sfxEnabled: true, sfxFiles: audio }, 3)).toContain('100 ไฟล์');
});

describe('Story draft feedback', () => {
  it('requires a real idea and bounds its size', () => {
    const draft = createStoryDraft();
    expect(validateStoryStep({ ...draft, topic: '  \n ' }, 0)).not.toBeNull();
    expect(validateStoryStep({ ...draft, topic: 'ก'.repeat(2001) }, 0)).not.toBeNull();
    expect(validateStoryStep({ ...draft, topic: 'แมวน้อยในสถานีรถไฟ' }, 0)).toBeNull();
  });
  it.each(['', '0', '2.5', '16', 'NaN'])('rejects an invalid scene count %s', scenes => {
    expect(validateStoryStep({ ...createStoryDraft(), scenes }, 2)).not.toBeNull();
  });
  it.each(['29', '60.5', '61'])('rejects an invalid target duration %s', seconds => {
    expect(validateStoryStep({ ...createStoryDraft(), seconds }, 2)).not.toBeNull();
  });
  it('accepts the proposed defaults', () => {
    expect(validateStoryStep(createStoryDraft(), 2)).toBeNull();
  });
});

// Regression coverage for optional sections and switching between single/batch drafts.
import { fieldGroups } from './fields';
import { draftWarnings } from './draft';
it('requires custom image direction only when selected', () => {
  const draft = createStoryDraft();
  expect(validateStoryStep(draft, 1)).toBeNull();
  expect(validateStoryStep({ ...draft, visualStyle: 'custom' }, 1)).toContain('แนวภาพ');
  expect(validateStoryStep({ ...draft, visualStyle: 'custom', visualCustom: 'เส้นหมึกสีฟ้า' }, 1)).toBeNull();
});
it('validates the active brief without destroying the other one', () => {
  const draft = { ...createStoryDraft(), creationMode: 'batch', topic: 'เก็บหัวข้อเดี่ยวไว้', batchTopics: 'เรื่องหนึ่ง\nเรื่องสอง' };
  expect(validateStoryStep(draft, 0)).toBeNull();
  expect(validateStoryStep({ ...draft, batchTopics: Array(11).fill('เรื่อง').join('\n') }, 0)).toContain('10');
  expect(validateStoryStep({ ...draft, creationMode: 'single' }, 0)).toBeNull();
});
it('requires files only for enabled features and validates file boundaries', () => {
  const draft = createStoryDraft();
  expect(validateStoryStep(draft, 2)).toBeNull();
  expect(validateStoryStep({ ...draft, introEnabled: true }, 2)).toContain('อินโทร');
  expect(validateStoryStep({ ...draft, topic: 'ทดสอบ', mainImage: [new File(['x'], 'wrong.exe')] }, 0)).toContain('ชนิดไฟล์');
  const greenFiles = Array.from({length: 4}, (_, i) => new File(['x'], `${i}.mp4`));
  expect(validateStoryStep({ ...draft, greenEnabled: true, greenFiles }, 2)).toContain('3 ไฟล์');
});
it('rejects stale scene references and too many music tracks, but retains configuration for correction', () => {
  const draft = { ...createStoryDraft(), scenes: '6', coverScene: '10' };
  expect(validateStoryStep(draft, 2)).toContain('ภาพอ้างอิงปก');
  expect(draft.coverScene).toBe('10');
  expect(validateStoryStep({ ...createStoryDraft(), musicEnabled: true, musicFiles: [new File(['x'], 'music.mp3')], musicCount: '2' }, 3)).toContain('จำนวนเพลง');
});
it('gives capability warnings without silently changing user choices', () => {
  const draft: ReturnType<typeof createStoryDraft> = { ...createStoryDraft(), speaker: 'dialogue' };
  expect(draftWarnings(draft).join()).toContain('Google Flow');
  expect(draft.videoMode).toBe('image_motion');
});
it('keeps independent defaults and unique field IDs', () => {
  const fields = fieldGroups.flatMap(group => group.fields);
  expect(new Set(fields.map(field => field.id)).size).toBe(fields.length);
  const first = createStoryDraft(), second = createStoryDraft();
  expect(first.mainImage).not.toBe(second.mainImage);
});
