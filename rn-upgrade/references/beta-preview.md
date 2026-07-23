> Snapshot date: 2026-07-23. Beta/preview tag conventions are the most volatile part of this workflow — `[VERIFY]` every command here against `https://docs.expo.dev/changelog/` before running on a real project.

# Upgrading to a beta / preview Expo SDK

Only follow this path on **explicit user request**. A beta SDK is, by definition, less stable than the current stable release — never move a production app here as a default or convenience.

## When this applies

- The user explicitly asks to try an upcoming SDK ahead of stable release (e.g. to unblock on a fix, or to test compatibility early).
- The user is debugging an issue that's reportedly fixed only in a preview build.

## Install path

```bash
npx expo install expo@next --fix
```

- `@next` is the dist-tag Expo publishes prerelease SDK builds under. `[VERIFY]` this tag name for the cycle in question — Expo has used `@next` consistently but always confirm against current docs before typing it into a real project.
- Package versions during a beta cycle often look like `x.y.z-preview.N` (prerelease semver). `expo install --fix` should resolve the compatible prerelease versions of every Expo-adjacent package automatically once `expo@next` is installed — do not hand-pin individual `-preview.N` versions unless `expo install --fix` fails to resolve one.

## Checking available versions and manifests

```bash
curl -s https://exp.host/--/api/v2/versions | less
```

Useful when diagnosing "why doesn't my beta build see the runtime it expects" issues — this endpoint reflects what Expo's infrastructure currently considers valid SDK/runtime combinations.

## Before recommending this path, tell the user

- Beta SDKs can and do change API shape between the beta and final stable release — code written against a beta may need adjustment when stable ships.
- Third-party native modules frequently lag behind beta SDK compatibility; expect some to fail `expo-doctor` or crash at runtime until they publish a compatible version.
- EAS Build / Submit support for a given beta SDK may itself lag — check before assuming a beta build can go through the full pipeline.
- Recommend a throwaway branch or a separate git worktree for beta experiments rather than upgrading the main working branch, so reverting is trivial if the beta proves unusable.

## Reverting

If the beta doesn't work out:

```bash
npx expo install expo@<last-known-good-stable> --fix
```

Then repeat Step 5 (cache clean) from the main `rn-upgrade` workflow — stale artifacts from the beta attempt are a common source of confusing errors after reverting.
