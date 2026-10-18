"""T9.2 (D061) — Email inbox intake with a deterministic-first invoice classifier.

Decision contract: `docs/T9_2_SPEC.md`. Config and thresholds live in
`app.inbox.config` (new module, not `app.config`) to avoid touching a file
shared with other in-flight tasks during this hackathon round; everything
here is additive and the only edit to an existing module is the single
`app.include_router(...)` call appended inside `app.api.app.create_app`.
"""
