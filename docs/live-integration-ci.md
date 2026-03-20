# Live Integration CI Setup (GitHub)

This project now has a dedicated live integration workflow:

- Workflow file: `.github/workflows/live-integration.yml`
- Job name: `backend-live-integration`
- Trigger: `main` pushes, nightly schedule, and manual dispatch
- Environment: `integration`
- Preflight validation job: `live-integration-preflight`

## 1) Create the GitHub Environment

In GitHub repository settings:

1. Go to `Settings` -> `Environments`.
2. Create environment: `integration`.
3. Add protection rules (recommended): required reviewer approval.

## 2) Add Environment Secrets and Variables

Under environment `integration`:

- Secret: `OPENAI_API_KEY`
- Secret: `MYSQL_ROOT_PASSWORD` (required)
- Variable: `OPENAI_MODEL` (required, recommended value: `gpt-4o-mini`)

## 3) How the Workflow Uses Them

The workflow injects values as environment variables for tests:

- `OPENAI_API_KEY` from `secrets.OPENAI_API_KEY`
- `OPENAI_MODEL` from `vars.OPENAI_MODEL`
- MySQL credentials from `secrets.MYSQL_ROOT_PASSWORD`

Live tests only run when `RUN_LIVE_TESTS=1` is present (set in workflow).
If required values are missing, `live-integration-preflight` fails immediately with a clear error.

## 4) Branch Protection Recommendation

Keep these checks required for `main`:

- `secret-scan`
- `backend-pytest`
- `frontend-lint-unit`

Keep `backend-live-integration` non-required until you decide to make live checks merge-blocking.

## 5) Security Best Practices

- Never put real secrets in repository files.
- Use environment-scoped secrets (not repo-wide) for production-like checks.
- Avoid running secret-backed live tests on untrusted fork PRs.
