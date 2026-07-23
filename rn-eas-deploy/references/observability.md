> Sources: https://docs.expo.dev/eas/observe/introduction/, https://docs.expo.dev/eas-update/introduction/, https://github.com/expo/skills (`plugins/expo/skills/eas-observe`, `plugins/expo/skills/eas-update-insights`), https://mcp.expo.dev/mcp. `[VERIFY]` markers flag details that move fast (dashboard URLs, exact flags, plan tiers) — recheck against live docs / the `mcp.expo.dev` MCP server / the official `expo/skills` `eas-observe` and `eas-update-insights` skills before relying on them verbatim.

# Observability — closing the release → observe → decide loop

`rn-eas-deploy` ships production builds; `rn-eas-build-submit-update` ships OTA updates. Neither skill closes the loop — without observability you ship blind and only find out something broke when a user complains. This reference covers the two Expo-native observability surfaces (EAS Observe, EAS Update Insights) that plug directly into both workflows, and how to read them to decide "do nothing / hotfix / rollback".

## The two tools, at a glance

| Tool | Answers | Granularity | Plan |
|---|---|---|---|
| **EAS Observe** | "Is the app fast / does it start well in production?" | Native + JS startup & navigation performance (cold/warm launch, TTI, custom events) | `[VERIFY]` paid EAS product, Open Beta with a free tier (first 10,000 MAU free per public docs, 2026-07) |
| **EAS Update Insights** | "Did this OTA / this channel roll out cleanly?" | Per-update-group and per-channel adoption, crash rate, embedded-vs-OTA split | `[VERIFY]` paid EAS product; queries count against the project's EAS Update usage |

