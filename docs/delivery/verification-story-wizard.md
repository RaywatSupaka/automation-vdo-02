# Verification: Story Shorts input wizard

Scope: frontend form/component only; no Story API/provider/DB migration or packaged EXE change
Implemented contract: [Step wizard](../architecture/step-wizard.md)

## Checks run

| Command / check | Result | Wall time |
|---|---|---|
| `python tools/check.py --scope ui build-ui` — UI portion | 16 tests passed in 3 files; Vitest itself 2.05s | 51.299s including npm/process startup |
| Same command — build portion | TypeScript and Vite passed | 39.657s |
| `--scope e2e --match "Story wizard\|support session\|invalid session"` | 4 passed, 1 failed | 32.845s |
| `--scope build-ui` after viewport spacing/required attribute adjustment | TypeScript and Vite passed | 9.795s |
| `--scope e2e --match "Story wizard fits\|Story wizard is unavailable"` | 2 passed, including corrected failed fixture | 14.159s |

Initial browser failure: test tried fragment-only navigation to log in after an expired session.
Changed the test to use the visible connection form, as a user would. No auth bypass was added.
The successful targeted rerun covers that case and final responsive CSS; the original run remains non-green.
No full backend suite, live provider call or EXE build was performed for this UI change.

## Behavioral evidence

- Required input and invalid scene count block Next; alert receives focus
- Step heading receives focus; unseen steps cannot be selected
- Back and switching sidebar views preserve draft values
- Editing an earlier step invalidates its and later completion while preserving entered fields
- Reopening a completed step without edits does not trap Next or double-count progress
- Final review/confirmation sends no POST request and does not create a job
- Expired session removes draft UI; support login has no Story creation menu
- 1366×768, 1024×600 and 390×844: no document overflow; progress/footer remain in viewport
- Long review content scrolls inside the card; confirmation remains in viewport
- Screenshots inspected for desktop, narrow layout and review; screenshot animations disabled for stable capture

## Native Dev activation

Confirmed new-project `.smartflow` DB had no active/queued jobs before closing its idle window normally.
Reopened through the same `RUN_DEV.vbs` entry point, preserving Dev mode.
Windows UI Automation verified the new `เรื่องเล่า Shorts` menu, invoked it and found the first-step
heading `เรื่องราวของคุณ เริ่มจากอะไร?` plus `ถัดไป` in the new SmartFlow Next window (PID 24300).
Left this user Dev window open. The legacy SmartFlow AI window was not restarted or modified.
This is source Dev activation evidence, not packaged EXE or clean-client proof.

## Remaining limits

Draft is held in React memory only; closing/reloading loses it, as stated in the form footer.
No Story API, persistence, real generation, voice selector or Extension has been added by this change.
UI validation is feedback only; future backend Story schema must enforce its own contract.
