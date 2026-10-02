import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';
import { fieldGroups } from './fields';

it('draft persistence contract covers every UI field without dropping hidden settings', () => {
  const registry = JSON.parse(readFileSync(new URL('../../../../backend/smartflow/draft_fields.json', import.meta.url), 'utf8'));
  const fields = fieldGroups.flatMap(group => group.fields);
  expect(Object.keys(registry).sort()).toEqual(fields.map(field => field.id).sort());
  for (const field of fields) {
    expect(registry[field.id].kind).toBe(field.kind);
    expect(registry[field.id].initial).toEqual(field.initial);
    if (field.maxLength) expect(registry[field.id].maxLength).toBe(field.maxLength);
  }
});
