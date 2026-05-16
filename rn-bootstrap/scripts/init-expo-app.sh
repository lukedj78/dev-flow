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

echo "[init-expo-app] running create-expo-app …"
npx --yes create-expo-app@latest . \
    --template blank-typescript \
    --no-install

echo "[init-expo-app] adding expo-router preset …"
# create-expo-app with blank-typescript does NOT include expo-router. Install it now.
npm install expo-router

echo "[init-expo-app] done. Next: install-stack.sh"