Neither replaces a dedicated crash reporter. `[VERIFY]` EAS Observe does not do crash/error tracking as of 2026-07 (Expo's own docs list it as a planned future addition) — keep Sentry/Bugsnag/etc. as the system of record for crashes, per `rn-eas-deploy/SKILL.md` Step 11 ("Where to monitor crash reports").

## EAS Observe — production performance monitoring

### What it gives you
- Cold launch time, warm launch time, time to first render (TTR), time to interactive (TTI), bundle load time.
- Per-route/navigation timing when wired to Expo Router or React Navigation.
- Custom events via `Observe.logEvent(...)`.
- Filterable by platform and app version in the EAS dashboard.
- Not available in Expo Go — dev-client and production/preview builds only.

### When to enable it
Enable it once the app is `feature_complete`, before its first `rn-eas-deploy` production build (insert this before Step 7 "Production build"). Enabling it before the first release gives a performance baseline from day one instead of only after an incident.

### Setup
```bash
npx expo install expo-observe
```
Then wrap the root layout — `[VERIFY]` the exact wrapper against the installed SDK, it changed between versions:
- SDK 55: `AppMetricsRoot`.
- SDK 56+: `ObserveRoot`.

Call `markInteractive()` once the app is ready for input (end of splash/loading state) — skipping this means TTI never resolves and the metric is meaningless.

### Reading the metrics
```bash
eas observe:metrics-summary   # top-line dashboard-in-a-terminal
eas observe:metrics           # raw metric rows, filterable by platform/version
eas observe:routes            # per-route navigation timing
eas observe:events            # custom Observe.logEvent() data
eas observe:versions          # breakdown by app version / build
```
`[VERIFY]` these exact subcommand names and flags against `eas observe --help` — this is a fast-moving beta surface, treat the list as a starting point, not a contract.

Dashboard: `[VERIFY]` the "Observe" tab of the project's EAS dashboard at expo.dev — confirm the current URL/tab name live before pointing a user at it.

### Anti-patterns
- Do not treat EAS Observe as the only safety net — it measures slowness, not errors. Pair it with Sentry/Bugsnag.
- Do not skip `markInteractive()` — TTI silently never resolves.
- Do not check metrics only when a user complains — read them on the cadence in "Closing the loop" below.

## EAS Update Insights — OTA rollout health

### What it gives you
- Per-update-group launches, failed launches, crash rate, unique users, payload size.
- Per-channel + per-runtimeVersion adoption: embedded-build users vs. OTA users, most popular updates.
- Daily time series to spot a spike right after a rollout.

### Core commands
```bash
eas update:list                                            # find recent update groups + IDs
eas update:insights <groupId> [--platform ios|android] [--days N | --start <iso> --end <iso>] [--json --non-interactive]
eas update:view <groupId> --insights                        # update details + metrics in one call
eas channel:insights --channel <name> --runtime-version <version> [--days N] [--json --non-interactive]
```
`[VERIFY]` flags/defaults (`--days` defaults to 7 per the public skill docs, 2026-07) against `eas update:insights --help` / `eas channel:insights --help` before wiring these into a script.

### Key metrics to know
- `crashRatePercent` = `failedInstalls / (installs + failedInstalls) * 100`.
- `installs` = downloads of the manifest/launch assets, NOT confirmed successful runs — a device only registers a "run" on its *next* update check. Don't read "installs" as "successful launches".
- `embeddedUpdateTotalUniqueUsers` vs `otaTotalUniqueUsers` — how much of the channel is still on the binary-bundled build vs. actually receiving OTAs. If `otaTotalUniqueUsers` stays flat near zero well after a publish, suspect a `runtimeVersion` mismatch (see `rn-eas-build-submit-update/references/decision-tree.md` Q4) before suspecting a bad rollout.
- Crashes are self-reported by the client; a crash that prevents the next check-in won't be reported — this is adoption/health telemetry, not a crash reporter.

### Deciding hotfix vs. rollback from the numbers
```
After `eas update --branch <name> --channel <preview|production> ...`:

1. Wait for adoption to build (minutes to hours depending on channel size).
2. eas channel:insights --channel <channel> --runtime-version <version> --days 1
   ├── otaTotalUniqueUsers flat near 0 after a reasonable window → runtimeVersion
   │        mismatch, not a bad update — fix the version match, republish.
   └── otaTotalUniqueUsers growing normally → check crash rate next.
3. eas update:insights <groupId> --days 1
   ├── crashRatePercent spikes vs. the previous update's baseline → ROLLBACK now:
   │        eas update:rollback --branch <name> --channel <channel>
   │        (or republish the previous known-good update group)
   ├── crashRatePercent asymmetric by platform (e.g. iOS only)   → investigate that
   │        platform's native module/config before choosing rollback vs. hotfix
   └── crashRatePercent flat/normal                               → healthy, no action
```
This is the same decision as "Q8 — Reverting a bad OTA" in `rn-eas-deploy/references/decision-tree.md`, now driven by actual numbers instead of "a user reported a bug".

## Closing the loop — where this plugs into the existing workflow

```
rn-eas-deploy (production build + submit)          rn-eas-build-submit-update (OTA)
        |                                                    |
        v                                                    v
  enable EAS Observe before Step 7               eas update --channel preview|production
  (production build)                                         |
        |                                                    v
        +---------------> OBSERVE (this file) <--------------+
                                |
                 eas observe:metrics-summary   (post-build)
                 eas channel:insights / update:insights   (post-OTA)
                                |
                 +--------------+---------------+
                 v                               v
         healthy -> no action            unhealthy -> hotfix OTA
                                          (preview channel first)
                                          or eas update:rollback
```

- **After a `rn-eas-deploy` production build + submit**: once the store accepts the binary and users start updating, check `eas observe:metrics-summary` filtered to the new version within the first 24-48h — this is when a real-world cold-start regression is most visible and cheapest to catch.
- **After an OTA via `rn-eas-build-submit-update`**: check `channel:insights` + `update:insights` before promoting from `preview` to `production`, and again a few hours after `production` — this is the trigger for the existing hotfix (Q7) / rollback (Q8) decision trees in `rn-eas-deploy/references/decision-tree.md`.
- There is no dedicated `.workflow/meta.json` field for observability yet (see `references/contracts.md`) — this is a manual runbook step in the deploy/OTA loop, not a phase transition. Both `rn-eas-deploy` and `rn-eas-build-submit-update` should print a reminder to run these checks rather than silently skipping them.

## Common anti-patterns (NEVER do)

- Ship a production build or an OTA to `production` and walk away without checking the metrics above within the first day.
- Confuse EAS Observe (performance) with a crash reporter — it does not catch errors/crashes.
- Read `installs` in EAS Update Insights as "successful launches" — it is a download count, not a confirmed run.
- Decide a rollback from a single data point — always compare against the previous update's baseline (`--days` window) before pulling the trigger.

## Sources

- https://docs.expo.dev/eas/observe/introduction/
- https://docs.expo.dev/eas/observe/get-started/ `[VERIFY]`
- https://docs.expo.dev/eas/observe/dashboard/ `[VERIFY]`
- https://docs.expo.dev/eas/observe/reference/metrics/ `[VERIFY]`
- https://docs.expo.dev/eas-update/introduction/
- https://github.com/expo/skills — `plugins/expo/skills/eas-observe/SKILL.md`, `plugins/expo/skills/eas-update-insights/SKILL.md`
- https://mcp.expo.dev/mcp — official Expo MCP server, surfaces EAS Observe + Update Insights data to AI agents (OAuth-backed, available on the Free plan per Expo's changelog)
