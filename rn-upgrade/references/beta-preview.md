> Snapshot date: **2026-08-26** (dist-tags read off npm that day; `expo@57.0.16` stable). Beta/preview tag conventions are the most volatile part of this workflow — and the tags themselves move without a release note. `[VERIFY]` with `npm view expo dist-tags` **and** `https://expo.dev/changelog` before running any of this on a real project.

# Upgrading to a beta / preview Expo SDK

Only follow this path on **explicit user request**. A beta SDK is, by definition, less stable than the current stable release — never move a production app here as a default or convenience.

## When this applies

- The user explicitly asks to try an upcoming SDK ahead of stable release (e.g. to unblock on a fix, or to test compatibility early).
- The user is debugging an issue that's reportedly fixed only in a preview build.

## Install path

```bash
npx expo install expo@next --fix
```

**The dist-tag map, read off npm on 2026-08-26** (`npm view expo dist-tags`) — and the headline is a trap:

| Tag | Then | Now |
|---|---|---|
| `latest` | stable | `57.0.16` |
| `next` | "the beta" | **`57.0.16` — the same build as `latest`** |
| `canary` | — | `58.0.0-canary-20260812-27f94d4` |
| `canary-sdk-NN` | — | one canary line per upcoming SDK |
| `sdk-NN` | — | `sdk-52` … `sdk-56`: the way to pin an SDK **line** and still get its patches |

⚠️ **`expo@next` is not a synonym for "beta".** Between cycles it tracks `latest`, which is exactly
where it sits today — so `npx expo install expo@next` right now installs **stable 57**, and a user who
asked for "the beta" gets nothing of the sort while believing they took a risk. Read the tag before
running the command, every time; the answer is one `npm view expo dist-tags` away and changes without
notice.

`-preview.N` versions are real (`56.0.0-preview.13`, `57.0.0-preview.1` are both published), but they
appear **during** a cycle. As of today SDK 58 exists only as canaries — there is no 58 preview yet.

- `expo install --fix` should resolve the compatible prerelease versions of every Expo-adjacent package once the right `expo` is installed.
- Do not hand-pin individual `-preview.N` or `-canary-*` versions unless `expo install --fix` fails to resolve one.

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
