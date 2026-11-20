# Security policy

PegScope is a local, read-only prototype. It does not execute trades or collect holdings. The HTTP dashboard binds to loopback; authenticated API calls are made only by the local CLI.

## Reporting a vulnerability

Do not post API keys, private captures, or exploit details in a public issue. Use GitHub's private vulnerability reporting for this repository if available, or contact the repository owner privately through GitHub. Include the affected version, impact, and a minimal reproduction that contains no real credentials or account data.

## Credential and data handling

- Keep `CMC_API_KEY` in the process environment. Never commit it or place it in browser storage, output logs, recordings, or test fixtures.
- The project intentionally omits local SQLite captures from Git. Recheck staged files before publishing.
- Test provider failures with synthetic fixtures; do not make tests depend on a live API account.
- Public keyless API output is still provider data and must be attributed and handled under CMC's terms.
