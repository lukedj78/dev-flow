> Snapshot date: **2026-09-22** (dist-tags read off npm that day; `expo@57.0.24` stable, `expo@next` = `58.0.0-preview.5`). Beta/preview tag conventions are the most volatile part of this workflow — and the tags themselves move without a release note. `[VERIFY]` with `npm view expo dist-tags` **and** `https://expo.dev/changelog` before running any of this on a real project.

# Upgrading to a beta / preview Expo SDK

Only follow this path on **explicit user request**. A beta SDK is, by definition, less stable than the current stable release — never move a production app here as a default or convenience.

## When this applies

- The user explicitly asks to try an upcoming SDK ahead of stable release (e.g. to unblock on a fix, or to test compatibility early).
- The user is debugging an issue that's reportedly fixed only in a preview build.

## Install path

```bash
npx expo install expo@next --fix
```

**The dist-tag map, read off npm on 2026-09-22** (`npm view expo dist-tags`):

| Tag | Means | On 2026-09-22 |
|---|---|---|
| `latest` | stable | `57.0.24` |
| `next` | **whatever the cycle is on — read it, never assume** | `58.0.0-preview.5` |
| `canary` | nightly of the upcoming SDK | `58.0.0-canary-20260909-ea7a89a` |
| `canary-sdk-NN` | — | one canary line per upcoming SDK |
| `sdk-NN` | pin an SDK **line** and still get its patches | `sdk-52` … `sdk-57` (`57.0.24`) |

⚠️ **`next` means different things at different times, and that is the trap — in both directions.**
On 2026-08-26 it pointed at stable `57.0.16`, so a user who asked for "the beta" got stable while
believing they had taken a risk. On 2026-09-22 it points at `58.0.0-preview.5`, so the same command
now moves a project onto a **beta** that the previous snapshot of this page promised it would not.
Read the tag before running the command, every time: `npm view expo dist-tags` answers it, and the
answer changes without notice. Name the version you are proposing, never the tag.

### SDK 58 beta — what it costs today (changelog 2026-09-15, read 2026-09-22)

The beta period was announced as three to four weeks, and the stable release follows **React Native
0.88**, which is itself still a release candidate (`react-native@next` = `0.88.0-rc.2` on 2026-09-22).
Four things make this beta heavier than usual to try:

- **EAS Build images with Xcode 27 were "coming soon"** at the announcement; the latest image ships
  Xcode 26.6. Check before promising a cloud build of a beta app.
- **Expo Go for SDK 58 is not in the stores yet** — it comes through Expo CLI (Android devices and
  emulators, iOS simulators) and `eas go` for iOS devices. The store builds update after stable.
- **React Native 0.88 is an RC**, so the SDK's own floor moves again before stable.
- The **breaking changes are large** (iOS 27 scene life cycle, the Strict TypeScript API, the
  expo-router core rework): `references/breaking-changes.md` §SDK 58 lists them, and each one is work
  that survives into the stable upgrade — the reason to do it early, if you do it at all.

**Tooling from this cycle worth knowing about, none of it adopted here yet:** `@expo/agent-cli`
(MIT, `1.0.16`, experimental) sits on top of Expo CLI, EAS CLI and `expo-doctor` and is built for
agents — `status` answers Expo Go compatibility without starting the app, `dev` starts the app in one
command, **`smoke` = start + screenshot + stop**, and `skills:sync` installs agent skills that ship
inside `node_modules`. `expo-device-hub` (`0.10.1`) is now an official dev-tools plugin: a browser
dashboard streaming every local simulator and emulator, tap/swipe/type included. Both are candidates
for the visual-verification loop the `rn-*` skills do not have; revisit when SDK 58 is stable.

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
