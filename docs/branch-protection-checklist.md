# Branch Protection Checklist

Use this checklist when configuring protection for `main` in GitHub.

## Required branch protection settings

1. Require a pull request before merging.
2. Require at least 1 approving review.
3. Require review conversation resolution before merging.
4. Require branches to be up to date before merging.
5. Restrict direct pushes to `main`.
6. Disable force pushes on `main`.

## Required status checks

Mark these checks as required:

- `secret-scan`
- `backend-pytest`
- `frontend-lint-unit`

Keep this check non-required while E2E is being stabilized:

- `frontend-e2e`

## Local pre-push commands

```bash
cd backend && uv run pytest -q
cd frontend && npm run lint
cd frontend && npm run test:unit
```

