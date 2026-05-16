#!/usr/bin/env bash
# install-stack.sh — install the opinionated RN/Expo stack into an existing Expo app.
# Idempotent: re-running detects already-installed packages via npm.
#
# Usage: install-stack.sh <project-root>

set -euo pipefail

PROJECT_ROOT="${1:?project root required}"
cd "$PROJECT_ROOT"

if [[ ! -f package.json ]]; then
  echo "[install-stack] no package.json — run init-expo-app.sh first"
  exit 1
fi

echo "[install-stack] installing styling stack (NativeWind v4 + safe-area + expo-image + FlashList) …"
# NativeWind v4 requires Tailwind 3.4.x — pin explicitly. Do NOT bump to TW 4.
npx expo install \
  nativewind@^4 tailwindcss@^3.4 \
  react-native-safe-area-context \
  expo-image \
  @shopify/flash-list

echo "[install-stack] installing animations stack (Reanimated + Gesture Handler) …"
# expo install picks the version compatible with the current Expo SDK.
# --legacy-peer-deps works around a known peer-dep conflict where transitively-installed
# react-native-screens (via @react-navigation/bottom-tabs) demands a newer RN than the
# Expo SDK ships. The Expo CLI's chosen versions are still correct; npm just refuses to
# resolve without the flag. Drop the flag once the upstream peer ranges align.
npx expo install react-native-reanimated react-native-gesture-handler -- --legacy-peer-deps

echo "[install-stack] installing state + data (Zustand + TanStack Query) …"
npm install zustand @tanstack/react-query

echo "[install-stack] installing dev tools (prettier + Tailwind plugin) …"
npm install --save-dev prettier prettier-plugin-tailwindcss

echo "[install-stack] done. Next: wire-nativewind.ts"
