# Secret Handling and Leak Prevention

## What changed

- Removed the exposed plaintext `OPENAI_API_KEY` value from `.env`.
- Kept `.env` as a local-only file and `.env.example` as placeholder-only.
- Added CI secret scanning workflow: `.github/workflows/secret-scan.yml` (gitleaks).

## Required one-time action

Rotate the previously exposed API key immediately. A key that appeared in plaintext should be considered compromised.

## Best-practice workflow

1. Store real keys only in local environment variables or local `.env`.
2. Keep `.env.example` free of secrets and use placeholders only.
3. Store CI/CD secrets in platform secret stores (for example GitHub Actions Secrets).
4. Let CI block secret leaks through `.github/workflows/secret-scan.yml`.

## Notes

- `.env` is already ignored by git; never force-add it.
- If a secret is exposed, rotate/revoke it immediately and assume compromise.
