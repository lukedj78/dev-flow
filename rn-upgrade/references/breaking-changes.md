> Snapshot date: 2026-07-23. This table is illustrative, not exhaustive — the per-SDK breaking-changes list is only correct on `https://docs.expo.dev/changelog/` for the exact versions being crossed. Re-verify `[VERIFY]` rows before relying on them.

# Breaking-changes checklist

Walk this before declaring an upgrade done. For every row that applies to the project, confirm the migration happened and the corresponding manual test passed.

## Deprecated / split / renamed modules

| Old | New | Notes |
|---|---|---|
| `expo-av` | `expo-audio` + `expo-video` | `expo-av` was deprecated in SDK 53 and **removed in SDK 54**, replaced by two focused packages: `expo-audio` for playback/recording, `expo-video` for video playback. Audio and video code must be split when migrating — they're no longer one API surface. |
| `expo-permissions` | per-module permission APIs | Long deprecated; each module (camera, location, notifications) now exposes its own `usePermissions`/`requestPermissionsAsync`. If still present in a project, this is a stale leftover, not a recent-SDK concern. |
| `expo-file-system` (legacy API) | `expo-file-system/next` (new API) | Some SDKs ship a parallel modern API alongside the legacy one before a full cutover. `[VERIFY]` which is current/required for the target SDK. |
| Old Expo Router APIs (e.g. pre-file-based conventions) | current Expo Router conventions | If the project predates Expo Router stabilizing, check `rn-expo-router/SKILL.md` for the current file-based routing shape. |

## Import-path and API shape changes to check every upgrade

- Search the codebase for imports from packages listed as removed/deprecated in the target SDK's changelog (`grep -rn "from 'expo-av'"` etc.) before assuming "it still builds so it's fine" — deprecated APIs often still work for one or two SDKs before hard removal.
- Check `app.json`/`app.config.*` config plugin entries against the plugin's current expected shape — plugin config schemas do change between majors.
- Check any native module with a config plugin (push notifications, Firebase, in-app purchases) for updated plugin option names.

## Manual test checklist (run after any deprecated-module migration)

- [ ] Camera: photo capture, video capture (if the app uses either).
- [ ] Audio: playback, recording (if migrated off `expo-av`).
- [ ] Video: playback, controls, fullscreen (if migrated off `expo-av`).
- [ ] Navigation: route transitions, deep links, back-gesture behavior (Expo Router internals can shift between SDKs even without an explicit changelog entry).
- [ ] Push notifications: permission prompt, foreground/background delivery (if config-plugin options changed).
- [ ] Any third-party native module the project depends on that has its own SDK-compatibility matrix (check that library's own changelog too — an Expo SDK bump can silently break a dependency that hasn't caught up).

## Where to find the authoritative list

Do not rely on memory or on this file's table alone for a specific SDK crossing — always cross-check:

1. `https://docs.expo.dev/changelog/` — the target SDK's full release notes, "Breaking Changes" section.
2. MCP Expo (`https://mcp.expo.dev/mcp`), if available, for current guidance.
3. The official `expo/skills` repo's `expo-upgrade` skill, if installed — it's the closest thing to a maintained per-SDK source.
