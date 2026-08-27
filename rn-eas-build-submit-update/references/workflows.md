> Sources: https://docs.expo.dev/eas/workflows/get-started/

# EAS Workflows — CI/CD on EAS infrastructure

EAS Workflows is Expo's CI: YAML workflows that run on EAS runners, triggered by git push / PR / cron. Free tier covers small projects; paid scales up.

## Why EAS Workflows over GitHub Actions

- **Built-in EAS auth**: no need to manage Expo tokens in CI secrets.
- **Native runners**: macOS + Linux, properly configured for Expo builds.
- **Single source of truth**: the workflow YAML lives in the same repo.

Use GitHub Actions if you already have a polished CI and just want to trigger `eas build` from there — `npx eas-cli@latest build --non-interactive` works fine. Use EAS Workflows for greenfield mobile projects.

## File structure

```
.eas/
└── workflows/
    ├── ci.yml             # on PR: lint + test + preview build
    ├── deploy-preview.yml # on push to main: preview build + update preview channel
    └── deploy-prod.yml    # on tag v*: production build + submit + update production channel
```

## Example: PR check workflow

```yaml
# .eas/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs_on: linux-medium
    steps:
      - uses: eas/checkout@v1
      - uses: eas/use-npm@v1
      - run: npm ci --legacy-peer-deps
      - run: npx tsc --noEmit
      - run: npm test -- --runInBand --bail

  preview-build:
    needs: lint-and-test
    runs_on: linux-medium
    if: github.event.pull_request.draft == false
    steps:
      - uses: eas/checkout@v1
      - uses: eas/build@v1
        with:
          profile: preview
          platform: all
```

## Example: deploy on push to main

```yaml
# .eas/workflows/deploy-preview.yml
name: Deploy Preview

on:
  push:
    branches: [main]

jobs:
  update-preview:
    runs_on: linux-medium
    steps:
      - uses: eas/checkout@v1
      - uses: eas/use-npm@v1
      - run: npm ci --legacy-peer-deps
      - uses: eas/update@v1
        with:
          branch: main
          channel: preview
          message: ${{ github.event.head_commit.message }}
```

## Example: tag-triggered production release

```yaml
# .eas/workflows/deploy-prod.yml
name: Deploy Production

on:
  push:
    tags: ["v*"]

jobs:
  production-release:
    runs_on: linux-medium
    steps:
      - uses: eas/checkout@v1
      - uses: eas/use-npm@v1
      - run: npm ci --legacy-peer-deps
      - uses: eas/build@v1
        with:
          profile: production
          platform: all
      - uses: eas/submit@v1
        with:
          profile: production
          platform: all
```

Tag a release: `git tag v1.2.0 && git push origin v1.2.0` → workflow builds + submits.

## Where to find runner / step references

- Runner types (linux-small / linux-medium / linux-large / macos-medium): https://docs.expo.dev/eas/workflows/syntax/
- Built-in actions (checkout, use-npm, build, submit, update): https://docs.expo.dev/eas/workflows/syntax/ — ⚠️ the `/eas/workflows/reference/` URL this line used to point at **404s** (checked 2026-08-26); the syntax page is the live one, and `/eas/workflows/examples/` has the worked cases.

## When to use cron

```yaml
on:
  schedule:
    - cron: "0 6 * * 1"   # every Monday 6 AM UTC
```

Use cases:
- Weekly snapshot of `preview` channel.
- Nightly dependency freshness check + auto-PR.
- Heartbeat to test that EAS auth still works.

## DON'T

- ❌ Trigger production build on every push to main. Tag-based releases stay sane.
- ❌ Skip `npx tsc --noEmit` in CI — saves you from green compile + red device.
- ❌ Put secrets in the YAML — use **`eas env:set --scope project`** and reference as env. (`eas secret:create` still works but is two renames behind at `eas-cli@22.6.0` — see `references/credentials.md`.)
- ❌ Mix `eas update` and `eas build` for the same change without considering native-side compatibility.
