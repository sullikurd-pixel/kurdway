# Master Clean QA gate

Baseline: 31ae66e8a5098b04c6f38874514d4f72e2d435f4 (0.7.1-dev).
This branch is not approved for deployment.

## Run
Use a separate checkout and a temporary HOME for tests. Install the declared dependencies in an isolated environment. Run python -m pytest -q. Regression tests mock SMTP and create synthetic accounts only. No real credentials or database files belong in Git.

## Backup
Run backup.py using the installed application interpreter on the owner Mac. It creates a read-only SQLite snapshot with integrity verification. Backup files contain personal data; do not upload them. A successful integrity check is not a complete restore drill. Verify restoration in an isolated directory before changing schema.

## Release gates
- Pass automated tests, including cross-account authorization and session revocation.
- Record exact installed dependency versions and review vulnerabilities.
- Test Safari, mobile layout, all three languages, GPX validation, local drafts, and live SMTP with an owner-controlled account.
- Verify backup restoration and rollback.
- Review keychain migration for SMTP, durable throttling, admin MFA, HTTPS, and location privacy before any public deployment.
- Keep main unchanged until review and approval.

Known gaps: existing smoke tests may reject non-loopback TestClient peers before reaching authentication. The new regression test uses an explicit loopback peer. The dependency declaration is a range specification, not a verified lockfile. Production readiness is not claimed.
