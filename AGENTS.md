# SmartFlow Next working rules

This is a new project. Do not import legacy source, MD files, jobs, browser profiles or credentials.

- Start with README.md, then only the relevant section of ARCHITECTURE.md or TESTING.md.
- Check Git status before editing. The owner requested development on `dev`; preserve existing changes.
- Keep business rules in backend services, not React components or desktop window callbacks.
- Every external operation needs a persisted receipt before dispatch. An uncertain or accepted send must never be replayed automatically.
- Recover safe local failures automatically with bounded retries. Persist the failure reason and retain checkpoints.
- Use stable error codes, job/trace/request IDs and allowlisted logs. Never log tokens, prompts, provider output, titles, raw exception messages or user paths.
- Persist state transitions and events in the same transaction. A UI progress label is not proof of a saved artifact.
- Add behavioral tests for the changed boundary, including a relevant crash, timing or duplicate case. Use injected clocks instead of real sleeps except process/browser integration tests.
- Run the smallest applicable scope in TESTING.md. Run `--scope all` for broad changes and release handoffs; do not repeat a completed full run for documentation or fixture-only corrections.
- Report exact checks and measured durations. Offline simulation, source UI, packaged EXE, clean Windows and live provider evidence are separate claims.
- Keep these instructions short. Update current docs in place; Git preserves history.
- Do not push private runtime data, generated EXEs, support bundles or browser test artifacts to Git. Do not bypass client/browser policy.
- A real provider adapter needs bounded I/O, durable ownership, acceptance evidence, read-only reconciliation and focused tests before activation. Never relabel simulator output as real media.
