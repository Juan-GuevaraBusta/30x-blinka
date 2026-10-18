# Security Policy

## Reporting a Vulnerability

Please report security issues privately using [GitHub Security Advisories](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability) for this repository ("Security" tab → "Report a vulnerability"). If that option is not available to you, open a regular issue in this repository as the default channel — there is no confirmed dedicated security email or other channel for this project at this time.

Do not include real credentials, tokens, or any non-synthetic data in a report (see Scope below).

## Scope

This is a hackathon project that works with **synthetic data only** (invariant I6, `AGENTS.md`). There are no real customer, vendor, or company records in this repository. A `PAGAR` (pay) decision is a simulated, recorded state — the system **never moves real money** (invariant I8, `AGENTS.md`).

Because of this:

- A report about "exposure of real data" does not apply: no real data exists in the repo.
- A report about the mutating endpoints lacking authentication, or about the ledger race condition under concurrency, is already known and documented. See the existing writeups and their fixes rather than re-reporting the same detail:
  - Ledger concurrency / single-worker lock: `docs/T5_8_SPEC.md`
  - Admin key and approver validation on mutating endpoints: `docs/T5_9_SPEC.md`

### Known limitations

- **Single-worker lock (`docs/T5_8_SPEC.md`).** The decision path that reads the ledger, decides, and persists a `PAGAR` is serialized with a single process-level lock. This only protects a single `uvicorn` worker process; it does not protect against multiple worker processes or replicas. The deployment is expected to run with one worker.
- **Admin key shared via server proxy (`docs/T5_9_SPEC.md`).** Mutating endpoints (`PUT /rules`, approve, reject) require an `X-Admin-Key` header validated against `ADMIN_API_KEY`. In the public demo, the frontend's server-side proxy routes inject that key on the visitor's behalf, so any visitor using the public demo UI can act through the proxy as if they held the admin key. This is a known limitation of the public demo, not a restricted-access system.

## Out of Scope

- Denial-of-service reports against the hackathon's free-tier deployment (Render/Vercel `free` plan). The backend is expected to sleep after inactivity on this plan; this is documented, expected behavior, not a vulnerability (`docs/T4_9_SPEC.md`).
- Vulnerabilities in third-party dependencies reported by CodeQL or Dependabot. Those are handled as ordinary issues/PRs, not as a private security report.
