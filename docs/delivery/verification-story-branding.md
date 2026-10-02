# Verification: Story branding and connected stepper

Scope: UI colors/assets, section-one heading and shared stepper presentation.
Contract/source links: [Branding](../architecture/branding.md), [Step wizard](../architecture/step-wizard.md).

## Checks

| Check | Result | Wall time |
|---|---|---|
| `python tools/check.py --scope build-ui` | TypeScript/Vite passed | 50.649s |
| `--scope e2e --match "Story wizard\|create, inspect"` | 3 passed, 1 failed: brand image was unavailable under `/brand/` | 20.140s |
| `--scope build-ui` after static asset path fix | Passed | 4.020s |
| `--scope e2e --match "Story wizard fits"` | Passed, including image load and connector geometry at all viewport sizes | 21.872s (Playwright 7.6s) |

Root cause: the existing desktop API serves frontend assets under `/assets/`, not arbitrary public directories.
Moved images to `frontend/public/assets/brand/` and updated image/favicon references.
No new backend route or auth policy was needed. The failed image check remains a regression assertion.
Image loading is polled until complete after responsive picture source changes, without fixed sleeps.

Verified 1366×768, 1024×600 and 390×844:

- Heading contains only `เรื่องเล่า short`
- No visible numeric step summaries or standalone progress bar
- Circles above labels, connector ends aligned with circle edges and vertically centered
- Branding PNG loads; no page overflow; footer remains visible; long body scrolls inside card
- Existing navigation, draft invalidation, session expiry and dashboard workflow checks passed
- PNG SHA-256 matches original files; no image modification or client media import

Inspected desktop/narrow screenshots. No full backend suite, unit rerun or EXE build: business/navigation state unchanged.

## Activation

The existing SmartFlow Next Dev window contains a nonempty Story draft and three completed steps.
Verified only presence of content/completion through Windows UI Automation; no draft text was exported.
Left that window untouched to preserve its in-memory draft. Activation of the new build in that window is pending.
Browser/source verification above does not claim the already-open native window has changed.
Legacy app, Extension, jobs and profiles were not changed.
