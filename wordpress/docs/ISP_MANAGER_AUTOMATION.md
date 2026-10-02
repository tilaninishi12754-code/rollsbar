# Rolls Bar — ISPmanager automation

Date: 2026-10-02
Status: AUTOMATION BOOTSTRAP

## Goal

The owner wants the deployment process to be agent-operated with almost no manual panel work.

Target flow:

GitHub / Codex -> CI gates -> GitHub staging environment -> ISPmanager API -> staging site -> WordPress Gate B -> later production promotion.

Manual FTP upload is a fallback, not the primary workflow.

## Why this fits ISPmanager

ISPmanager exposes an official API. Exact functions and parameters depend on the panel configuration, so the safe order is:

1. authenticate;
2. perform a read-only capability probe;
3. inspect actual account capabilities;
4. generate the exact mutation plan for this panel;
5. only then create staging website/database/SSL;
6. deploy the exact package-of-record;
7. verify Gate B.

The first workflow intentionally performs no mutation.

## GitHub staging environment

Create one GitHub Environment named:

`staging`

Add these Environment Secrets:

- `ISP_MANAGER_URL` — panel base URL, for example `https://panel.example.com:1500` or another HTTPS URL used by this hosting panel;
- `ISP_MANAGER_USER`;
- `ISP_MANAGER_PASSWORD`.

Do not put these values in repository files, issues, chat messages, workflow variables, commit history, or screenshots.

The current read-only workflow:

`.github/workflows/ispmanager-staging-probe.yml`

It verifies that the account can authenticate and read:

- websites;
- databases.

It does not create, edit, or delete anything.

## Security rules

- Use HTTPS only.
- Prefer a limited staging/site-owner account instead of a full administrator account when the hosting setup allows it.
- Keep credentials in GitHub Environment Secrets or another secret manager.
- Never hard-code credentials in the repository.
- Production must use a separate environment and separate credentials.
- Production deployment will require an explicit protected gate.
- Database state will not be overwritten wholesale after the live store starts receiving orders.

## After probe PASS

The next workflow will be generated from the actual panel capabilities and will:

1. ensure isolated staging site;
2. ensure separate staging database;
3. ensure supported PHP >= 8.1;
4. request/attach Let's Encrypt when DNS permits;
5. upload the exact Rolls Bar staging bundle;
6. bootstrap only five catalog cards;
7. run Gate B;
8. stop before full catalog promotion unless Gate B passes.

## Codex role

Codex can maintain and audit the deployment scripts/workflows in Git.

Codex should not receive raw long-lived hosting credentials in prompts. Credentials belong in a secret store and are injected only into deployment jobs that need them.
