# SmartFlow Next working rules

This is a new project. Do not import legacy source, MD files, jobs, browser profiles or credentials.

- Open `docs/index.md`, then only the topic needed for the task. Do not read all MD files or all source files.
- Check Git status before editing. The owner requested development on `dev`; preserve existing changes.
- Keep business rules in backend services, not React components or desktop window callbacks.
- Every API route must authenticate and declare a server-enforced permission; missing policy denies access. Add allow/deny tests with each feature. Dev identity bypass never skips token/permission checks and is forbidden in prod/frozen builds; see `docs/operations/security.md`.
- Every external operation needs a persisted receipt before dispatch. An uncertain or accepted send must never be replayed automatically.
- Recover safe local failures automatically with bounded retries. Persist the failure reason and retain checkpoints.
- Use stable error codes, job/trace/request IDs and allowlisted logs. Never log tokens, prompts, provider output, titles, raw exception messages or user paths.
- Persist state transitions and events in the same transaction. A UI progress label is not proof of a saved artifact.
- Add behavioral tests for the changed boundary, including a relevant crash, timing or duplicate case. Use injected clocks instead of real sleeps except process/browser integration tests.
- Choose checks from `docs/development/testing.md`. Run `--scope all` for broad changes and release handoffs; do not repeat a completed full run for documentation or fixture-only corrections.
- Report exact checks and measured durations. Offline simulation, source UI, packaged EXE, clean Windows and live provider evidence are separate claims.
- One topic per document; follow `docs/development/documentation.md`. Keep this file as rules and the index as links only.
- Update the owning topic in place and add its index link. Never append release history, reports or plans to a central file; Git preserves edits.
- For docs-only work, check links, topic coverage and `git diff --check`; do not run runtime tests or rebuild the EXE.
- Do not push private runtime data, generated EXEs, support bundles or browser test artifacts to Git. Do not bypass client/browser policy.
- A real provider adapter needs bounded I/O, durable ownership, acceptance evidence, read-only reconciliation and focused tests before activation. Never relabel simulator output as real media.
