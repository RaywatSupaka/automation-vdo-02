import { describe, expect, it } from 'vitest';
import { createStoryDraft, validateStoryStep } from './draft';

describe('Story draft feedback', () => {
  it('requires a real idea and bounds its size', () => {
    const draft = createStoryDraft();
    expect(validateStoryStep({ ...draft, topic: '  \n ' }, 0)).not.toBeNull();
    expect(validateStoryStep({ ...draft, topic: 'ก'.repeat(2001) }, 0)).not.toBeNull();
    expect(validateStoryStep({ ...draft, topic: 'แมวน้อยในสถานีรถไฟ' }, 0)).toBeNull();
  });
  it.each(['', '0', '2.5', '13', 'NaN'])('rejects an invalid scene count %s', scenes => {
    expect(validateStoryStep({ ...createStoryDraft(), scenes }, 2)).not.toBeNull();
  });
  it.each(['', '29', '60.5', '61'])('rejects an invalid target duration %s', seconds => {
    expect(validateStoryStep({ ...createStoryDraft(), seconds }, 2)).not.toBeNull();
  });
  it('accepts the proposed defaults', () => {
    expect(validateStoryStep(createStoryDraft(), 2)).toBeNull();
  });
});
