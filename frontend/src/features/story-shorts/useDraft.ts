import { useEffect, useRef, useState } from 'react';
import { DraftStore, transport, type Snapshot } from './persistence';
import { createStoryDraft } from './draft';

declare global { interface Window { smartflowFlush?: () => Promise<boolean>; } }
export function useDraft() {
  const [snapshot, setSnapshot] = useState<Snapshot>({ draft: createStoryDraft(), step: 0, state: 'loading', error: '', generation: 0 });
  const ref = useRef<DraftStore | null>(null);
  useEffect(() => {
    const store = new DraftStore(transport(), setSnapshot, () => window.dispatchEvent(new Event('smartflow-auth-lost')));
    ref.current = store; void store.load();
    const flush = () => store.flush(); window.smartflowFlush = flush;
    const warn = (event: BeforeUnloadEvent) => {
      if (store.value.state !== 'saved') { event.preventDefault(); event.returnValue = ''; }
    };
    window.addEventListener('beforeunload', warn);
    return () => { store.stop(); window.removeEventListener('beforeunload', warn); if (window.smartflowFlush === flush) delete window.smartflowFlush; };
  }, []);
  return { ...snapshot, update: (draft: Snapshot['draft'], step?: number) => ref.current?.update(draft, step),
    retry: () => ref.current?.value.state === 'load_error' ? ref.current.load() : ref.current?.flush(), reload: () => ref.current?.load() };
}
