#!/usr/bin/env bash
# init-expo-app.sh — create a new Expo + TypeScript app at the given project root.
# Idempotent: if package.json + app/ already exist, exits 0 with "already bootstrapped".
#
# Usage: init-expo-app.sh <project-root> <app-name>

set -euo pipefail

PROJECT_ROOT="${1:?project root required}"
APP_NAME="${2:?app name required}"

cd "$PROJECT_ROOT"

if [[ -f package.json && -d app ]]; then
  echo "[init-expo-app] already bootstrapped (package.json + app/ exist) — skipping"
  exit 0
fi

if [[ -f package.json ]]; then
  echo "[init-expo-app] package.json exists but app/ missing — refusing to overwrite, please clean up"
  exit 1
fi

# create-expo-app refuses to scaffold into a non-empty dir. In real usage the project
# root already contains PROJECT.md, PRD.md, DESIGN.md, .workflow/, possibly .git/, etc.
# Stash those into a sibling temp dir, run create-expo-app, then restore.
STASH_DIR="$(mktemp -d "${TMPDIR:-/tmp}/rn-bootstrap-stash-XXXXXX")"
echo "[init-expo-app] stashing pre-existing files to $STASH_DIR …"
# Move everything except dotfiles managed by version control / OS (.git, .DS_Store) —
# create-expo-app tolerates those. Anything else moves.
shopt -s nullglob dotglob
for entry in "$PROJECT_ROOT"/*; do
  base="$(basename "$entry")"
  # Keep .git in place so create-expo-app can append to it; never stash node_modules.
  case "$base" in
    .|..|.git|.DS_Store|node_modules) continue ;;
  esac
  mv "$entry" "$STASH_DIR/"
done
shopt -u nullglob dotglob

# Trap ensures stash is restored even if create-expo-app fails.
restore_stash() {
  echo "[init-expo-app] restoring stashed files from $STASH_DIR …"
  shopt -s nullglob dotglob
  for entry in "$STASH_DIR"/*; do
    base="$(basename "$entry")"
    # If create-expo-app generated a file with the same name (unlikely for PROJECT.md etc.),
    # the stashed copy is authoritative — overwrite.
    mv -f "$entry" "$PROJECT_ROOT/"
  done
  shopt -u nullglob dotglob
  rmdir "$STASH_DIR" 2>/dev/null || true
}
trap restore_stash EXIT

echo "[init-expo-app] running create-expo-app …"
npx --yes create-expo-app@latest . \
    --template blank-typescript \
    --no-install

echo "[init-expo-app] installing base dependencies …"
# create-expo-app --no-install skipped npm install. We MUST install the base deps
# (including the `expo` package itself) here so the subsequent `npx expo install …`
# call can read the SDK version from node_modules/expo/package.json. Without this
# step, expo CLI errors with: "Cannot determine the project's Expo SDK version".
# --legacy-peer-deps avoids known peer-range mismatches between Expo SDK 57 deps
# and transitively-required RN versions; safe to drop when upstream peer ranges
# stabilize.
npm install --legacy-peer-deps

echo "[init-expo-app] adding expo-router + its runtime peers (SDK-matched versions) …"
# Use `npx expo install` so the Expo CLI picks the version compatible with the
# installed Expo SDK. Plain `npm install expo-router` grabs latest from npm, which
# can be one SDK ahead and fail with peer-dep conflicts (e.g. RN version mismatch).
# `-- --legacy-peer-deps` is passed through to the underlying npm install — same
# reason as install-stack.sh: Expo SDK 57 transitively pulls packages (e.g.
# react-native-screens) that demand a newer RN than SDK 57 ships (RN 0.86.2).
#
# expo-linking, expo-constants and react-native-screens are NOT optional. They are
# peerDependencies of expo-router (`npm view expo-router@57 peerDependencies`:
# expo-linking ^57.0.9, expo-constants ^57.0.17, react-native-screens ^4.26.0) and
# `npm install --legacy-peer-deps` does not auto-install peers. Without them
# `tsc --noEmit` passes and the very first `expo start` fails with
#   Unable to resolve "expo-linking" from "node_modules/expo-router/build/fork/useLinking.native.js"
# (observed 2026-09-08 on SDK 57 / expo-router 57.0.20). The remaining peers
# (@expo/log-box, @expo/metro-runtime, reanimated, gesture-handler, safe-area) come
# from the blank-typescript template or from install-stack.sh.
npx --yes expo install expo-router expo-linking expo-constants react-native-screens -- --legacy-peer-deps

echo "[init-expo-app] done. Next: install-stack.sh"
